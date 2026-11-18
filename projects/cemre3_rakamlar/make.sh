#!/usr/bin/env bash
# Rebuild the Cemre 3 stats reel end to end.
#   ./make.sh <source-media-dir>      (dir with full/<key>.jpg and vid/<key>.<ext> from Drive)
#   ./make.sh                         (reuse already prepared assets)
set -euo pipefail
cd "$(dirname "$0")"
HERE=$(pwd)
NODE_DIR="$HERE/../../reels/node"

python3 tools/timing.py
if [ "${1:-}" != "" ]; then python3 tools/prep.py "$1"; fi
python3 tools/sound.py

mkdir -p out
( cd "$NODE_DIR" && HYPERFRAMES_SKIP_SKILLS=1 npx --no-install hyperframes lint "$HERE" )
( cd "$NODE_DIR" && HYPERFRAMES_SKIP_SKILLS=1 npx --no-install hyperframes render "$HERE" \
    --fps 30 --quality delivery --quiet -o "$HERE/out/video_silent.mp4" < /dev/null )

# -14 LUFS; master to WAV first so the AAC encode stays under -1 dBTP
ffmpeg -v error -y -i audio/mix.wav -af "loudnorm=I=-14:TP=-2:LRA=11,alimiter=limit=0.75:level=false:attack=1:release=60" \
  -ar 48000 audio/mix_master.wav
VENC="-c:v libx264 -preset slow -crf 18 -pix_fmt yuv420p -profile:v high"
# Main version: temporary music + effects
ffmpeg -v error -y -i out/video_silent.mp4 -i audio/mix_master.wav -map 0:v -map 1:a $VENC \
  -c:a aac -b:a 256k -ar 48000 -shortest -movflags +faststart out/cemre3_rakamlar.mp4
# _SESSIZ: effects only, for adding a song inside Instagram
ffmpeg -v error -y -i out/cemre3_rakamlar.mp4 -i audio/sfx.wav -map 0:v -map 1:a -c:v copy \
  -af "volume=-6dB" -c:a aac -b:a 192k -ar 48000 -shortest -movflags +faststart out/cemre3_rakamlar_SESSIZ.mp4
python3 tools/review.py out/cemre3_rakamlar.mp4 out/review_sheet.jpg
echo "done: out/cemre3_rakamlar.mp4, out/cemre3_rakamlar_SESSIZ.mp4, out/review_sheet.jpg"
