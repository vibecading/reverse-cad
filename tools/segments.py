"""Number the photo's long straight edges so marks can be picked by id instead of read off pixels.

usage:
  python -I segments.py photo.jpg out_dir [--min 40] [--merge 3] [--crop x0 y0 x1 y1]

Writes out_dir/segments.json ({id: [x0, y0, x1, y1, length]}) and
out_dir/segments.jpg (the photo dimmed, every segment drawn with its id).
With --crop, only segments inside the box are drawn, enlarged, so ids stay
legible on busy facades; ids are the same as in the full list.

Collinear pieces of one edge (split by a mullion or a branch) are merged when
they are within --merge px of each other's line and point the same way.
Then in a spec, a line mark can be written as {"seg": 17, ...} instead of
"px"; resolve with `python -I segments.py --resolve spec.json segments.json out.json`.
"""
import json
import math
import os
import sys

import cv2
import numpy as np


def detect(gray, min_len):
    lsd = cv2.createLineSegmentDetector(cv2.LSD_REFINE_STD)
    s = lsd.detect(gray)[0]
    s = np.zeros((0, 4)) if s is None else s.reshape(-1, 4)
    L = np.hypot(s[:, 2] - s[:, 0], s[:, 3] - s[:, 1])
    return s[L >= min_len / 2]


def merge(segs, tol):
    """Greedy merge of near-collinear segments, longest first."""
    order = np.argsort(-np.hypot(segs[:, 2] - segs[:, 0], segs[:, 3] - segs[:, 1]))
    used = np.zeros(len(segs), bool)
    out = []
    for i in order:
        if used[i]:
            continue
        a, b = segs[i, :2], segs[i, 2:]
        u = (b - a) / max(np.linalg.norm(b - a), 1e-9)
        n = np.array([-u[1], u[0]])
        pts = [a, b]
        used[i] = True
        for j in order:
            if used[j]:
                continue
            p, q = segs[j, :2], segs[j, 2:]
            v = (q - p) / max(np.linalg.norm(q - p), 1e-9)
            if abs(u @ v) < math.cos(math.radians(2)):
                continue
            if abs((p - a) @ n) > tol or abs((q - a) @ n) > tol:
                continue
            t = [(p - a) @ u, (q - a) @ u]
            span = [min((x - a) @ u for x in pts), max((x - a) @ u for x in pts)]
            if min(t) > span[1] + 60 or max(t) < span[0] - 60:  # allow gaps up to 60 px
                continue
            pts += [p, q]
            used[j] = True
        P = np.array(pts)
        ts = (P - a) @ u
        out.append(np.concatenate([a + ts.min() * u, a + ts.max() * u]))
    return np.array(out)


def draw(img, segs, ids, crop=None):
    im = (img * 0.45).astype(np.uint8)
    if crop:
        x0, y0, x1, y1 = crop
        im = im[y0:y1, x0:x1].copy()
        sc = max(1.0, 1400 / im.shape[1])
        im = cv2.resize(im, None, fx=sc, fy=sc, interpolation=cv2.INTER_CUBIC)
    else:
        x0 = y0 = 0
        sc = 1.0
    rng = np.random.default_rng(1)
    for k, s in zip(ids, segs):
        a = ((s[0] - x0) * sc, (s[1] - y0) * sc)
        b = ((s[2] - x0) * sc, (s[3] - y0) * sc)
        col = tuple(int(c) for c in rng.integers(90, 256, 3))
        cv2.line(im, tuple(map(int, a)), tuple(map(int, b)), col, 2)
        m = (int((a[0] + b[0]) / 2), int((a[1] + b[1]) / 2))
        cv2.putText(im, str(k), (m[0] + 3, m[1] - 3), 0, 0.5, (0, 0, 0), 3)
        cv2.putText(im, str(k), (m[0] + 3, m[1] - 3), 0, 0.5, col, 1)
    return im


def resolve(spec_p, segs_p, out_p):
    spec = json.load(open(spec_p, encoding='utf-8'))
    segs = json.load(open(segs_p, encoding='utf-8'))
    for m in spec.get('lines', []):
        if 'seg' in m:
            s = segs[str(m['seg'])]
            m['px'] = [[s[0], s[1]], [s[2], s[3]]]
    json.dump(spec, open(out_p, 'w', encoding='utf-8'), indent=1, ensure_ascii=False)


def main():
    if sys.argv[1] == '--resolve':
        return resolve(*sys.argv[2:5])
    photo, out = sys.argv[1], sys.argv[2]
    opt = lambda k, d: float(sys.argv[sys.argv.index(k) + 1]) if k in sys.argv else d
    os.makedirs(out, exist_ok=True)
    img = cv2.imread(photo)
    gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
    segs = merge(detect(gray, opt('--min', 40)), opt('--merge', 3))
    L = np.hypot(segs[:, 2] - segs[:, 0], segs[:, 3] - segs[:, 1])
    keep = L >= opt('--min', 40)
    segs, L = segs[keep], L[keep]
    order = np.argsort(-L)
    segs, L = segs[order], L[order]
    table = {str(i): [round(float(v), 1) for v in s] + [round(float(l), 1)] for i, (s, l) in enumerate(zip(segs, L))}
    json.dump(table, open(os.path.join(out, 'segments.json'), 'w'), indent=0)
    if '--crop' in sys.argv:
        i = sys.argv.index('--crop')
        crop = tuple(int(v) for v in sys.argv[i + 1:i + 5])
        x0, y0, x1, y1 = crop
        inside = [(k, s) for k, s in enumerate(segs)
                  if min(s[0], s[2]) >= x0 - 5 and max(s[0], s[2]) <= x1 + 5 and min(s[1], s[3]) >= y0 - 5 and max(s[1], s[3]) <= y1 + 5]
        name = 'segments_%d_%d_%d_%d.jpg' % crop
        cv2.imwrite(os.path.join(out, name), draw(img, [s for _, s in inside], [k for k, _ in inside], crop))
    else:
        cv2.imwrite(os.path.join(out, 'segments.jpg'), draw(img, segs, range(len(segs))))
    print(len(segs), 'segments')


if __name__ == '__main__':
    main()
