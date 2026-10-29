"""Re-solve one spec under several camera-model assumptions and report how far
each parameter moves between them.

usage: python -I variants.py spec.json [--tol 5] [--out variants.json]

The bootstrap in solve.py jitters the marks and keeps the camera model fixed,
so it cannot see an error that comes from the model itself: an unknown crop of
a phone photo, a keystone correction, a barrel distortion. Here every variant
is a plausible camera and fits the marks to a few pixels; if the parameters
still disagree between variants, the photo does not determine them, whatever
the bootstrap says.

Variants: plain pinhole; principal point free in y (keystone or shift lens);
free radial distortion; both; the focal prior removed and tightened when the
spec has one; principal point free in x and y (only as a stress case).
A parameter is "stable" when max-min across the variants that count is under
--tol percent of its value. A variant counts when it fits (rms within 1.5x the
best + 0.5 px) and its camera is physically plausible: principal point within
10 % of the image width of the centre in x (any y: keystone corrections shift it), focal length within 25 % of the EXIF
prior when there is one. Without the plausibility test, a free x principal
point or a focal length collapsing on a frontal photo dominates every spread.
"""
import copy
import json
import os
import sys

import numpy as np

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from solve import Problem, summary  # noqa: E402


def variants(spec):
    cam = spec['camera']
    v = {'pinhole': {}, 'pp_y': {'free_principal_point': 'y'}, 'k1': {'free_distortion': True},
         'k1+pp_y': {'free_distortion': True, 'free_principal_point': 'y'},
         'pp_xy': {'free_principal_point': 'xy'}}
    if cam.get('f_px_prior'):
        fp = cam['f_px_prior']
        v['no_f_prior'] = {'f_px_prior': None}
        v['f_prior_tight'] = {'f_px_prior': dict(fp, sigma_frac=min(fp['sigma_frac'], 0.02))}
    return v


def run(spec, mods):
    s = copy.deepcopy(spec)
    s['camera'].pop('free_principal_point', None)
    s['camera'].pop('free_distortion', None)
    for k, val in mods.items():
        if val is None:
            s['camera'].pop(k, None)
        else:
            s['camera'][k] = val
    prob = Problem(s)
    r = prob.solve()
    res = prob.residuals(r.x)
    out = summary(prob, r.x)
    out['rms_px'] = float(np.sqrt(np.mean(res ** 2)))
    return out


def main():
    path = sys.argv[1]
    tol = float(sys.argv[sys.argv.index('--tol') + 1]) if '--tol' in sys.argv else 5.0
    spec = json.load(open(path, encoding='utf-8'))
    free = [k for k, p in spec['params'].items() if 'fixed' not in p]
    rows = {}
    for name, mods in variants(spec).items():
        o = run(spec, mods)
        rows[name] = {'rms_px': round(o['rms_px'], 2), 'f_px': o['camera']['f_px'], 'k1': o['k1'],
                      'pp': o['principal_point'], 'params': {k: round(o['params'][k], 3) for k in free}}
    best = min(r['rms_px'] for r in rows.values())
    import cv2
    h, w = cv2.imread(spec['image']).shape[:2]
    fp = (spec['camera'].get('f_px_prior') or {}).get('value')

    def plausible(r):
        off = abs(r['pp'][0] - w / 2) / w  # a y shift is a legitimate keystone correction
        return bool(off <= 0.10 and (not fp or 0.75 <= r['f_px'] / fp <= 1.33))
    for r in rows.values():
        r['plausible'] = plausible(r)
    fit = [n for n, r in rows.items() if r['rms_px'] <= 1.5 * best + 0.5 and r['plausible']]
    spread = {}
    for k in free:
        vals = [rows[n]['params'][k] for n in fit]
        ref = np.median(vals)
        pct = 100 * (max(vals) - min(vals)) / max(abs(ref), 1e-6)
        spread[k] = {'min': min(vals), 'max': max(vals), 'spread_pct': round(pct, 1),
                     'stable': bool(pct < tol)}
    out = {'variants': rows, 'fitting_variants': fit, 'tol_pct': tol, 'spread': spread,
           'unstable': [k for k, v in spread.items() if not v['stable']]}
    if 'truth' in spec:
        out['truth'] = spec['truth']
    print('%-14s %6s %6s %7s  %s' % ('variant', 'rms', 'f', 'k1', '  '.join('%8s' % k[:8] for k in free)))
    for n, r in rows.items():
        print('%-14s %6.2f %6.0f %+7.3f  %s %s' % (n, r['rms_px'], r['f_px'], r['k1'],
              '  '.join('%8.3f' % r['params'][k] for k in free), '' if n in fit else '(implausible camera)' if not r['plausible'] else '(poor fit)'))
    print('%-14s %6s %6s %7s  %s' % ('spread %', '', '', '', '  '.join('%8.1f' % spread[k]['spread_pct'] for k in free)))
    if 'truth' in spec:
        print('%-14s %6s %6s %7s  %s' % ('truth', '', '', '', '  '.join(
            '%8.3f' % spec['truth'][k] if k in spec['truth'] else '%8s' % '-' for k in free)))
    print('unstable (> %.0f %%):' % tol, ', '.join(out['unstable']) or 'none')
    if '--out' in sys.argv:
        json.dump(out, open(sys.argv[sys.argv.index('--out') + 1], 'w', encoding='utf-8'), indent=1, ensure_ascii=False)


if __name__ == '__main__':
    main()
