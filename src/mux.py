#!/usr/bin/env python3
"""Bulletproof MP4: H.264 High@4.0 yuv420p 30fps CFR + AAC-LC stereo 48k, +faststart.

Mono VO is upmixed with pan (both channels = c0) so players never get
left-only audio. Audio is padded/trimmed to the video length. Verifies the
result with ffprobe and exits non-zero if anything is off.
Usage: python mux.py video.mp4 voiceover.wav out.mp4 [--pad-to SECONDS]
"""
import argparse, json, subprocess, sys

FPS = 30


def probe(path):
    return json.loads(subprocess.check_output(["ffprobe", "-v", "error", "-show_streams", "-show_format",
                                               "-of", "json", path]))


def audio_filter(src, total):
    ch = next((s["channels"] for s in probe(src)["streams"] if s["codec_type"] == "audio"), 1)
    up = "pan=stereo|c0=c0|c1=c0," if ch == 1 else "aformat=channel_layouts=stereo,"
    return f"{up}aresample=48000,apad=whole_dur={total:.3f},atrim=0:{total:.3f}"


def mux(video, audio, out, pad_to=None):
    vdur = float(probe(video)["format"]["duration"])
    total = pad_to or vdur
    cmd = ["ffmpeg", "-y", "-loglevel", "error", "-i", video, "-i", audio,
           "-map", "0:v:0", "-map", "1:a:0",
           "-vf", f"fps={FPS},format=yuv420p" + (f",tpad=stop_mode=clone:stop_duration={max(0,total-vdur):.3f}" if total > vdur else ""),
           "-c:v", "libx264", "-preset", "medium", "-crf", "18", "-pix_fmt", "yuv420p",
           "-profile:v", "high", "-level:v", "4.0", "-r", str(FPS), "-fps_mode", "cfr",
           "-af", audio_filter(audio, total), "-c:a", "aac", "-profile:a", "aac_low", "-b:a", "160k",
           "-ar", "48000", "-ac", "2", "-t", f"{total:.3f}", "-movflags", "+faststart", out]
    subprocess.check_call(cmd)
    return check(out)


def check(path):
    p = probe(path)
    v = next(s for s in p["streams"] if s["codec_type"] == "video")
    a = next((s for s in p["streams"] if s["codec_type"] == "audio"), None)
    errs = []
    want = {"codec_name": "h264", "pix_fmt": "yuv420p", "profile": "High", "level": 40, "r_frame_rate": "30/1"}
    for k, val in want.items():
        if v.get(k) != val:
            errs.append(f"video {k}={v.get(k)} want {val}")
    if not a:
        errs.append("no audio stream")
    else:
        for k, val in {"codec_name": "aac", "profile": "LC", "sample_rate": "48000", "channels": 2}.items():
            if a.get(k) != val:
                errs.append(f"audio {k}={a.get(k)} want {val}")
    with open(path, "rb") as f:
        head = f.read(64 * 1024)
    if head.find(b"moov") < 0 or (head.find(b"mdat") >= 0 and head.find(b"moov") > head.find(b"mdat")):
        errs.append("moov atom not at front (faststart failed)")
    summary = {"file": path, "duration": p["format"]["duration"],
               "video": f"{v['codec_name']} {v.get('profile')} L{v.get('level')} {v['pix_fmt']} {v['width']}x{v['height']} {v['r_frame_rate']}",
               "audio": f"{a['codec_name']} {a.get('profile')} {a['sample_rate']}Hz ch{a['channels']}" if a else None,
               "ok": not errs, "errors": errs}
    print(json.dumps(summary, indent=1))
    return summary


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("video"); ap.add_argument("audio"); ap.add_argument("out")
    ap.add_argument("--pad-to", type=float)
    a = ap.parse_args()
    sys.exit(0 if mux(a.video, a.audio, a.out, a.pad_to)["ok"] else 1)
