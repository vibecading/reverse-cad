"""Build studio/index.html: the solved cases as interactive 3D parametric models.

usage: python -I build_studio.py
Reads specs and results from cases/, writes studio/index.html. Open it from
inside the repository (photos are linked relatively); three.js loads from a CDN.
"""
import json
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from dag import build as build_dag, grade  # noqa: E402

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

FARNSWORTH = {'s': 'column bay', 'c': 'cantilever, slab end to column', 'W': 'width of the house',
              'zf_t': 'top of the floor', 'zf_b': 'underside of the floor slab', 'zr_t': 'top of the roof',
              'zr_b': 'underside of the roof (ceiling)', 'x_te': 'east edge of the terrace',
              'y_tf': 'south edge of the terrace', 'y_tn': 'north edge of the terrace', 'h_t': 'top of the terrace',
              'd_t': 'terrace depth', 'x_p': 'terrace post, x', 'y_p': 'terrace post, y',
              'g_x': 'west glass wall', 'g_y': 'glass set back from the edge',
              'zr_b - zf_t': 'floor to ceiling', 'zr_t - zf_t': 'floor to top of roof',
              '2*c + 3*s': 'length of the house', 'n': 'number of bays', 't_len': 'terrace length'}
CROWN = {'b': 'mullion bay (10 ft)', 'c': 'cantilever (end out of frame)', 's': 'column bay under the girders',
         'wc': 'column width', 'd_c': 'column in front of the glass', 'zg': 'top of the girders',
         'zr_t': 'top of the roof', 'zr_b': 'underside of the roof', 'z_tt': 'horizontal mullion',
         'z_mb': 'bottom of the middle glass tier', 'zg - zr_t': 'girder above the roof', 'n': 'number of girders - 1'}
ROBIE = {'Lw': 'west wall of the enclosure', 'Ls': 'south wall of the enclosure',
         'h_ct': 'top of the stone coping', 'h_cb': 'underside of the coping', 'h_b': 'bottom of the brick',
         'rx': 'west edge of the roof', 'rys': 'south edge of the roof', 'ryn': 'north edge of the roof',
         'rzt': 'top of the roof fascia', 'h_cb - h_b': 'height of the brick', 'ryn - rys': 'roof, north to south',
         'fascia': 'roof fascia depth', 'depth': 'living floor depth'}
GAMBLE = {'Ww': 'width of the wing', 'ov': 'gable overhang', 'w2x0': 'upper windows, left', 'w2x1': 'upper windows, right',
          'w2t': 'upper windows, head', 'w2b': 'upper windows, sill', 'w1x0': 'lower windows, left',
          'w1x1': 'lower windows, right', 'w1t': 'lower windows, head', 'w1b': 'lower windows, sill',
          'zap': 'ridge (top of the verge)', 'zve': 'verge, lower ends', 'dv': 'verge in front of the wall',
          'D': 'depth of the wing'}

CASES = [
    {'id': 'farnsworth', 'title': 'Farnsworth House', 'by': 'Mies van der Rohe, 1951',
     'spec': 'cases/farnsworth/spec_9970.json', 'result': 'cases/farnsworth/result_9970.json', 'labels': FARNSWORTH,
     'ref': 'HABS IL-1105 measured drawings'},
    {'id': 'crownhall', 'title': 'S. R. Crown Hall', 'by': 'Mies van der Rohe, 1956',
     'spec': 'cases/crownhall/spec_c1.json', 'result': 'cases/crownhall/result_c1.json', 'labels': CROWN,
     'ref': 'published figures'},
    {'id': 'robie', 'title': 'Robie House', 'by': 'one photo', 'model': 'robie',
     'spec': 'cases/robie/spec_w1.json', 'result': 'cases/robie/result_w1.json', 'labels': ROBIE,
     'ref': 'HABS ILL-1005 measured drawings'},
    {'id': 'robie2', 'title': 'Robie House', 'by': 'two photos together', 'model': 'robie',
     'spec': 'cases/robie/spec_w1.json', 'joint': 'cases/robie/joint_w1_w2.json', 'labels': ROBIE,
     'ref': 'HABS ILL-1005 measured drawings'},
    {'id': 'gamble', 'title': 'Gamble House', 'by': 'Greene & Greene, 1908', 'model': 'gamble',
     'spec': 'cases/gamble/spec_g5.json', 'joint': 'cases/gamble/joint_g5_g4.json', 'labels': GAMBLE,
     'ref': 'Greene & Greene drawings, 1908'},
]


def load(p):
    return json.load(open(os.path.join(ROOT, p), encoding='utf-8'))


data = []
for c in CASES:
    spec = load(c['spec'])
    if 'joint' in c:
        j = load(c['joint'])
        ph = j['photos'][0]
        res = {'camera': ph['camera'], 'principal_point': ph['principal_point'], 'params': j['params'],
               'param_sd': j.get('param_sd', {}), 'photos': len(j['photos'])}
    else:
        res = load(c['result'])
        res['photos'] = 1
    grades = {k: grade(k, p) for k, p in spec['params'].items()}
    data.append({'id': c['id'], 'model': c.get('model', c['id']), 'title': c['title'], 'by': c['by'],
                 'ref': c['ref'], 'labels': c['labels'], 'photo': '../' + spec['image'],
                 'source': spec.get('source', ''), 'points': spec.get('points', []), 'lines': spec.get('lines', []),
                 'truth': spec.get('truth', {}), 'notes': {k: p.get('note', '') for k, p in spec['params'].items()},
                 'fixed': [k for k, p in spec['params'].items() if 'fixed' in p], 'grades': grades,
                 'camera': res['camera'], 'pp': res['principal_point'], 'params': res['params'],
                 'sd': res.get('param_sd', {}), 'photos': res['photos'], 'uses': build_dag(spec)['uses']})

html = open(os.path.join(ROOT, 'tools', 'studio_template.html'), encoding='utf-8').read()
html = html.replace('/*DATA*/null', json.dumps(data, ensure_ascii=False))
os.makedirs(os.path.join(ROOT, 'studio'), exist_ok=True)
open(os.path.join(ROOT, 'studio', 'index.html'), 'w', encoding='utf-8').write(html)
print('studio/index.html', len(html) // 1024, 'KB')
