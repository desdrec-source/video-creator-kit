#!/usr/bin/env python3
"""words.json -> phrase cards (3-7 words), each with a visual system.

Rules (from the production renderers):
  * break on sentence punctuation, then on commas once >=3 words, hard cap 7
  * merge stragglers (<3 words) into the neighbour
  * a card holds until its last word ends + 150 ms (TAIL)
  * visual system chosen from cue words; never the same system twice in a row
Usage: python cards.py words.json cards.json   (renderers also import this)
"""
import json, re, sys

TAIL = 0.15
MIN_W, MAX_W = 3, 7
CUE_RULES = [  # (regex on card text, system)
    (r"\d|percent|%|twice|half|double", "stat-burst"),
    (r"\b(one|two|three|first|second|third|step|piece|fix)\b", "icon-diagram"),
    (r"\b(post|feed|scroll|inbox|dm|message|email|comment)s?\b", "ui-mock"),
    (r"\b(not|never|stop|wrong|ignored?|fail)\b", "cross-out"),
    (r"\?$", "question"),
]
FALLBACK = ["type-only", "underline", "type-only", "highlight"]


def norm(s):
    return re.sub(r"[^a-z0-9%']", "", s.lower())


def split_cards(words):
    cards, cur = [], []
    for w in words:
        cur.append(w)
        t = w["text"]
        if len(cur) >= MAX_W or re.search(r"[.!?]$", t) or (re.search(r"[,;:—-]$", t) and len(cur) >= MIN_W):
            cards.append(cur); cur = []
    if cur:
        cards.append(cur)
    out = []
    for c in cards:  # merge short
        if out and len(c) < MIN_W and len(out[-1]) + len(c) <= MAX_W + 1:
            out[-1] += c
        else:
            out.append(c)
    if len(out) > 1 and len(out[0]) < MIN_W:
        out[1] = out[0] + out[1]; out.pop(0)
    return out


def choose_system(text, prev):
    for rx, sysname in CUE_RULES:
        if re.search(rx, text.lower()) and sysname != prev:
            return sysname
    for s in FALLBACK:
        if s != prev:
            return s
    return "type-only"


def build_cards(words_json):
    wj = json.load(open(words_json)) if isinstance(words_json, str) else words_json
    cards, prev = [], None
    for i, ws in enumerate(split_cards(wj["words"])):
        text = " ".join(w["text"] for w in ws)
        sysname = choose_system(text, prev); prev = sysname
        # accent word = longest content word (renderer colours it)
        accent = max(range(len(ws)), key=lambda k: len(norm(ws[k]["text"])))
        cards.append({"idx": i, "text": text, "words": ws, "start": ws[0]["start"],
                      "end": ws[-1]["end"] + TAIL, "system": sysname, "accent": accent})
    for a, b in zip(cards, cards[1:]):  # never overlap the next card's first word
        a["end"] = min(a["end"], b["start"] + 0.12)
    return cards


if __name__ == "__main__":
    cs = build_cards(sys.argv[1])
    for c in cs:
        print(f"{c['start']:6.2f}-{c['end']:6.2f} {c['system']:12s} {c['text']}")
    if len(sys.argv) > 2:
        json.dump([{k: v for k, v in c.items()} for c in cs], open(sys.argv[2], "w"), indent=1)
