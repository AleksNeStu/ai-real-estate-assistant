#!/bin/bash
cd "$(dirname "$0")/.." || exit 1

# Create optimized GIF slideshow from screenshots
# Target: < 500KB, 10 screenshots, ~15 seconds total

ffmpeg -y \
  -i assets/screenshots/01-home-dark.png \
  -i assets/screenshots/02-search-dark.png \
  -i assets/screenshots/03-chat-dark.png \
  -i assets/screenshots/04-analytics-dark.png \
  -i assets/screenshots/05-favorites-dark.png \
  -i assets/screenshots/06-city-overview-dark.png \
  -i assets/screenshots/07-agents-dark.png \
  -i assets/screenshots/08-knowledge-dark.png \
  -i assets/screenshots/09-documents-dark.png \
  -i assets/screenshots/10-settings-dark.png \
  -filter_complex \
    "[0:v]scale=640:400:force_original_aspect_ratio=decrease,pad=640:400:(ow-iw)/2:(oh-ih)/2,split=2[v0][v1];[v0]palettegen=max_colors=64:reserve_transparent=on[p];[v1][p]paletteuse" \
  -frames:v 1 \
  assets/screenshots/slideshow.gif 2>&1 | tail -10

ls -lh assets/screenshots/slideshow.gif
