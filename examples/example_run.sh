#!/usr/bin/env bash
# End-to-end: script -> VO -> words.json -> render -> mux.
# MODE=fish (needs FISH_AUDIO_API_KEY + FISH_VOICE_ID), MODE=own VO=path/to/your.wav,
# or MODE=smoke (synthetic tone, no API). STYLE=tech_mono|brand
set -euo pipefail
KIT="$(cd "$(dirname "$0")/.." && pwd)"
MODE="${MODE:-smoke}"; STYLE="${STYLE:-tech_mono}"; OUT="${OUT:-$KIT/out}"
SCRIPT="${SCRIPT:-$KIT/examples/example_script.txt}"
mkdir -p "$OUT"
case "$MODE" in
  fish)  python3 "$KIT/src/fish_tts.py" "$SCRIPT" "$OUT" --speed "${SPEED:-0.88}" ;;
  own)   ffmpeg -y -loglevel error -i "$VO" -ar 48000 "$OUT/voiceover.wav"
         python3 "$KIT/src/align.py" "$OUT/voiceover.wav" "$OUT" --script "$SCRIPT" ;;
  smoke) python3 "$KIT/examples/make_synthetic_vo.py" "$(cat "$SCRIPT")" "$OUT" ;;
esac
R="$KIT/src/render_tech_mono.py"; [ "$STYLE" = brand ] && R="$KIT/src/render_brand.py"
UL=(); [ -n "${UNDERLAYS:-}" ] && UL=(--underlays "$UNDERLAYS")
python3 "$R" "$OUT/words.json" "$OUT/video_only.mp4" --work "$OUT/work" "${UL[@]}"
python3 "$KIT/src/mux.py" "$OUT/video_only.mp4" "$OUT/voiceover.wav" "$OUT/final.mp4"
echo "Done: $OUT/final.mp4"
