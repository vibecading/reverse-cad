"""Draw a labelled pixel grid over an image (or a crop of it) so marks can be read off precisely.

usage: python -I grid.py photo.jpg out.jpg [x0 y0 x1 y1] [--step N]
"""
import sys
import cv2

args = [a for a in sys.argv[1:] if not a.startswith('--')]
step = int(sys.argv[sys.argv.index('--step') + 1]) if '--step' in sys.argv else 100
if '--step' in sys.argv:
    args.remove(str(step))
src, out = args[0], args[1]
im = cv2.imread(src)
x0, y0, x1, y1 = (int(v) for v in args[2:6]) if len(args) >= 6 else (0, 0, im.shape[1], im.shape[0])
crop = im[y0:y1, x0:x1].copy()
scale = max(1.0, 1200 / crop.shape[1])
crop = cv2.resize(crop, None, fx=scale, fy=scale, interpolation=cv2.INTER_CUBIC)
for gx in range((x0 // step + 1) * step, x1, step):
    px = int((gx - x0) * scale)
    cv2.line(crop, (px, 0), (px, crop.shape[0]), (0, 0, 255), 1)
    cv2.putText(crop, str(gx), (px + 2, 14), 0, 0.45, (0, 0, 255), 1)
for gy in range((y0 // step + 1) * step, y1, step):
    py = int((gy - y0) * scale)
    cv2.line(crop, (0, py), (crop.shape[1], py), (255, 0, 0), 1)
    cv2.putText(crop, str(gy), (2, py - 3), 0, 0.45, (255, 0, 0), 1)
cv2.imwrite(out, crop)
