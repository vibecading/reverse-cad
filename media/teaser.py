"""Cut the studio walkthrough into a short teaser: fast cuts, sped up.

usage: python -I media/teaser.py      (after media/encode.sh studio)
Writes media/teaser.mp4 and media/teaser.gif. The cut list refers to times in
media/studio.mp4; re-check it after re-recording.
"""
import pathlib
import subprocess

M = pathlib.Path(__file__).resolve().parent
# (start, end, speed) in studio.mp4
CUTS = [
    (4.6, 8.5, 1.5),     # the photo comes in, the model builds itself
    (11.5, 17.0, 1.8),   # bays added with a slider
    (22.5, 25.0, 1.3),   # dependency graph
    (28.5, 33.0, 2.0),   # dragging a grip in the plan
    (45.5, 50.5, 1.6),   # flying back into the photo camera
    (62.3, 63.9, 1.0),   # Crown Hall on its photo
    (66.0, 69.5, 1.6),   # Gamble: raise the ridge
    (72.5, 74.5, 1.2),   # Gamble on its photo
    (75.5, 78.0, 1.25),  # Robie, one photo: off the drawings
    (80.5, 83.0, 1.25),  # Robie, two photos: on the drawings
    (89.0, 92.0, 1.5),   # an agent's proposal in review
    (95.5, 99.0, 1.6),   # a design conflict in plain words
    (112.0, 115.0, 1.5),  # end card
]


def main():
    parts, labels = [], []
    for i, (a, b, sp) in enumerate(CUTS):
        parts.append('[0:v]trim=%.2f:%.2f,setpts=(PTS-STARTPTS)/%.3f[v%d]' % (a, b, sp, i))
        labels.append('[v%d]' % i)
    total = sum((b - a) / sp for a, b, sp in CUTS)
    fc = ';'.join(parts) + ';' + ''.join(labels) + 'concat=n=%d:v=1[out]' % len(CUTS)
    src = str(M / 'studio.mp4')
    subprocess.run(['ffmpeg', '-v', 'error', '-y', '-i', src, '-filter_complex', fc, '-map', '[out]', '-r', '30',
                    '-c:v', 'libx264', '-preset', 'slow', '-crf', '21', '-pix_fmt', 'yuv420p', '-movflags', '+faststart',
                    str(M / 'teaser.mp4')], check=True)
    subprocess.run(['ffmpeg', '-v', 'error', '-y', '-i', str(M / 'teaser.mp4'), '-vf',
                    'fps=8,scale=800:-1:flags=lanczos,split[x][y];[x]palettegen=max_colors=96[p];[y][p]paletteuse=dither=bayer:bayer_scale=4',
                    str(M / 'teaser.gif')], check=True)
    print('teaser: %.1f s' % total)


if __name__ == '__main__':
    main()
