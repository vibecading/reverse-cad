"""Control for overlay.py: score the same render shifted by known offsets.
A metric that barely drops under a 15-40 px shift is not measuring fit.

usage: python -I control.py photo.jpg render.png
"""
import subprocess
import sys

import cv2
import numpy as np

photo_p, render_p = sys.argv[1:3]
r = cv2.imread(render_p)
here = __file__.replace('control.py', '')
for dx, dy in [(0, 0), (5, 0), (15, 0), (40, 0), (0, 5), (0, 15)]:
    M = np.float32([[1, 0, dx], [0, 1, dy]])
    sh = cv2.warpAffine(r, M, (r.shape[1], r.shape[0]), borderMode=cv2.BORDER_REPLICATE)
    p = render_p.replace('.png', '_shift.png')
    cv2.imwrite(p, sh)
    out = subprocess.run([sys.executable, '-I', here + 'overlay.py', photo_p, p, sys.argv[3], sys.argv[4], p.replace('.png', '.jpg')],
                         capture_output=True, text=True).stdout
    import json
    sc = json.loads(out)
    print(dx, dy, 'vertical', sc['vertical_edges']['within_3px'], 'horizontal', sc['horizontal_edges']['within_3px'],
          'worst', sc['worst_within_3px'])
