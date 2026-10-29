"""Joint camera + parameter solve from marked photo correspondences.

The spec (JSON) describes a parametric model only through the 3D points the
marks refer to. Every coordinate is a Python expression over the parameters,
so the same spec drives the solve and documents the model's logic.

    {
      "image": "photos/x.jpg",
      "params": {"c": {"init": 1.5}, "s": {"fixed": 6.7}, ...},
      "camera": {"pos": [x, y, z], "target": [x, y, z], "f_px": 1800},
      "points": [{"id": "A", "px": [462, 383], "xyz": ["0", "0", "zr_t"]}],
      "lines":  [{"id": "L1", "px": [[462, 383], [1900, 323]],
                  "xyz": [["0", "0", "zr_t"], ["20", "0", "zr_t"]]}],
      "truth":  {"c": 1.68, ...}          # optional, never used by the solve
    }

A line mark says the projected 3D segment must lie on the 2D line through the
two pixels; its residual is the distance of both projected endpoints to it.

usage: python -I solve.py spec.json [--boot 200] [--holdout] [--out result.json]
"""
import json
import math
import sys

import numpy as np
from scipy.optimize import least_squares


MIN_DEPTH = 0.5          # metres; marks closer than this to the camera are treated as a failed solve
F_RANGE = (200.0, 40000.0)  # focal length bounds in pixels; head-on photos otherwise let f and distance collapse


def look_at_R(pos, target):
    """World->camera rotation for a camera at pos looking at target, z up.
    Camera axes: x right, y down, z forward (OpenCV)."""
    fwd = np.asarray(target, float) - np.asarray(pos, float)
    fwd /= np.linalg.norm(fwd)
    right = np.cross(fwd, [0, 0, 1.0])
    right /= np.linalg.norm(right)
    down = np.cross(fwd, right)
    return np.stack([right, down, fwd])


def rodrigues(v):
    th = np.linalg.norm(v)
    if th < 1e-12:
        return np.eye(3)
    k = v / th
    K = np.array([[0, -k[2], k[1]], [k[2], 0, -k[0]], [-k[1], k[0], 0]])
    return np.eye(3) + math.sin(th) * K + (1 - math.cos(th)) * K @ K


class Problem:
    def __init__(self, spec):
        self.spec = spec
        import cv2
        im = cv2.imread(spec['image'])
        self.h, self.w = im.shape[:2]
        self.cx, self.cy = self.w / 2, self.h / 2
        self.free = [k for k, v in spec['params'].items() if 'fixed' not in v]
        self.fixed = {k: v['fixed'] for k, v in spec['params'].items() if 'fixed' in v}
        cam = spec['camera']
        self.R0 = look_at_R(cam['pos'], cam['target'])
        # a perspective-corrected (shift-lens or keystoned) photo has its principal
        # point shifted vertically; set camera.free_principal_point to "y" to solve
        # for that shift. Freeing x as well trades off against yaw and is not advised.
        self.free_pp = cam.get('free_principal_point') or ''
        # phone and wide-angle photos keep some barrel distortion after the
        # maker's correction; camera.free_distortion solves one radial term k1
        self.free_k1 = bool(cam.get('free_distortion'))
        self.k1 = 0.0
        # an edited photo (a phone's perspective correction, a stretched crop) can
        # have non-square pixels; camera.free_aspect solves fy / fx
        self.free_aspect = bool(cam.get('free_aspect'))
        self.aspect = 1.0
        self.x0 = np.concatenate([
            np.zeros(3), np.asarray(cam['pos'], float), [math.log(cam['f_px'])],
            [spec['params'][k]['init'] for k in self.free],
            ([self.cx] if 'x' in self.free_pp else []) + ([self.cy] if 'y' in self.free_pp else []),
            [0.0] if self.free_k1 else [],
            [0.0] if self.free_aspect else []])
        self.compiled = {}

    def unpack(self, x):
        R = rodrigues(x[0:3]) @ self.R0
        C = x[3:6]
        f = math.exp(x[6])
        P = dict(self.fixed)
        P.update(zip(self.free, x[7:7 + len(self.free)]))
        tail = list(x[7 + len(self.free):])
        if 'x' in self.free_pp:
            self.cx = tail.pop(0)
        if 'y' in self.free_pp:
            self.cy = tail.pop(0)
        if self.free_k1:
            self.k1 = tail.pop(0)
        if self.free_aspect:
            self.aspect = math.exp(tail.pop(0))
        return R, C, f, P

    def xyz(self, exprs, P):
        out = []
        for e in exprs:
            code = self.compiled.get(e)
            if code is None:
                code = self.compiled[e] = compile(str(e), e, 'eval')
            out.append(eval(code, {'__builtins__': {}, 'math': math}, P))
        return np.array(out, float)

    def project(self, X, R, C, f):
        Xc = R @ (X - C)
        return np.array([self.cx + f * Xc[0] / Xc[2], self.cy + f * self.aspect * Xc[1] / Xc[2]]), Xc[2]

    def undistort(self, px):
        """Marked pixel -> where a pinhole camera would have put it. Distortion is
        taken about the image centre; k1 is per unit radius at the half-width, so
        -0.02 means the left and right edges are pulled in by 2 %. Undistorting the
        marks, not the model, keeps a straight 3D edge a straight 2D line."""
        px = np.asarray(px, float)
        if not self.k1:
            return px
        c = np.array([self.w / 2, self.h / 2])
        q = (px - c) / (self.w / 2)
        return c + (px - c) / (1.0 + self.k1 * (q @ q))

    def residuals(self, x, marks=None):
        spec = self.spec
        marks = marks or (spec.get('points', []), spec.get('lines', []))
        R, C, f, P = self.unpack(x)
        res = []
        for m in marks[0]:
            uv, depth = self.project(self.xyz(m['xyz'], P), R, C, f)
            w = m.get('w', 1.0)
            res += list(w * (uv - self.undistort(m['px']))) if depth > MIN_DEPTH else [1e3, 1e3]
        for m in marks[1]:
            a, b = (self.undistort(p) for p in m['px'])
            n = np.array([-(b - a)[1], (b - a)[0]])
            n /= np.linalg.norm(n)
            w = m.get('w', 1.0)
            for e in m['xyz']:
                uv, depth = self.project(self.xyz(e, P), R, C, f)
                res.append(w * float(n @ (uv - a)) if depth > MIN_DEPTH else 1e3)
        # focal length from EXIF, if given: camera.f_px_prior = {"value": px, "sigma_frac": 0.03}
        fp = spec['camera'].get('f_px_prior')
        if fp:
            res.append(2.0 * (math.log(f) - math.log(fp['value'])) / fp['sigma_frac'])
        # soft priors: an assumption stated in metres, weighted like a 2 px mark per sigma
        for pr in spec.get('priors', []):
            v = float(self.xyz([pr['expr']], P)[0])
            res.append(2.0 * (v - pr['value']) / pr['sigma_m'])
        return np.array(res)

    def solve(self, x0=None, marks=None):
        lo = np.full(len(self.x0), -np.inf)
        hi = np.full(len(self.x0), np.inf)
        lo[6], hi[6] = math.log(F_RANGE[0]), math.log(F_RANGE[1])
        tail = len(self.x0) - (int(self.free_k1) + int(self.free_aspect))
        if self.free_k1:  # beyond +-0.3 it is fitting noise, not a lens
            lo[tail], hi[tail] = -0.3, 0.3
        if self.free_aspect:  # log fy/fx; +-0.3 is already a 35 % stretch
            lo[-1], hi[-1] = -0.3, 0.3
        start = np.clip(self.x0 if x0 is None else x0, lo + 1e-9, hi - 1e-9)
        r = least_squares(lambda x: self.residuals(x, marks), start, bounds=(lo, hi),
                          loss='soft_l1', f_scale=3.0, max_nfev=20000)
        return r


def unobserved(prob, x, eps=1e-6):
    """Free parameters no residual responds to. The optimiser can leave such a
    parameter anywhere (a synthetic test saw it drift from 7.0 to 4.0 with no
    mark using it), so its value must not be reported as a measurement."""
    base = prob.residuals(x)
    out = []
    for j, k in enumerate(prob.free):
        xp = np.array(x, float)
        xp[7 + j] += 1e-3
        if np.max(np.abs(prob.residuals(xp) - base)) < eps:
            out.append(k)
    return out


def summary(prob, x):
    R, C, f, P = prob.unpack(x)
    fov = 2 * math.degrees(math.atan(prob.w / 2 / f))
    fwd = R[2]
    return {'camera': {'pos': [round(v, 3) for v in C], 'target': [round(v, 3) for v in C + 10 * fwd],
                       'f_px': round(f, 1), 'hfov_deg': round(fov, 2),
                       'lens_35mm': round(36 / 2 / math.tan(math.radians(fov / 2)), 1),
                       'up': [round(v, 4) for v in -R[1]],
                       'R': [[round(v, 7) for v in row] for row in R]},
            'principal_point': [round(prob.cx, 1), round(prob.cy, 1)],
            'k1': round(prob.k1, 4),
            'aspect': round(prob.aspect, 4),
            'params': {k: round(v, 4) for k, v in P.items()}}


def main():
    path = sys.argv[1]
    spec = json.load(open(path, encoding='utf-8'))
    prob = Problem(spec)
    start_rms = float(np.sqrt(np.mean(prob.residuals(prob.x0) ** 2)))
    r = prob.solve()
    res = prob.residuals(r.x)
    out = summary(prob, r.x)
    out['warnings'] = []
    if start_rms > 300:
        # Gamble House: 793 px at the start meant the x axis ran right to left in the
        # photo (camera on the wrong side of the wall); the solve then ran to infinity
        out['warnings'].append('starting camera misses the marks by %.0f px: check that the camera '
                               'is on the right side of the model and that x runs left to right in '
                               'the photo as seen from it' % start_rms)
    if float(np.linalg.norm(prob.unpack(r.x)[1])) > 1e4:
        out['warnings'].append('camera ended more than 10 km away: the scale is not held by the marks')
    out['rms_px'] = round(float(np.sqrt(np.mean(res ** 2))), 2)
    out['max_px'] = round(float(np.max(np.abs(res))), 2)
    out['unobserved'] = unobserved(prob, r.x)

    # per-mark residuals, so a bad mark is visible instead of averaged away
    per = {}
    i = 0
    for m in spec.get('points', []):
        per[m['id']] = round(float(np.hypot(res[i], res[i + 1])), 2)
        i += 2
    for m in spec.get('lines', []):
        per[m['id']] = round(float(np.max(np.abs(res[i:i + len(m['xyz'])]))), 2)
        i += len(m['xyz'])
    for pr in spec.get('priors', []):
        per['prior ' + pr['expr']] = round(float(res[i]), 2)
        i += 1
    out['per_mark_px'] = per

    # bootstrap: jitter every mark by the stated pixel noise and re-solve
    nboot = int(sys.argv[sys.argv.index('--boot') + 1]) if '--boot' in sys.argv else 0
    if nboot:
        sigma = spec.get('mark_sigma_px', 2.0)
        rng = np.random.default_rng(0)
        samples = []
        for _ in range(nboot):
            pts = [dict(m, px=list(np.asarray(m['px']) + rng.normal(0, sigma, 2))) for m in spec.get('points', [])]
            lns = [dict(m, px=[list(np.asarray(p) + rng.normal(0, sigma, 2)) for p in m['px']]) for m in spec.get('lines', [])]
            rb = prob.solve(r.x, (pts, lns))
            samples.append([prob.unpack(rb.x)[3][k] for k in prob.free])
        sd = np.std(samples, axis=0)
        out['param_sd'] = {k: round(float(v), 4) for k, v in zip(prob.free, sd)}

    # hold-out: drop one mark, re-solve, and see how far the model now misses it.
    # A mark the rest of the photo cannot predict is either misread or carries the
    # only information about some parameter; both are worth knowing.
    if '--holdout' in sys.argv:
        pts_all, lns_all = spec.get('points', []), spec.get('lines', [])
        hold = {}
        for kind, coll in (('p', pts_all), ('l', lns_all)):
            for j, m in enumerate(coll):
                pts = [q for i, q in enumerate(pts_all) if not (kind == 'p' and i == j)]
                lns = [q for i, q in enumerate(lns_all) if not (kind == 'l' and i == j)]
                rh = prob.solve(r.x, (pts, lns))
                one = prob.residuals(rh.x, ([m], []) if kind == 'p' else ([], [m]))
                hold[m['id']] = round(float(np.max(np.abs(one[:2] if kind == 'p' else one))), 2)
        out['holdout_px'] = hold
        vals = np.array(list(hold.values()))
        out['holdout_median_px'] = round(float(np.median(vals)), 2)

    if 'truth' in spec:
        P = out['params']
        out['vs_truth'] = {}
        for k, t in spec['truth'].items():
            v = eval(k, {'__builtins__': {}}, P) if k not in P else P[k]
            out['vs_truth'][k] = {'solved': round(v, 3), 'truth': t,
                                  'err_m': round(v - t, 3), 'err_pct': round(100 * (v - t) / t, 1)}
            if set(out['unobserved']) & set(compile(k, k, 'eval').co_names):
                out['vs_truth'][k]['unobserved'] = True
    print(json.dumps(out, indent=1, ensure_ascii=False))
    if '--out' in sys.argv:
        json.dump(out, open(sys.argv[sys.argv.index('--out') + 1], 'w', encoding='utf-8'), indent=1, ensure_ascii=False)


if __name__ == '__main__':
    main()
