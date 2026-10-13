#!/usr/bin/env python3
"""Align your own voiceover -> words.json (same schema as fish_tts.py).

Tries whisperx (forced alignment, best timing) then falls back to
openai-whisper with word_timestamps=True. CPU works; use model 'small' or
'medium.en' for quality, 'base.en' for speed.
Usage: python align.py voiceover.wav out_dir [--model small.en] [--script script.txt]
If --script is given, recognised words are snapped back to your script's
spelling/punctuation when the word counts match.
"""
import argparse, json, os, re, subprocess


def dur(path):
    return float(subprocess.check_output(["ffprobe", "-v", "error", "-show_entries", "format=duration",
                                          "-of", "csv=p=0", path]).decode().strip())


def run_whisperx(wav, model):
    import whisperx
    dev = "cpu"
    m = whisperx.load_model(model, dev, compute_type="int8")
    audio = whisperx.load_audio(wav)
    res = m.transcribe(audio, batch_size=8)
    am, meta = whisperx.load_align_model(language_code=res["language"], device=dev)
    res = whisperx.align(res["segments"], am, meta, audio, dev)
    return [{"text": w["word"], "start": w["start"], "end": w["end"]}
            for s in res["segments"] for w in s.get("words", []) if "start" in w]


def run_whisper(wav, model):
    import whisper
    m = whisper.load_model(model)
    res = m.transcribe(wav, word_timestamps=True, fp16=False)
    return [{"text": w["word"].strip(), "start": w["start"], "end": w["end"]}
            for s in res["segments"] for w in s["words"]]


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("wav"); ap.add_argument("out_dir")
    ap.add_argument("--model", default="small.en"); ap.add_argument("--script")
    a = ap.parse_args()
    os.makedirs(a.out_dir, exist_ok=True)
    try:
        words, eng = run_whisperx(a.wav, a.model), "whisperx"
    except ImportError:
        words, eng = run_whisper(a.wav, a.model), "whisper"
    if a.script:
        sw = open(a.script).read().split()
        if len(sw) == len(words):
            for w, s in zip(words, sw):
                w["text"] = s
        else:
            print(f"note: script {len(sw)} words vs recognised {len(words)}; keeping recognised text")
    for i, w in enumerate(words):
        w.update(i=i, start=round(float(w["start"]), 3), end=round(float(w["end"]), 3))
    out = {"source": eng, "audio": os.path.basename(a.wav), "audio_duration_sec": round(dur(a.wav), 3),
           "words": words}
    json.dump(out, open(os.path.join(a.out_dir, "words.json"), "w"), indent=1)
    print(f"{eng}: {len(words)} words -> {a.out_dir}/words.json")


if __name__ == "__main__":
    main()
