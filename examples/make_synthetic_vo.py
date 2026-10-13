#!/usr/bin/env python3
"""Smoke-test helper: synthetic words.json + quiet tone WAV (no TTS, no real voice).
Usage: python make_synthetic_vo.py "text ..." out_dir [--wpm 160]"""
import json, math, os, struct, sys, wave
text, out = sys.argv[1], sys.argv[2]
os.makedirs(out, exist_ok=True)
wpm = 160; t = 0.3; words = []
for i, w in enumerate(text.split()):
    d = max(0.18, 60 / wpm * (0.6 + len(w) / 8))
    words.append({"i": i, "text": w, "start": round(t, 3), "end": round(t + d * 0.85, 3)})
    t += d + (0.25 if w[-1] in ".?!" else 0.08 if w[-1] == "," else 0)
dur = t + 0.3; sr = 48000
with wave.open(f"{out}/voiceover.wav", "wb") as wv:
    wv.setnchannels(1); wv.setsampwidth(2); wv.setframerate(sr)
    on = [(w["start"], w["end"]) for w in words]
    fr = bytearray()
    for n in range(int(dur * sr)):
        s = n / sr; a = 0.08 if any(a0 <= s <= b0 for a0, b0 in on) else 0.0
        fr += struct.pack("<h", int(32767 * a * math.sin(2 * math.pi * 220 * s)))
    wv.writeframes(bytes(fr))
json.dump({"source": "synthetic", "audio": "voiceover.wav", "audio_duration_sec": round(dur, 3), "words": words},
          open(f"{out}/words.json", "w"), indent=1)
print(f"{len(words)} words, {dur:.2f}s -> {out}")
