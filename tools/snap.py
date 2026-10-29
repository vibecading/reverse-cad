"""Refine rough line marks against the photo's own line segments.

A mark read off a crop is good to a few pixels; the photo usually holds the
edge itself. For each line mark, collect LSD segments lying within `tol` px of
the rough line and within `ang` degrees of its direction, then refit the line
through them (length-weighted). Points that are the meeting of two refined
lines can be recomputed as their intersection.

usage:
  python -I snap.py spec.json out_spec.json [--tol 6] [--ang 4] [--report]

Only `lines` are changed. Each refined mark keeps its original pixels in
`px_rough` and gets `snap` = {segments, support_px, moved_px}. A mark with no
support is left as it was and flagged, so a mark the photo does not show is
never "snapped" onto some other edge silently.
"""
import json
import math
import sys

import cv2
import numpy as np


def segments(gray):
    lsd = cv2.createLineSegmentDetector(cv2.LSD_REFINE_STD)
    segs = lsd.detect(gray)[0]
    return np.zeros((0, 4)) if segs is None else segs.reshape(-1, 4)


def refine(a, b, segs, tol, ang):
    a, b = np.asarray(a, float), np.asarray(b, float)
    d = b - a
    L = np.linalg.norm(d)
    u = d / L
    n = np.array([-u[1], u[0]])
    p, q = segs[:, :2], segs[:, 2:]
    sd = q - p
    slen = np.linalg.norm(sd, axis=1)
    cosang = np.abs(sd @ u) / np.maximum(slen, 1e-9)
    near = (np.abs((p - a) @ n) < tol) & (np.abs((q - a) @ n) < tol)
    # keep segments overlapping the rough span (with a little slack)
    tp, tq = (p - a) @ u, (q - a) @ u
    overlap = (np.maximum(tp, tq) > -0.1 * L) & (np.minimum(tp, tq) < 1.1 * L)
    keep = near & overlap & (cosang > math.cos(math.radians(ang))) & (slen > 8)
    if not keep.any():
        return None
    pts = np.vstack([p[keep], q[keep]])
    w = np.concatenate([slen[keep], slen[keep]])
    c = (pts * w[:, None]).sum(0) / w.sum()
    cov = ((pts - c) * w[:, None]).T @ (pts - c)
    evals, evecs = np.linalg.eigh(cov)
    dirv = evecs[:, 1]
    if dirv @ u < 0:
        dirv = -dirv
    # project the rough endpoints onto the refined line so the span stays the same
    na, nb = c + ((a - c) @ dirv) * dirv, c + ((b - c) @ dirv) * dirv
    return na, nb, int(keep.sum()), float(slen[keep].sum())


def main():
    src, dst = sys.argv[1], sys.argv[2]
    tol = float(sys.argv[sys.argv.index('--tol') + 1]) if '--tol' in sys.argv else 6.0
    ang = float(sys.argv[sys.argv.index('--ang') + 1]) if '--ang' in sys.argv else 4.0
    spec = json.load(open(src, encoding='utf-8'))
    gray = cv2.imread(spec['image'], cv2.IMREAD_GRAYSCALE)
    segs = segments(gray)
    report = []
    for m in spec.get('lines', []):
        a, b = m.get('px_rough', m['px'])
        r = refine(a, b, segs, tol, ang)
        if r is None:
            m['snap'] = {'segments': 0, 'note': 'no photo edge near this mark; left as read'}
            report.append((m['id'], 'NO SUPPORT'))
            continue
        na, nb, nseg, sup = r
        moved = max(np.linalg.norm(na - np.asarray(a, float)), np.linalg.norm(nb - np.asarray(b, float)))
        m['px_rough'] = [list(map(float, a)), list(map(float, b))]
        m['px'] = [[round(float(v), 2) for v in na], [round(float(v), 2) for v in nb]]
        m['snap'] = {'segments': nseg, 'support_px': round(sup, 1), 'moved_px': round(float(moved), 2)}
        report.append((m['id'], f'{nseg} segs, {sup:.0f} px of edge, moved {moved:.1f} px'))
    json.dump(spec, open(dst, 'w', encoding='utf-8'), indent=1, ensure_ascii=False)
    if '--report' in sys.argv:
        for row in report:
            print(*row, sep=': ')


if __name__ == '__main__':
    main()
