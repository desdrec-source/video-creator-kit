# Video Creator — starter kit

Kinetic-typography explainer videos driven by **word timestamps**: every word lands on screen exactly when it's spoken. Two looks out of the box:

- **Tech Mono** — off-white dot grid, IBM Plex Mono, one electric-blue accent, editorial ease, optional video underlays.
- **Brand** — your palette, fonts, logo and end card from a JSON file (`styles/brand_example.json` is a neutral placeholder — replace it).

Pipeline: **script → voiceover (Fish Audio or your own) → words.json → render → mux** into a bulletproof MP4 (H.264 High@4.0 yuv420p 30 fps CFR, AAC-LC stereo 48 kHz, +faststart, checked with ffprobe).

## Download
```bash
git clone https://github.com/desdrec-source/video-creator-kit.git
cd video-creator-kit
bash install.sh                                 # pip install, ffmpeg check, unpack fonts + logo
MODE=smoke bash examples/example_run.sh         # -> out/final.mp4, no API key needed
```

You can also use the zip: download https://github.com/desdrec-source/video-creator-kit/archive/refs/heads/main.zip, unzip it, and run `bash install.sh`.

Fonts and the placeholder logo ship base64-packed in `packed/`. `install.sh` rebuilds them into `assets/` and checks each SHA-256.

## Prerequisites
- Python 3.10+, `ffmpeg` + `ffprobe` on PATH
- `bash install.sh` (or `pip install -r requirements.txt` then `python3 tools/unpack_assets.py`)
- Optional (own voiceover): `pip install whisperx` (best timing) or `pip install openai-whisper`

## Quickstart
```bash
# 0) no API needed: synthetic tone + fake timings, proves the toolchain works
MODE=smoke bash examples/example_run.sh         # -> out/final.mp4

# 1) Fish Audio voice
export FISH_AUDIO_API_KEY=...   # your key, never commit it
export FISH_VOICE_ID=...        # reference_id of a voice you own/are licensed for
MODE=fish SCRIPT=my_script.txt bash examples/example_run.sh

# 2) your own recorded voiceover
MODE=own VO=my_vo.wav SCRIPT=my_script.txt bash examples/example_run.sh

# brand look
STYLE=brand MODE=smoke bash examples/example_run.sh
```

### Step by step
| Step | Command |
|---|---|
| VO + timings (Fish) | `python src/fish_tts.py script.txt out/ --speed 0.88` → `out/voiceover.wav`, `out/words.json` |
| Timings (own VO) | `python src/align.py my_vo.wav out/ --script script.txt --model small.en` |
| Inspect cards | `python src/cards.py out/words.json` |
| Preview stills | `python src/render_tech_mono.py out/words.json out/v.mp4 --preview 2 5.5 9` (JPGs in `work/`) |
| Render | `python src/render_tech_mono.py out/words.json out/video_only.mp4` (or `render_brand.py --style styles/my_brand.json`) |
| Mux | `python src/mux.py out/video_only.mp4 out/voiceover.wav out/final.mp4` |

## How it works
- **fish_tts.py** calls `POST /v1/tts/stream/with-timestamp` and saves the raw SSE stream. Fish sends alignment per text chunk with times *relative to the chunk*; absolute word time = `segment.start + chunk_audio_offset_sec` (latest snapshot per `chunk_seq` wins). Default `speed` 0.88 reads well for explainers. `--parse saved.raw` re-parses offline.
- **align.py** gives the same `words.json` schema from your own recording (whisperx forced alignment, falls back to whisper `word_timestamps`). With `--script`, recognised words are snapped to your script spelling when counts match.
- **cards.py** groups words into 3–7-word phrase cards (sentence/comma breaks), holds each until last word +150 ms, and picks a visual system from cue words (numbers → stat-burst, steps/first/three → icon-diagram, post/feed/inbox → ui-mock, not/never → cross-out, `?` → question, else underline/highlight/type-only), never repeating back-to-back. Edit `CUE_RULES` to taste.
- **kinetic.py** (shared engine) renders 1920×1080 frames in parallel: words rise in on an expo ease at their timestamp, one accent word per card, slow camera push, progress bar, end card.

`words.json` schema: `{"audio_duration_sec": 12.3, "words": [{"i":0,"text":"Why","start":0.30,"end":0.52}, ...]}`

## Style presets
- **Tech Mono** (`styles/tech_mono.json`, `src/render_tech_mono.py`): off-white dot grid, IBM Plex Mono, one #2B6CFF accent, blur-in type (`"type_in": "blur"`), slot swaps on the accent word (`"slot_swap": true`), UI cards for post/inbox/comment lines, and hand-drawn underlines and cross-outs (`"accents": "hand-drawn"`).
- **Brand example** (`styles/brand_example.json`, `src/render_brand.py`): a neutral placeholder. Copy it, then set your own palette, fonts, logo and end-card copy.

Both presets use a 10 s end-card hold (allowed range 8-12 s). Every preset goes through the style gate before rendering. A bad colour, a missing font or logo, or an out-of-range hold stops the render with a list of what to fix. See `docs/DEFAULTS.md` for all the settled defaults.

## Style config (`styles/*.json`)
`palette` (bg, bg2, grid, ink, ink_on_dark, accent, muted, panel, underlay_tint), `fonts.head/body` (`file`, optional `variation` for variable fonts e.g. "ExtraBold"), `background.type` (`dot-grid` | `gradient` | `solid`), `uppercase`, `tracking`, `type_size` [max,min], `camera_push`, `end_hold_sec` (8-12), `type_in` (`rise` | `blur`), `slot_swap`, `accents` (`clean` | `hand-drawn`), `chrome` (progress_bar, label, timecode), `logo` (PNG with transparency; path relative to kit), `end_card` (title, cta). Keep **one** accent colour — it's what makes the look.

## Video underlays from Pexels
1. Find clips on https://www.pexels.com/videos/ (or the free API: https://www.pexels.com/api/ — key in `PEXELS_API_KEY`). Download HD MP4s into your own project folder.
2. Write `underlays.json`: `[{"card": 0, "clip": "clips/typing.mp4", "in": 2.0, "darken": 0.6}]` — `card` is the index printed by the renderer, `in` the source start second, `darken` the blend toward `underlay_tint`. Text switches to `ink_on_dark` while an underlay is up.
3. `python src/render_tech_mono.py out/words.json out/video_only.mp4 --underlays underlays.json`

Pexels Licence: free to use and modify in your videos, attribution appreciated not required; don't redistribute clips as-is or sell unaltered copies. That's why no clips ship with this kit.

## Notes
- Fonts bundled are SIL OFL 1.1 (see `LICENCES.md`). Want a different font? Drop a TTF you're licensed for in `assets/fonts/` and point the style at it.
- No voice, no logo, no stock media from anyone else ships here — bring your own.

Made for the AI Video Motion community. MIT licence.
