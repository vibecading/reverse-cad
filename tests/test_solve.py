"""Synthetic checks of the solvers: a known building seen by known cameras.

Marks are made by projecting the model with the true camera, so every test
knows the right answer. Run: python -I -m pytest tests -q
"""
import copy
import json
import math
import os
import sys

import cv2
import numpy as np
import pytest

sys.path.insert(0, os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), 'tools'))
from solve import Problem, look_at_R  # noqa: E402
from solve_multi import Multi  # noqa: E402
import dag  # noqa: E402

W, H = 1920, 1440
TRUE = {'L': 20.0, 'D': 9.0, 'Hh': 6.0, 'zf': 1.2}
# corners of a raised box: floor slab at zf, roof at Hh
CORNERS = [(x, y, z) for x in ('0', 'L') for y in ('0', 'D') for z in ('0', 'zf', 'Hh')]


def image(tmp_path):
    p = str(tmp_path / 'blank.png')
    cv2.imwrite(p, np.zeros((H, W, 3), np.uint8))
    return p


def project(X, pos, target, f, k1=0.0):
    R = look_at_R(pos, target)
    Xc = R @ (np.asarray(X, float) - np.asarray(pos, float))
    u = np.array([W / 2 + f * Xc[0] / Xc[2], H / 2 + f * Xc[1] / Xc[2]])
    if k1:  # distort about the centre, inverse of solve.Problem.undistort (to first order)
        c = np.array([W / 2, H / 2])
        q = (u - c) / (W / 2)
        u = c + (u - c) * (1 + k1 * (q @ q))
    return u


def spec_for(img, pos, target, f, noise=0.0, seed=0, k1=0.0, drop=()):
    rng = np.random.default_rng(seed)
    pts = []
    for i, c in enumerate(CORNERS):
        if i in drop:
            continue
        X = [eval(e, {}, TRUE) for e in c]
        px = project(X, pos, target, f, k1) + rng.normal(0, noise, 2)
        pts.append({'id': 'p%d' % i, 'px': [float(v) for v in px], 'xyz': list(c)})
    return {
        'image': img,
        'params': {'L': {'fixed': TRUE['L']}, 'D': {'init': 7.0}, 'Hh': {'init': 4.0}, 'zf': {'init': 0.5}},
        'camera': {'pos': [pos[0] + 3, pos[1] - 2, pos[2] + 0.5], 'target': list(target), 'f_px': f * 0.85},
        'points': pts, 'lines': [],
    }


CAM_A = ((-12.0, -18.0, 1.6), (10.0, 4.0, 3.0), 1500.0)
CAM_B = ((34.0, 22.0, 1.7), (10.0, 4.0, 3.0), 1300.0)


def solve_single(spec):
    prob = Problem(spec)
    r = prob.solve()
    R, C, f, P = prob.unpack(r.x)
    return P, f, prob


def test_exact_marks_recover_the_model(tmp_path):
    P, f, _ = solve_single(spec_for(image(tmp_path), *CAM_A))
    for k in ('D', 'Hh', 'zf'):
        assert P[k] == pytest.approx(TRUE[k], abs=1e-3)
    assert f == pytest.approx(CAM_A[2], rel=1e-3)


def test_noisy_marks_stay_close(tmp_path):
    P, f, _ = solve_single(spec_for(image(tmp_path), *CAM_A, noise=1.0))
    for k in ('D', 'Hh', 'zf'):
        assert P[k] == pytest.approx(TRUE[k], rel=0.03)


def test_distortion_is_recovered_and_needed(tmp_path):
    img = image(tmp_path)
    s = spec_for(img, *CAM_A, k1=-0.04)
    P0, _, prob0 = solve_single(copy.deepcopy(s))
    rms0 = float(np.sqrt(np.mean(prob0.residuals(prob0.solve().x) ** 2)))
    s['camera']['free_distortion'] = True
    P1, _, prob1 = solve_single(s)
    assert prob1.k1 == pytest.approx(-0.04, abs=0.01)
    rms1 = float(np.sqrt(np.mean(prob1.residuals(prob1.solve().x) ** 2)))
    assert rms1 < rms0 / 3
    assert abs(P1['Hh'] - TRUE['Hh']) < abs(P0['Hh'] - TRUE['Hh']) + 1e-3


def test_joint_solve_shares_parameters(tmp_path):
    img = image(tmp_path)
    a = spec_for(img, *CAM_A, noise=1.0, seed=1)
    b = spec_for(img, *CAM_B, noise=1.0, seed=2)
    m = Multi([a, b])
    r = m.solve()
    shared = dict(zip(m.free, r.x[:m.nf]))
    for k in ('D', 'Hh', 'zf'):
        assert shared[k] == pytest.approx(TRUE[k], rel=0.02)
    # each photo keeps its own camera
    fa = math.exp(m.local(r.x, 0)[6])
    fb = math.exp(m.local(r.x, 1)[6])
    assert fa == pytest.approx(CAM_A[2], rel=0.03)
    assert fb == pytest.approx(CAM_B[2], rel=0.03)


def test_joint_fixes_a_photo_that_is_weak_alone(tmp_path):
    """Photo A sees only the near corners on one face: its depth is poorly
    constrained. Joined with B it is pinned down."""
    img = image(tmp_path)
    far = [i for i, c in enumerate(CORNERS) if c[1] == 'D']  # drop the back face
    a = spec_for(img, *CAM_A, noise=2.0, seed=3, drop=far)
    b = spec_for(img, *CAM_B, noise=2.0, seed=4)
    P_alone, _, prob_a = solve_single(copy.deepcopy(a))
    alone = P_alone
    m = Multi([a, b])
    rj = m.solve()
    joint = dict(zip(m.free, rj.x[:m.nf]))
    # the back face is invisible in A alone: D is not measured there at all
    assert abs(joint['D'] - TRUE['D']) < 0.2
    # A alone cannot see D at all; the solver must say so instead of quoting a value
    from solve import unobserved
    assert unobserved(prob_a, prob_a.solve().x) == ['D']


def test_observed_parameters_are_not_flagged(tmp_path):
    from solve import unobserved
    s = spec_for(image(tmp_path), *CAM_A)
    prob = Problem(s)
    assert unobserved(prob, prob.solve().x) == []


def test_mixed_fixed_values_are_refused(tmp_path):
    img = image(tmp_path)
    a = spec_for(img, *CAM_A)
    b = spec_for(img, *CAM_B)
    b['params']['L'] = {'fixed': 21.0}
    with pytest.raises(SystemExit):
        Multi([a, b])


def test_dag_finds_unseen_and_single_mark_parameters(tmp_path):
    s = spec_for(image(tmp_path), *CAM_A)
    s['params']['ghost'] = {'init': 1.0}
    s['params']['once'] = {'init': 1.0}
    # the first three corners are on the x = 0, y = 0 edge: they use zf and Hh, never D
    s['points'] = s['points'][:3] + [{'id': 'only', 'px': [1, 1], 'xyz': ['once', '0', 'zf']}]
    rep = dag.build(s)['report']
    assert set(rep['free_without_marks']) == {'ghost', 'D'}
    assert rep['free_on_one_mark'] == {'Hh': 'p2', 'once': 'only'}


def test_dag_names_ignore_math():
    assert dag.names('math.sqrt(a) + 2*b') == {'a', 'b'}
