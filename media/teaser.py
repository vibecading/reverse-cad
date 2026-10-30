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
    (5.8, 9.8, 1.5),     # the photo comes in, the model builds itself
    (13.0, 18.5, 1.8),   # bays added with a slider
    (20.0, 22.5, 1.3),   # dependency graph
    (28.5, 33.0, 2.0),   # dragging a grip in the plan
    (46.8, 51.8, 1.6),   # flying back into the photo camera
    (62.6, 64.0, 1.0),   # Crown Hall on its photo
    (67.2, 71.0, 1.6),   # Gamble: raise the ridge
    (74.0, 75.9, 1.2),   # Gamble on its photo
    (77.0, 79.5, 1.25),  # Robie, one photo: off the drawings
    (82.0, 84.5, 1.25),  # Robie, two photos: on the drawings
    (90.8, 94.3, 1.5),   # an agent's proposal in review, accepted
    (97.5, 101.0, 1.6),  # a design conflict in plain words
    (114.3, 117.3, 1.5),  # end card
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
                    'fps=7,scale=800:-1:flags=lanczos,split[x][y];[x]palettegen=max_colors=80[p];[y][p]paletteuse=dither=bayer:bayer_scale=4',
                    str(M / 'teaser.gif')], check=True)
    print('teaser: %.1f s' % total)


if __name__ == '__main__':
    main()
