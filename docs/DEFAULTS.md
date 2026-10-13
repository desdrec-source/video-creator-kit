# Settled defaults

These are the defaults that came out of production use. The kit ships with all of them switched on.

| Area | Default | Where |
|---|---|---|
| Fish voice speed | **0.88** | `src/fish_tts.py --speed` |
| Phrase cards | **3-7 words**, each held until its last word ends **+150 ms** | `src/cards.py` (`MIN_W`, `MAX_W`, `TAIL`) |
| End-card hold | **8-12 s** (default 10 s) | `end_hold_sec` in `styles/*.json`, checked by the style gate |
| Audio | **Stereo AAC-LC, 48 kHz** | `src/mux.py` |
| Video | **H.264 High@L4.0, yuv420p, 30 fps CFR, +faststart** | `src/mux.py` (checked after muxing) |
| Style gate | Every style JSON is checked before rendering: required palette keys, #RRGGBB colours, font and logo files exist, end hold within 8-12 s, sane `type_size`, valid `type_in`/`accents` | `style_gate()` in `src/kinetic.py` |
| Tech Mono tuning | **#2B6CFF** single accent, **blur-in** type, **slot swaps** on the accent word, **UI cards** (`ui-mock` system), **hand-drawn** underline and cross-out accents | `styles/tech_mono.json` |
