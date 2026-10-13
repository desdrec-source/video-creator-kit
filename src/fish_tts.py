#!/usr/bin/env python3
"""Fish Audio TTS -> voiceover.wav + words.json (word timestamps).

Uses POST /v1/tts/stream/with-timestamp (SSE). Each event may carry a base64
audio slice and/or an alignment snapshot for a text chunk. Fish reports
segment times *relative to the chunk*, so absolute time =
segment.start + chunk_audio_offset_sec. Only the latest snapshot per
chunk_seq is kept.

Env:  FISH_AUDIO_API_KEY (required), FISH_VOICE_ID (reference_id of a voice
      you own or are licensed to use), FISH_MODEL (optional, default s1).
Usage: python fish_tts.py script.txt out_dir [--speed 0.88]
       python fish_tts.py --parse saved_stream.raw out_dir   # offline re-parse
"""
import argparse, base64, json, os, struct, sys, wave

API = "https://api.fish.audio/v1/tts/stream/with-timestamp"


def fetch_stream(text, speed, raw_path):
    import requests
    key = os.environ.get("FISH_AUDIO_API_KEY")
    voice = os.environ.get("FISH_VOICE_ID")
    if not key or not voice:
        sys.exit("Set FISH_AUDIO_API_KEY and FISH_VOICE_ID (see README).")
    payload = {"text": text, "reference_id": voice, "format": "wav",
               "sample_rate": 44100, "prosody": {"speed": speed, "volume": 0}}
    headers = {"Authorization": f"Bearer {key}", "Content-Type": "application/json",
               "model": os.environ.get("FISH_MODEL", "s1")}
    with requests.post(API, json=payload, headers=headers, stream=True, timeout=300) as r:
        r.raise_for_status()
        with open(raw_path, "w") as f:
            for line in r.iter_lines(decode_unicode=True):
                if line:
                    f.write(line + "\n")


def parse_stream(raw_path, out_dir, script_text=None, meta=None):
    evs = []
    for l in open(raw_path):
        if l.startswith("data:"):
            try:
                evs.append(json.loads(l[5:].strip()))
            except json.JSONDecodeError:
                pass
    blob = b"".join(base64.b64decode(e["audio_base64"]) for e in evs if e.get("audio_base64"))
    if blob[:4] != b"RIFF":
        sys.exit("Stream audio is not WAV; request format=wav.")
    ch = struct.unpack("<H", blob[22:24])[0]
    sr = struct.unpack("<I", blob[24:28])[0]
    bits = struct.unpack("<H", blob[34:36])[0]
    # find 'data' chunk rather than assuming a 44-byte header
    i = blob.find(b"data", 12)
    pcm = blob[i + 8:] if i > 0 else blob[44:]
    fs = ch * bits // 8
    pcm = pcm[: len(pcm) // fs * fs]
    wav = os.path.join(out_dir, "voiceover.wav")
    with wave.open(wav, "wb") as w:
        w.setnchannels(ch); w.setsampwidth(bits // 8); w.setframerate(sr); w.writeframes(pcm)
    dur = len(pcm) / fs / sr
    chunks = {}
    for e in evs:
        if e.get("alignment"):
            chunks[e.get("chunk_seq", 0)] = {"offset": float(e.get("chunk_audio_offset_sec", 0.0)),
                                             "segments": e["alignment"]["segments"]}
    words = []
    for seq in sorted(chunks):
        c = chunks[seq]
        for s in c["segments"]:
            words.append({"i": len(words), "text": s["text"],
                          "start": round(s["start"] + c["offset"], 3),
                          "end": round(s["end"] + c["offset"], 3)})
    out = {"source": "fish.audio stream/with-timestamp", "audio": "voiceover.wav",
           "audio_duration_sec": round(dur, 3), "sample_rate_hz": sr, "channels": ch,
           "words": words, **(meta or {})}
    json.dump(out, open(os.path.join(out_dir, "words.json"), "w"), indent=1)
    print(f"wav {dur:.2f}s {sr}Hz ch{ch}; {len(words)} words -> {out_dir}/words.json")
    return out


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("script"); ap.add_argument("out_dir")
    ap.add_argument("--speed", type=float, default=0.88)
    ap.add_argument("--parse", action="store_true", help="script arg is a saved .raw stream")
    a = ap.parse_args()
    os.makedirs(a.out_dir, exist_ok=True)
    if a.parse:
        parse_stream(a.script, a.out_dir); return
    text = open(a.script).read().strip()
    raw = os.path.join(a.out_dir, "fish_stream.raw")
    fetch_stream(text, a.speed, raw)
    parse_stream(raw, a.out_dir, meta={"prosody_speed": a.speed})


if __name__ == "__main__":
    main()
