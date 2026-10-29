"""Draw the solved Robie model (pink) and the HABS model seen through the same
camera (green) over the photo. Run from the repo root:

    python -I cases/robie/draw_overlay.py cases/robie/spec_w1.json cases/robie/result_w1.json out.jpg
"""
import json, sys, cv2, numpy as np
sys.path.insert(0, 'tools')
from solve import Problem
spec = json.load(open(sys.argv[1])); res = json.load(open(sys.argv[2]))
prob = Problem(spec)
R = np.array(res['camera']['R']); C = np.array(res['camera']['pos']); f = res['camera']['f_px']
prob.cx, prob.cy = res['principal_point']; k1 = res.get('k1', 0)
P = res['params']
im = cv2.imread(spec['image'])
def proj(X):
    Xc = R @ (np.array(X, float) - C); u = np.array([prob.cx + f * Xc[0] / Xc[2], prob.cy + f * Xc[1] / Xc[2]])
    c = np.array([prob.w / 2, prob.h / 2]); q = (u - c) / (prob.w / 2)
    # distort (approximate inverse of undistort)
    return c + (u - c) * (1 + k1 * (q @ q))
def seg(a, b, col, n=30):
    pts = [proj(np.array(a) + (np.array(b) - np.array(a)) * t) for t in np.linspace(0, 1, n)]
    for p, q in zip(pts, pts[1:]): cv2.line(im, tuple(map(int, p)), tuple(map(int, q)), col, 2)
def model(P, col):
    Lw, Ls, hct, hcb, hb = P['Lw'], P['Ls'], P['h_ct'], P['h_cb'], P['h_b']
    for z in (hct, hcb, hb, 0):
        seg([0, Lw, z], [0, 0, z], col); seg([0, 0, z], [Ls, 0, z], col)
    for x, y in ((0, Lw), (0, 0), (Ls, 0)): seg([x, y, 0], [x, y, hct], col)
    rx, rys, ryn, rzt = P['rx'], P['rys'], P['ryn'], P['rzt']
    seg([rx, ryn, rzt], [rx, rys, rzt], col); seg([rx, rys, rzt], [rx + 25, rys, rzt], col); seg([rx, ryn, rzt], [rx + 25, ryn, rzt], col)
model(P, (138, 33, 224))
T = dict(P); T.update(spec['truth'])
model(T, (60, 200, 60))
for m in spec['points']: cv2.circle(im, tuple(map(int, m['px'])), 5, (255, 200, 0), 2)
cv2.imwrite(sys.argv[3], im)
