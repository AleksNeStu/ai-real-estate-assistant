#!/usr/bin/env bash
# Builds the six-second demo clip from the three captured scenes.
#
#   bash scripts/utils/build_demo_clip.sh
#
# Reads tmp/clip/{1-landing,2-search,3-chat}.png and writes
# assets/clips/{demo-6s.mp4,demo-6s.gif,poster.png}.
# Needs ffmpeg on the PATH.
set -euo pipefail
ROOT="$(cd "$(dirname "$0")/../.." && pwd)"
FRAMES="$ROOT/tmp/clip"
OUT="$ROOT/assets/clips"
F="ffmpeg -y -loglevel error"

for f in 1-landing 2-search 3-chat; do
  if [ ! -f "$FRAMES/$f.png" ]; then
    echo "missing $FRAMES/$f.png - run: node scripts/utils/capture_demo_clip.js" >&2
    exit 1
  fi
done
mkdir -p "$OUT"

# Three scenes of 2.267 s, two 0.4 s cross-fades -> exactly 6.000 s
$F -loop 1 -i "$FRAMES/1-landing.png" -loop 1 -i "$FRAMES/2-search.png" -loop 1 -i "$FRAMES/3-chat.png" \
 -filter_complex "\
 [0:v]scale=1280:800:force_original_aspect_ratio=increase,crop=1280:800,zoompan=z='min(zoom+0.0007,1.15)':d=68:x='iw/2-(iw/zoom/2)':y='ih/2-(ih/zoom/2)':s=1280x800:fps=30,setsar=1[v0];\
 [1:v]scale=1280:800:force_original_aspect_ratio=increase,crop=1280:800,zoompan=z='min(zoom+0.0007,1.15)':d=68:x='iw/2-(iw/zoom/2)':y='ih/2-(ih/zoom/2)':s=1280x800:fps=30,setsar=1[v1];\
 [2:v]scale=1280:800:force_original_aspect_ratio=increase,crop=1280:800,zoompan=z='min(zoom+0.0007,1.15)':d=68:x='iw/2-(iw/zoom/2)':y='ih/2-(ih/zoom/2)':s=1280x800:fps=30,setsar=1[v2];\
 [v0][v1]xfade=transition=fade:duration=0.4:offset=1.867[x];\
 [x][v2]xfade=transition=fade:duration=0.4:offset=3.733[y]" \
 -map "[y]" -t 6 -r 30 -c:v libx264 -preset slow -crf 24 -pix_fmt yuv420p -movflags +faststart "$OUT/demo-6s.mp4"

# The GIF is what a forum post inlines - lean enough for a phone.
$F -i "$OUT/demo-6s.mp4" -vf "fps=10,scale=560:-1:flags=lanczos,split[a][b];[a]palettegen=max_colors=48:stats_mode=diff[p];[b][p]paletteuse=dither=bayer:bayer_scale=3:diff_mode=rectangle" -loop 0 "$OUT/demo-6s.gif"

# The poster is the frame the landing shows before the play button, and the
# still that represents the clip where motion is not possible - the landing
# scene, which is the densest frame of the three.
$F -ss 1.0 -i "$OUT/demo-6s.mp4" -frames:v 1 -q:v 3 "$OUT/poster.png"

for f in demo-6s.mp4 demo-6s.gif poster.png; do
  printf '%-16s %8s bytes\n' "$f" "$(stat -c%s "$OUT/$f")"
done
ffprobe -v error -show_entries format=duration -of csv=p=0 "$OUT/demo-6s.mp4"
