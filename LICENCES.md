# Third-party licences

The kit's own code (everything in `src/`, `examples/`, `styles/`) is MIT — see `LICENSE`.

| Item | Source | Licence | File(s) | Redistribution OK |
|---|---|---|---|---|
| IBM Plex Mono (Regular, Medium, SemiBold, Bold) | https://github.com/IBM/plex · https://fonts.google.com/specimen/IBM+Plex+Mono | SIL OFL 1.1 (Reserved Font Name "Plex") | `assets/fonts/IBMPlexMono-*.ttf`, `assets/fonts/OFL-IBMPlexMono.txt` | Yes (with OFL text; don't sell the font on its own; renamed modifications only) |
| Inter (variable) | https://github.com/rsms/inter · https://fonts.google.com/specimen/Inter | SIL OFL 1.1 | `assets/fonts/Inter-VariableFont.ttf`, `assets/fonts/OFL-Inter.txt` | Yes (with OFL text) |
| Montserrat (variable) | https://github.com/JulietaUla/Montserrat · https://fonts.google.com/specimen/Montserrat | SIL OFL 1.1 | `assets/fonts/Montserrat-VariableFont.ttf`, `assets/fonts/OFL-Montserrat.txt` | Yes (with OFL text) |
| SIL OFL 1.1 text | https://openfontlicense.org | — | `assets/fonts/OFL.txt` | Yes |
| Placeholder logo (rounded square + play triangle) | Drawn programmatically for this kit | MIT (kit) | `assets/icons/placeholder_logo.png` | Yes |
| On-screen icons/diagrams (step circles, UI-mock card, underline, cross-out) | Drawn in code at render time (`src/kinetic.py`) | MIT (kit) | — | Yes |

## Not bundled — you fetch / supply these yourself
| Item | Licence / terms | Notes |
|---|---|---|
| Pexels stock video (underlays) | Pexels Licence — https://www.pexels.com/license/ | Free to use and modify in your videos; do **not** redistribute clips as stand-alone files or sell unaltered copies. Download your own; not included in the kit. |
| Fish Audio TTS output | Fish Audio terms — https://fish.audio | Use only voices you own or are licensed to use. Your API key stays in your env. |
| Python deps (numpy BSD-3, Pillow MIT-CMU, requests Apache-2.0, whisper MIT, whisperx BSD-2) | via pip | Installed by the user, not vendored. |
| ffmpeg | LGPL/GPL | Installed by the user, not vendored. |
