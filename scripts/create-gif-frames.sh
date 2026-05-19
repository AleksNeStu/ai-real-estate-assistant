#!/bin/bash
# Create individual GIF frames for slideshow

cd "$(dirname "$0")/.." || exit 1

FRAMES=(
  "01:home"
  "02:search"
  "03:chat"
  "04:analytics"
  "05:favorites"
  "06:city-overview"
  "07:agents"
  "08:knowledge"
  "09:documents"
  "10:settings"
)

for frame in "${FRAMES[@]}"; do
  num="${frame%%:*}"
  name="${frame##*:}"
  input="assets/screenshots/${num}-${name}-dark.png"
  output="assets/screenshots/frame${num}.gif"

  echo "Creating $output..."
  ffmpeg -y -loop 1 -i "$input" \
    -vf "scale=640x400:force_original_aspect_ratio=decrease,pad=640:400:(ow-iw)/2:(oh-ih)/2" \
    -t 1.5 \
    "$output" 2>&1 | tail -3
done

echo "All frames created. Now concatenating..."

# Concatenate all GIFs
ffmpeg -y -i "assets/screenshots/frame01.gif" \
  -i "assets/screenshots/frame02.gif" \
  -i "assets/screenshots/frame03.gif" \
  -i "assets/screenshots/frame04.gif" \
  -i "assets/screenshots/frame05.gif" \
  -i "assets/screenshots/frame06.gif" \
  -i "assets/screenshots/frame07.gif" \
  -i "assets/screenshots/frame08.gif" \
  -i "assets/screenshots/frame09.gif" \
  -i "assets/screenshots/frame10.gif" \
  -filter_complex "[0:v][1:v][2:v][3:v][4:v][5:v][6:v][7:v][8:v][9:v]concat=n=10:v=1[a]" \
  -map "[a]" "assets/screenshots/slideshow.gif" 2>&1 | tail -10

echo "Slideshow created: assets/screenshots/slideshow.gif"
