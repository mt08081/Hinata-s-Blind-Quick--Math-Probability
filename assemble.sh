#!/bin/bash
# Concatenate rendered scene segments, add the soundtrack, encode the final video.
set -e
cd /home/claude/fq
python3 - <<'EOF'
import video
video.import_scenes()
from registry import SCENES
with open("segs/list.txt", "w") as f:
    for n, d, _ in SCENES:
        f.write(f"file '{n}.mp4'\n")
EOF
ffmpeg -y -loglevel error -f concat -safe 0 -i segs/list.txt -c copy segs/all_video.mp4
ffmpeg -y -loglevel error -i segs/all_video.mp4 -i soundtrack.wav \
  -map 0:v:0 -map 1:a:0 -c:v libx264 -preset slow -crf ${CRF:-21} -tune animation -pix_fmt yuv420p \
  -c:a aac -b:a 192k -movflags +faststart -shortest "${OUT:-The_Blind_Quick.mp4}"
ls -la "${OUT:-The_Blind_Quick.mp4}"
ffprobe -v error -show_entries format=duration,bit_rate -of default=nw=1 "${OUT:-The_Blind_Quick.mp4}"
