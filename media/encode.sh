#!/usr/bin/env bash
# build/<name>_raw.webm or build/raw.webm (from record*.py) -> <name>.mp4 (1080p, H.264).
#   bash media/encode.sh            the result walkthrough: raw.webm -> screencast.mp4 and screencast.gif
#   bash media/encode.sh studio     the studio walkthrough: studio_raw.webm -> studio.mp4 and studio.gif
# The recording is blank while the page loads; it is cut at the first frame of the dark title card.
set -e
cd "$(dirname "$0")/build"
if [ "$1" = studio ]; then RAW=studio_raw.webm; OUT=studio; else RAW=raw.webm; OUT=screencast; fi
SS=$(ffmpeg -v error -i "$RAW" -vf "fps=10,scale=64:36,format=gray" -f rawvideo - |      python -I -c "import sys; d=sys.stdin.buffer.read(); n=64*36
for i in range(len(d)//n):
    f=d[i*n:(i+1)*n]
    if sum(f)/n < 60: print('%.1f' % (i/10)); break")
echo "cut at $SS s"
ffmpeg -v error -y -ss "$SS" -i "$RAW" -c:v libx264 -preset slow -crf 20 -pix_fmt yuv420p -movflags +faststart ../$OUT.mp4
# a short gif for the README, 800 px, 8 fps
if [ "$OUT" = studio ]; then CUTS="[0:v]trim=6:20,setpts=PTS-STARTPTS[a];[0:v]trim=30:36,setpts=PTS-STARTPTS[b]"
else CUTS="[0:v]trim=8.5:15,setpts=PTS-STARTPTS[a];[0:v]trim=34:46.5,setpts=PTS-STARTPTS[b]"; fi
ffmpeg -v error -y -i ../$OUT.mp4 -filter_complex   "$CUTS;[a][b]concat=n=2:v=1[c];[c]fps=8,scale=800:-1:flags=lanczos,split[x][y];[x]palettegen=max_colors=96[p];[y][p]paletteuse=dither=bayer:bayer_scale=4"   ../$OUT.gif
ls -la ../$OUT.*
