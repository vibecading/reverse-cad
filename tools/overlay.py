"""Overlay a Shaded model render (captured from the solved camera) on the source photo
and score how well the model's visible edges sit on the photo's edges.

usage: python -I overlay.py photo.jpg render.png spec.json result.json out.jpg

Score: for every model edge pixel, distance to the nearest photo edge pixel
running in the same direction (within 15 degrees). Vertical and horizontal
edges are scored apart and the worse one is the headline, so long horizontal
slabs cannot hide a sideways shift.
Only the model's own edges are scored, so foliage in the photo does not count
against the model; missing model parts show up in the picture, not the number.
"""
import json
import os
import sys

import cv2
import numpy as np

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from solve import Problem  # noqa: E402

photo_p, render_p, spec_p, result_p, out_p = sys.argv[1:6]
photo = cv2.imread(photo_p)
render = cv2.imread(render_p)
render = cv2.resize(render, (photo.shape[1], photo.shape[0]))

# model edges: Canny on a Shaded capture finds silhouettes and creases between faces
g = cv2.cvtColor(render, cv2.COLOR_BGR2GRAY)
model_edges = (cv2.Canny(g, 20, 60) > 0).astype(np.uint8)

pg = cv2.GaussianBlur(cv2.cvtColor(photo, cv2.COLOR_BGR2GRAY), (3, 3), 0)
photo_edges = cv2.Canny(pg, 40, 120)


def orientation(gray):
    gx = cv2.Sobel(gray.astype(np.float32), cv2.CV_32F, 1, 0, ksize=3)
    gy = cv2.Sobel(gray.astype(np.float32), cv2.CV_32F, 0, 1, ksize=3)
    return (np.degrees(np.arctan2(gy, gx)) + 180.0) % 180.0  # gradient direction, mod 180


NB = 12  # 15 degree bins
pbin = (orientation(pg) // (180 / NB)).astype(int) % NB
mbin = (orientation(g) // (180 / NB)).astype(int) % NB
dist_b = []
for b in range(NB):
    # a photo edge counts for bin b if its direction is within one bin of b
    sel = (photo_edges > 0) & ((pbin == b) | (pbin == (b - 1) % NB) | (pbin == (b + 1) % NB))
    dist_b.append(cv2.distanceTransform((~sel).astype(np.uint8), cv2.DIST_L2, 3))
dist_b = np.stack(dist_b)
ys, xs = np.nonzero(model_edges)
d = dist_b[mbin[ys, xs], ys, xs]
ang = mbin[ys, xs] * (180 / NB)
vertical_grad = (ang < 30) | (ang >= 150)      # horizontal gradient = vertical edge
horizontal_grad = (ang >= 60) & (ang < 120)    # vertical gradient = horizontal edge


def part(mask):
    dd = d[mask]
    return {'px': int(dd.size), 'within_3px': round(float(np.mean(dd <= 3)), 3) if dd.size else None,
            'median_px': round(float(np.median(dd)), 2) if dd.size else None}


score = {'all': part(np.ones_like(d, bool)), 'vertical_edges': part(vertical_grad),
         'horizontal_edges': part(horizontal_grad)}
score['worst_within_3px'] = min(score['vertical_edges']['within_3px'], score['horizontal_edges']['within_3px'])
dist = None

# picture: photo dimmed, model edges in magenta, solver projections of the marks in cyan
out = (photo * 0.55).astype(np.uint8)
out[model_edges > 0] = (255, 0, 255)
spec = json.load(open(spec_p, encoding='utf-8'))
res = json.load(open(result_p, encoding='utf-8'))
prob = Problem(spec)
if 'principal_point' in res:
    prob.cx, prob.cy = res['principal_point']
from solve import look_at_R  # noqa: E402
R = look_at_R(res['camera']['pos'], res['camera']['target'])
C = np.array(res['camera']['pos'])
f = res['camera']['f_px']
for m in spec.get('points', []):
    X = prob.xyz(m['xyz'], res['params'])
    uv, _ = prob.project(X, R, C, f)
    cv2.circle(out, tuple(int(v) for v in m['px']), 7, (0, 255, 255), 2)
    cv2.drawMarker(out, tuple(int(v) for v in uv), (255, 255, 0), cv2.MARKER_CROSS, 14, 2)
cv2.putText(out, 'edges on same-direction photo edges within 3px: vertical %.0f%%, horizontal %.0f%%'
            % (100 * score['vertical_edges']['within_3px'], 100 * score['horizontal_edges']['within_3px']),
            (20, 40), 0, 1.0, (255, 255, 255), 2)
cv2.imwrite(out_p, out)
print(json.dumps(score))
