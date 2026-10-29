"""Joint solve of one parametric model from several photos.

usage: python -I solve_multi.py spec_a.json spec_b.json [...] [--boot 30] [--out result.json]

Each spec is an ordinary single-photo spec (its own image, camera, marks and
camera options). Parameters with the same name are the same unknown in every
photo; a parameter fixed in any spec is fixed in all, and must agree. Each
photo keeps its own camera.

Reported: the shared parameters, each photo's rms in the joint solve next to
its rms alone, and the truth comparison. A photo whose rms grows a lot when
it has to agree with the others is telling you the photos disagree: misread
marks, a different datum, or an edited image. That is the cross-photo check
of the reverse-photo skill as one number per photo.
"""
import copy
import json
import math
import os
import sys

import numpy as np
from scipy.optimize import least_squares

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from solve import F_RANGE, Problem, summary  # noqa: E402


def merged_params(specs):
    params = {}
    for s in specs:
        for k, p in s['params'].items():
            if k not in params:
                params[k] = dict(p)
                continue
            q = params[k]
            if 'fixed' in p and 'fixed' in q and abs(p['fixed'] - q['fixed']) > 1e-9:
                raise SystemExit('parameter %s is fixed to %s and %s in different specs' % (k, q['fixed'], p['fixed']))
            if 'fixed' in p:
                params[k] = dict(p)
    return params


class Multi:
    def __init__(self, specs):
        self.params = merged_params(specs)
        self.probs = []
        for s in specs:
            s = copy.deepcopy(s)
            s['params'] = self.params  # same free names in the same order everywhere
            self.probs.append(Problem(s))
        self.free = self.probs[0].free
        self.nf = len(self.free)
        # per photo: camera (6) + log f + optional tail (pp, k1, aspect)
        self.cam_len = [7 + (len(p.x0) - 7 - self.nf) for p in self.probs]
        self.x0 = np.concatenate([self.probs[0].x0[7:7 + self.nf]] +
                                 [np.concatenate([p.x0[:7], p.x0[7 + self.nf:]]) for p in self.probs])

    def local(self, x, i):
        shared = x[:self.nf]
        off = self.nf + sum(self.cam_len[:i])
        cam = x[off:off + self.cam_len[i]]
        return np.concatenate([cam[:7], shared, cam[7:]])

    def residuals(self, x):
        return np.concatenate([p.residuals(self.local(x, i)) for i, p in enumerate(self.probs)])

    def solve(self):
        lo = np.full(len(self.x0), -np.inf)
        hi = np.full(len(self.x0), np.inf)
        off = self.nf
        for i, p in enumerate(self.probs):
            lo[off + 6], hi[off + 6] = math.log(F_RANGE[0]), math.log(F_RANGE[1])
            n = self.cam_len[i]
            k = off + n - (int(p.free_k1) + int(p.free_aspect))
            if p.free_k1:
                lo[k], hi[k] = -0.3, 0.3
            if p.free_aspect:
                lo[off + n - 1], hi[off + n - 1] = -0.3, 0.3
            off += n
        start = np.clip(self.x0, lo + 1e-9, hi - 1e-9)
        return least_squares(self.residuals, start, bounds=(lo, hi), loss='soft_l1', f_scale=3.0, max_nfev=40000)


def rms(v):
    return float(np.sqrt(np.mean(np.asarray(v) ** 2)))


def main():
    paths = [a for a in sys.argv[1:] if a.endswith('.json') and not (sys.argv.index(a) > 0 and sys.argv[sys.argv.index(a) - 1] == '--out')]
    specs = [json.load(open(p, encoding='utf-8')) for p in paths]
    m = Multi(specs)
    r = m.solve()
    base = m.residuals(r.x)
    unobs = []
    for j, k in enumerate(m.free):
        xp = r.x.copy()
        xp[j] += 1e-3
        if np.max(np.abs(m.residuals(xp) - base)) < 1e-6:
            unobs.append(k)
    out = {'photos': [], 'params': {}, 'unobserved': unobs}
    for i, (p, path) in enumerate(zip(m.probs, paths)):
        xi = m.local(r.x, i)
        joint = rms(p.residuals(xi))
        alone = rms(p.residuals(p.solve().x))
        s = summary(p, xi)
        out['photos'].append({'spec': path, 'rms_joint_px': round(joint, 2), 'rms_alone_px': round(alone, 2),
                              'camera': s['camera'], 'principal_point': s['principal_point'], 'k1': s['k1'], 'aspect': s['aspect']})
        out['params'] = s['params']
    # bootstrap: jitter every mark in every photo by its stated noise, re-solve jointly
    nboot = int(sys.argv[sys.argv.index('--boot') + 1]) if '--boot' in sys.argv else 0
    if nboot:
        rng = np.random.default_rng(0)
        samples = []
        for _ in range(nboot):
            jit = copy.deepcopy(specs)
            for s in jit:
                sig = s.get('mark_sigma_px', 2.0)
                for q in s.get('points', []):
                    q['px'] = list(np.asarray(q['px'], float) + rng.normal(0, sig, 2))
                for q in s.get('lines', []):
                    q['px'] = [list(np.asarray(e, float) + rng.normal(0, sig, 2)) for e in q['px']]
            mb = Multi(jit)
            mb.x0 = r.x.copy()
            rb = mb.solve()
            samples.append(rb.x[:m.nf])
        out['param_sd'] = {k: round(float(v), 4) for k, v in zip(m.free, np.std(samples, axis=0))}
    truth = {}
    for s in specs:
        truth.update(s.get('truth', {}))
    out['vs_truth'] = {}
    for k, t in truth.items():
        v = eval(k, {'__builtins__': {}}, out['params'])
        out['vs_truth'][k] = {'solved': round(v, 3), 'truth': t, 'err_m': round(v - t, 3), 'err_pct': round(100 * (v - t) / t, 1)}
        if set(unobs) & set(compile(k, k, 'eval').co_names):
            out['vs_truth'][k]['unobserved'] = True
    print(json.dumps(out, indent=1, ensure_ascii=False))
    if '--out' in sys.argv:
        json.dump(out, open(sys.argv[sys.argv.index('--out') + 1], 'w', encoding='utf-8'), indent=1, ensure_ascii=False)


if __name__ == '__main__':
    main()
