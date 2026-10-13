"""Shared kinetic-typography engine used by render_tech_mono.py and render_brand.py.

Everything visual comes from a style JSON (styles/*.json); everything timed
comes from words.json. No content is hard-coded.
"""
import json, math, os, re, subprocess, sys
from functools import lru_cache
from multiprocessing import Pool

import numpy as np
from PIL import Image, ImageDraw, ImageFilter, ImageFont

from cards import build_cards, norm

KIT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
W, H, FPS = 1920, 1080, 30
F1 = 1 / FPS
ENTER, STAGGER, RISE, EXIT = 0.40, 2 * F1, 28, 0.25


# ---------- easing ----------
def _bez(p1x, p1y, p2x, p2y):
    def f(t):
        if t <= 0: return 0.0
        if t >= 1: return 1.0
        lo, hi = 0.0, 1.0
        for _ in range(30):
            m = (lo + hi) / 2
            x = 3 * (1 - m) ** 2 * m * p1x + 3 * (1 - m) * m * m * p2x + m ** 3
            lo, hi = (m, hi) if x < t else (lo, m)
        m = (lo + hi) / 2
        return 3 * (1 - m) ** 2 * m * p1y + 3 * (1 - m) * m * m * p2y + m ** 3
    return f


EXPO = _bez(0.16, 1, 0.3, 1)
c01 = lambda x: max(0.0, min(1.0, x))
ease_in = lambda t: c01(t) ** 3


def back(t, c1=1.4):
    t = c01(t); c3 = c1 + 1
    return 1 + c3 * (t - 1) ** 3 + c1 * (t - 1) ** 2


# ---------- style ----------
def hexrgb(h):
    h = h.lstrip("#"); return tuple(int(h[i:i + 2], 16) for i in (0, 2, 4))


END_HOLD_RANGE = (8.0, 12.0)
REQUIRED_PALETTE = ("bg", "ink", "accent", "muted")


def style_gate(s, path="style"):
    """Reject a style JSON before any frame is rendered. Raises SystemExit listing every problem."""
    errs = []
    pal = s.get("palette", {})
    for k in REQUIRED_PALETTE:
        if k not in pal:
            errs.append(f"palette.{k} missing")
    for k, v in pal.items():
        if not re.fullmatch(r"#[0-9A-Fa-f]{6}", str(v)):
            errs.append(f"palette.{k}={v!r} is not #RRGGBB")
    for role in ("head", "body"):
        f = s.get("fonts", {}).get(role, {}).get("file")
        if not f:
            errs.append(f"fonts.{role}.file missing")
        elif not os.path.exists(f if os.path.isabs(f) else os.path.join(KIT, f)):
            errs.append(f"fonts.{role}.file not found: {f}")
    hold = float(s.get("end_hold_sec", 10.0))
    if not END_HOLD_RANGE[0] <= hold <= END_HOLD_RANGE[1]:
        errs.append(f"end_hold_sec={hold} outside {END_HOLD_RANGE[0]:g}-{END_HOLD_RANGE[1]:g} s")
    ts = s.get("type_size", [150, 70])
    if len(ts) != 2 or not (40 <= ts[1] <= ts[0] <= 300):
        errs.append(f"type_size={ts} must be [max, min] with 40 <= min <= max <= 300")
    if s.get("type_in", "rise") not in ("rise", "blur"):
        errs.append("type_in must be 'rise' or 'blur'")
    if s.get("accents", "clean") not in ("clean", "hand-drawn"):
        errs.append("accents must be 'clean' or 'hand-drawn'")
    lg = s.get("logo")
    if lg and not os.path.exists(lg if os.path.isabs(lg) else os.path.join(KIT, lg)):
        errs.append(f"logo not found: {lg}")
    if errs:
        sys.exit(f"style gate FAILED for {path}:\n  - " + "\n  - ".join(errs))


class Style:
    def __init__(self, path):
        s = json.load(open(path))
        style_gate(s, path)
        self.raw = s
        self.name = s.get("name", os.path.basename(path))
        self.c = {k: hexrgb(v) for k, v in s["palette"].items()}
        self.fonts = s["fonts"]
        self.bg = s.get("background", {"type": "solid"})
        self.uppercase = s.get("uppercase", False)
        self.tracking = s.get("tracking", 0)
        self.size_max, self.size_min = s.get("type_size", [150, 70])
        self.logo = s.get("logo")
        self.end = s.get("end_card", {})
        self.end_hold = float(s.get("end_hold_sec", 10.0))
        self.type_in = s.get("type_in", "rise")        # "blur" = blur-in type
        self.slot_swap = bool(s.get("slot_swap", False))  # accent word rolls in like a slot reel
        self.hand = s.get("accents", "clean") == "hand-drawn"
        self.camera_push = float(s.get("camera_push", 0.03))
        self.chrome = s.get("chrome", {})

    def font(self, role, size):
        return _font(self.fonts[role]["file"], self.fonts[role].get("variation"), int(size))


@lru_cache(maxsize=256)
def _font(file, variation, size):
    p = file if os.path.isabs(file) else os.path.join(KIT, file)
    f = ImageFont.truetype(p, size)
    if variation:
        try: f.set_variation_by_name(variation)
        except Exception: pass
    return f


# ---------- layout ----------
def layout_card(card, st):
    toks = [w["text"].upper() if st.uppercase else w["text"] for w in card["words"]]
    maxw = W * 0.78
    for size in range(st.size_max, st.size_min - 1, -4):
        f = st.font("head", size)
        sp = f.getlength(" ")
        lines, cur, cw = [], [], 0
        for i, t in enumerate(toks):
            tw = f.getlength(t) + st.tracking * len(t)
            if cur and cw + sp + tw > maxw:
                lines.append(cur); cur, cw = [], 0
            cur.append((i, t, tw)); cw += (sp if len(cur) > 1 else 0) + tw
        lines.append(cur)
        if len(lines) <= 3:
            break
    lh = size * 1.12
    top = H / 2 - lh * len(lines) / 2 + (40 if card["system"] in ("stat-burst", "icon-diagram") else 0)
    if card["system"] in ("stat-burst", "icon-diagram", "ui-mock"):
        top += 120
    placed = []
    for li, ln in enumerate(lines):
        lw = sum(t[2] for t in ln) + sp * (len(ln) - 1)
        x = (W - lw) / 2
        for i, t, tw in ln:
            placed.append({"i": i, "text": t, "x": x, "y": top + li * lh, "w": tw})
            x += tw + sp
    card["layout"] = {"size": size, "tokens": placed, "lh": lh, "top": top}
    return card


# ---------- background & underlays ----------
@lru_cache(maxsize=1)
def _grid(st_key, bg, dot, spacing):
    im = Image.new("RGB", (W + 2 * spacing, H + 2 * spacing), bg)
    d = ImageDraw.Draw(im)
    for y in range(0, im.height, spacing):
        for x in range(0, im.width, spacing):
            d.ellipse([x - 2, y - 2, x + 2, y + 2], fill=dot)
    return im


def background(st, t):
    b = st.bg
    if b.get("type") == "dot-grid":
        sp = int(b.get("spacing", 80))
        g = _grid(st.name, st.c["bg"], st.c.get("grid", st.c["muted"]), sp)
        dx = int((t * 12) % sp)
        return g.crop((dx, sp // 2, dx + W, sp // 2 + H))
    if b.get("type") == "gradient":
        top, bot = np.array(st.c["bg"]), np.array(st.c.get("bg2", st.c["bg"]))
        a = np.linspace(0, 1, H)[:, None, None]
        arr = (top * (1 - a) + bot * a).astype(np.uint8)
        return Image.fromarray(np.repeat(arr, W, axis=1))
    return Image.new("RGB", (W, H), st.c["bg"])


class Underlays:
    """Optional video underlays: {"card": idx, "clip": path, "darken": 0.55}.
    Clips are pre-extracted to frames once (scaled/cropped to 1920x1080)."""

    def __init__(self, spec, work, cards):
        self.items = []
        for u in spec or []:
            idx = u["card"]
            if idx >= len(cards):
                continue
            c = cards[idx]
            d = os.path.join(work, f"underlay_{idx:02d}")
            n = int(math.ceil((c["end"] - c["start"] + 1.0) * FPS))
            if not os.path.isdir(d) or len(os.listdir(d)) < n:
                os.makedirs(d, exist_ok=True)
                subprocess.check_call(["ffmpeg", "-y", "-loglevel", "error", "-ss", str(u.get("in", 0)),
                                       "-i", u["clip"], "-vf",
                                       f"fps={FPS},scale={W}:{H}:force_original_aspect_ratio=increase,crop={W}:{H}",
                                       "-frames:v", str(n), "-q:v", "3", f"{d}/%05d.jpg"])
            self.items.append({"card": idx, "dir": d, "start": c["start"] - 0.3, "end": c["end"],
                               "darken": float(u.get("darken", 0.55)), "n": len(os.listdir(d))})

    def frame(self, t, st):
        for u in self.items:
            if u["start"] <= t <= u["end"] + 0.3:
                k = min(u["n"], max(1, int((t - u["start"]) * FPS) + 1))
                im = Image.open(f"{u['dir']}/{k:05d}.jpg").convert("RGB")
                a = c01((t - u["start"]) / 0.3) * c01((u["end"] + 0.3 - t) / 0.3)
                tint = Image.new("RGB", (W, H), st.c.get("underlay_tint", st.c["bg"]))
                im = Image.blend(im, tint, u["darken"])
                return im, a
        return None, 0.0


# ---------- drawing ----------
def draw_tokens(L, card, st, t, on_dark):
    lay = card["layout"]; f = st.font("head", lay["size"])
    d = ImageDraw.Draw(L)
    ink = st.c["ink_on_dark"] if on_dark else st.c["ink"]
    exit_p = ease_in((t - card["end"]) / EXIT)
    for tk in lay["tokens"]:
        w = card["words"][tk["i"]]
        t0 = w["start"] - 2 * F1
        p = EXPO(c01((t - t0) / ENTER))
        if p <= 0:
            continue
        a = int(255 * c01(p * 1.6) * (1 - exit_p))
        y = tk["y"] + RISE * (1 - p) - 28 * exit_p
        is_acc = tk["i"] == card["accent"]
        col = st.c["accent"] if is_acc else ink
        slot = st.slot_swap and is_acc
        blur = st.type_in == "blur" and p < 1
        if not (slot or blur):
            _glyphs(d, tk, f, st, y + lay["size"] * 0.8, col, a)
            continue
        # per-word layer for blur-in / slot swap
        pad = int(lay["size"] * 0.4)
        bw, bh = int(tk["w"] + 2 * pad), int(lay["lh"] + 2 * pad)
        wl = Image.new("RGBA", (bw, bh), (0, 0, 0, 0))
        oy = pad + (lay["lh"] * (1 - p) if slot else RISE * (1 - p))
        _glyphs(ImageDraw.Draw(wl), {"x": pad, "text": tk["text"]}, f, st, oy + lay["size"] * 0.8, col, a)
        if slot:  # clip to the line slot so the word rolls up into place
            m = Image.new("L", (bw, bh), 0)
            ImageDraw.Draw(m).rectangle([0, pad - 6, bw, pad + lay["lh"] + 6], fill=255)
            wl.putalpha(Image.fromarray(np.minimum(np.array(wl.getchannel("A")), np.array(m))))
        if blur:
            wl = wl.filter(ImageFilter.GaussianBlur(14 * (1 - p)))
        L.alpha_composite(wl, (int(tk["x"] - pad), int(tk["y"] - 28 * exit_p - pad)))
    return exit_p


def _glyphs(d, tk, f, st, baseline, col, a):
    x = tk["x"]
    for ch in tk["text"]:
        d.text((x, baseline), ch, font=f, fill=col + (a,), anchor="ls")
        x += f.getlength(ch) + st.tracking


def _stroke(d, st, pts, fill, width, seed):
    """Straight line, or a wobbly hand-drawn marker stroke when accents == 'hand-drawn'."""
    if not st.hand or len(pts) < 2:
        d.line(pts, fill=fill, width=width); return
    rng = np.random.default_rng(seed)
    (x0, y0), (x1, y1) = pts[0], pts[-1]
    n = max(4, int(abs(x1 - x0) / 40))
    xs = np.linspace(x0, x1, n); ys = np.linspace(y0, y1, n) + rng.normal(0, width * 0.35, n)
    ys += np.sin(np.linspace(0, math.pi, n)) * width * 0.6
    d.line(list(zip(xs.tolist(), ys.tolist())), fill=fill, width=width, joint="curve")


def deco(L, card, st, t, exit_p):
    """System-specific accents, all drawn in the single accent colour."""
    d = ImageDraw.Draw(L)
    lay = card["layout"]; A = st.c["accent"]; s = card["system"]
    alpha = int(255 * (1 - exit_p))
    acc = next(tk for tk in lay["tokens"] if tk["i"] == card["accent"])
    aw = card["words"][card["accent"]]
    pa = EXPO(c01((t - aw["end"] + 0.05) / 0.35))
    by = acc["y"] + lay["size"] * 1.02
    if s == "underline":
        if st.hand:
            _stroke(d, st, [(acc["x"], by + 5), (acc["x"] + acc["w"] * pa, by + 5)], A + (alpha,), 11, card["idx"])
        else:
            d.rectangle([acc["x"], by, acc["x"] + acc["w"] * pa, by + 10], fill=A + (alpha,))
    elif s == "highlight":
        d.rectangle([acc["x"] - 10, acc["y"] - 4, acc["x"] - 10 + (acc["w"] + 20) * pa, by], fill=A + (int(alpha * 0.18),))
    elif s == "cross-out":
        neg = next((tk for tk in lay["tokens"] if re.match(r"(not|never|stop|wrong|ignored?|fail)", norm(card["words"][tk["i"]]["text"]))), acc)
        nw = card["words"][neg["i"]]; pn = EXPO(c01((t - nw["end"]) / 0.3))
        my = neg["y"] + lay["size"] * 0.55
        _stroke(d, st, [(neg["x"] - 6, my), (neg["x"] - 6 + (neg["w"] + 12) * pn, my)], A + (alpha,), 12, card["idx"] + 99)
    elif s == "stat-burst":
        num = next((w["text"] for w in card["words"] if re.search(r"\d", w["text"])), None)
        label = re.sub(r"[^\d%x.]", "", num) if num else "!"
        p = back(c01((t - card["start"]) / 0.45))
        f = st.font("head", int(260 * max(0.01, p)))
        d.text((W / 2, lay["top"] - 170), label, font=f, fill=A + (alpha,), anchor="mm")
    elif s == "icon-diagram":
        n = 3; cx = [W / 2 - 300, W / 2, W / 2 + 300]
        for k in range(n):
            pk = back(c01((t - card["start"] - k * 0.12) / 0.4))
            r = 46 * pk
            y = lay["top"] - 150
            if k < n - 1:
                pl = EXPO(c01((t - card["start"] - k * 0.12 - 0.2) / 0.4))
                d.line([cx[k] + 50, y, cx[k] + 50 + 200 * pl, y], fill=st.c["muted"] + (alpha,), width=5)
            d.ellipse([cx[k] - r, y - r, cx[k] + r, y + r], outline=A + (alpha,), width=8)
            if pk > 0.3:
                d.text((cx[k], y), str(k + 1), font=st.font("body", 44), fill=A + (alpha,), anchor="mm")
    elif s == "ui-mock":
        p = EXPO(c01((t - card["start"]) / 0.45))
        pw, ph = 760, 200; x0 = (W - pw) / 2; y0 = lay["top"] - 260 + 40 * (1 - p)
        a = int(alpha * p)
        d.rounded_rectangle([x0, y0, x0 + pw, y0 + ph], 22, fill=st.c["panel"] + (a,), outline=st.c["muted"] + (a // 2,), width=2)
        d.ellipse([x0 + 30, y0 + 30, x0 + 90, y0 + 90], fill=st.c["muted"] + (a // 2,))
        for k, ln in enumerate([0.55, 0.8, 0.4]):
            d.rounded_rectangle([x0 + 120, y0 + 38 + k * 46, x0 + 120 + (pw - 160) * ln, y0 + 58 + k * 46], 8,
                                fill=(A if k == 1 else st.c["muted"]) + (int(a * (0.9 if k == 1 else 0.4)),))
    elif s == "question":
        p = back(c01((t - card["words"][-1]["end"] + 0.1) / 0.4))
        d.text((W - 260, H / 2), "?", font=st.font("head", int(320 * max(0.01, p))), fill=A + (int(alpha * 0.25),), anchor="mm")


def chrome(L, st, t, total):
    d = ImageDraw.Draw(L)
    ch = st.chrome
    if ch.get("progress_bar", True):
        d.rectangle([0, H - 8, W * c01(t / total), H], fill=st.c["accent"] + (220,))
    if ch.get("label"):
        d.text((60, 50), ch["label"], font=st.font("body", 26), fill=st.c["muted"] + (255,))
    if ch.get("timecode"):
        d.text((W - 60, 50), f"{t:05.2f}", font=st.font("body", 26), fill=st.c["muted"] + (255,), anchor="ra")


@lru_cache(maxsize=4)
def _logo(path, h):
    p = path if os.path.isabs(path) else os.path.join(KIT, path)
    im = Image.open(p).convert("RGBA")
    return im.resize((int(im.width * h / im.height), h), Image.Resampling.LANCZOS)


def end_card(L, st, t, t0):
    e = st.end
    if not e or t < t0:
        return
    d = ImageDraw.Draw(L)
    p = EXPO(c01((t - t0) / 0.5)); a = int(255 * p)
    y = H / 2 - 60
    if st.logo and os.path.exists(st.logo if os.path.isabs(st.logo) else os.path.join(KIT, st.logo)):
        lg = _logo(st.logo, 120).copy(); lg.putalpha(lg.getchannel("A").point(lambda v: v * p))
        L.alpha_composite(lg, (int((W - lg.width) / 2), int(y - 200)))
    d.text((W / 2, y + 30 * (1 - p)), e.get("title", ""), font=st.font("head", 110), fill=st.c["ink"] + (a,), anchor="mm")
    d.rectangle([W / 2 - 80 * p, y + 90, W / 2 + 80 * p, y + 98], fill=st.c["accent"] + (a,))
    d.text((W / 2, y + 160), e.get("cta", ""), font=st.font("body", 48), fill=st.c["muted"] + (a,), anchor="mm")


# ---------- frame ----------
G = {}


def render_frame(t):
    st, cards, und, vo_end, total = G["st"], G["cards"], G["und"], G["vo_end"], G["total"]
    base = background(st, t)
    uimg, ua = und.frame(t, st) if und else (None, 0)
    if uimg is not None:
        base = Image.blend(base, uimg, ua)
    on_dark = ua > 0.5 and st.raw.get("underlay_text_light", True)
    L = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    for c in cards:
        if c["start"] - 0.2 <= t <= c["end"] + EXIT:
            ex = draw_tokens(L, c, st, t, on_dark)
            deco(L, c, st, t, ex)
    end_card(L, st, t, vo_end + 0.2)
    # slow camera push on the type layer
    z = 1 + st.camera_push * (t / total)
    if z != 1:
        L = L.resize((int(W * z), int(H * z)), Image.Resampling.BICUBIC)
        ox, oy = (L.width - W) // 2, (L.height - H) // 2
        L = L.crop((ox, oy, ox + W, oy + H))
    chrome(L, st, t, total)
    out = base.convert("RGBA"); out.alpha_composite(L)
    return out.convert("RGB")


def _init(style, words, underlays, work):
    st = Style(style)
    wj = json.load(open(words))
    cards = [layout_card(c, st) for c in build_cards(wj)]
    vo_end = float(wj.get("audio_duration_sec") or cards[-1]["end"])
    G.update(st=st, cards=cards, vo_end=vo_end, total=vo_end + st.end_hold,
             und=Underlays(underlays, work, cards) if underlays else None)


def _rf(i):
    return render_frame(i / FPS).tobytes()


def main(default_style):
    import argparse
    ap = argparse.ArgumentParser()
    ap.add_argument("words"); ap.add_argument("out_video", help="video-only MP4 (mux audio with mux.py)")
    ap.add_argument("--style", default=os.path.join(KIT, "styles", default_style))
    ap.add_argument("--underlays", help="JSON list of {card, clip, in, darken}")
    ap.add_argument("--work", default="work")
    ap.add_argument("--preview", nargs="*", type=float, help="write JPG stills at these times and exit")
    ap.add_argument("--jobs", type=int, default=os.cpu_count() or 4)
    a = ap.parse_args()
    os.makedirs(a.work, exist_ok=True)
    und = json.load(open(a.underlays)) if a.underlays else None
    _init(a.style, a.words, und, a.work)
    for c in G["cards"]:
        print(f"#{c['idx']:2d} {c['start']:6.2f}-{c['end']:6.2f} {c['system']:12s} {c['text']}")
    if a.preview is not None:
        for t in a.preview:
            render_frame(t).save(os.path.join(a.work, f"prev_{t:06.2f}.jpg"), quality=88)
        return
    n = int(round(G["total"] * FPS))
    p = subprocess.Popen(["ffmpeg", "-y", "-loglevel", "error", "-f", "rawvideo", "-pix_fmt", "rgb24",
                          "-s", f"{W}x{H}", "-r", str(FPS), "-i", "pipe:0", "-c:v", "libx264", "-preset", "medium",
                          "-crf", "16", "-pix_fmt", "yuv420p", a.out_video], stdin=subprocess.PIPE)
    with Pool(a.jobs, initializer=_init, initargs=(a.style, a.words, und, a.work)) as pool:
        for i, fb in enumerate(pool.imap(_rf, range(n), chunksize=4)):
            p.stdin.write(fb)
            if i % 150 == 0:
                print(f"  frame {i}/{n}", flush=True)
    p.stdin.close()
    if p.wait():
        sys.exit("ffmpeg encode failed")
    print(f"video-only -> {a.out_video} ({n} frames, {G['total']:.2f}s). Next: mux.py")
