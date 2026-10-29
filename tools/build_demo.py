"""Build demo/index.html: the solved cases with a live parametric wireframe over the photo.

usage: python -I build_demo.py
Reads cases/*/spec_*.json and result_*.json, writes demo/index.html.
Photos and renders are linked relatively, so open the file from inside the repo.
"""
import json
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from dag import build as build_dag  # noqa: E402

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

CASES = [
    {'id': 'farnsworth', 'title': 'Farnsworth House', 'by': 'Mies van der Rohe, 1951',
     'spec': 'cases/farnsworth/spec_9970.json', 'result': 'cases/farnsworth/result_9970.json',
     'render': 'cases/farnsworth/render_9970.png', 'model': 'farnsworth',
     'grades': {'s': 'scale'},
     'labels': {'s': 'column bay', 'c': 'cantilever, slab end to column', 'W': 'width of the house',
                'zf_t': 'top of the floor', 'zf_b': 'underside of the floor slab', 'zr_t': 'top of the roof', 'zr_b': 'underside of the roof (ceiling)',
                'x_te': 'east edge of the terrace', 'y_tf': 'south edge of the terrace', 'y_tn': 'north edge of the terrace',
                'h_t': 'top of the terrace', 'd_t': 'terrace depth', 'x_p': 'terrace post, x', 'y_p': 'terrace post, y',
                'g_x': 'west glass wall', 'g_y': 'glass set back from the edge',
                'zr_b - zf_t': 'floor to ceiling', 'zr_t - zf_t': 'floor to top of roof',
                '2*c + 3*s - g_x - g_y': 'length of the glass volume', '2*c + 3*s': 'length of the house (rule)'}},
    {'id': 'crownhall', 'title': 'S. R. Crown Hall', 'by': 'Mies van der Rohe, 1956',
     'spec': 'cases/crownhall/spec_c1.json', 'result': 'cases/crownhall/result_c1.json',
     'render': 'cases/crownhall/render_c1.png', 'model': 'crownhall',
     'grades': {'b': 'scale', 'c': 'gauge'},
     'labels': {'b': 'mullion bay (10 ft)', 'c': 'cantilever (end out of frame)', 's': 'column bay under the girders',
                'wc': 'column width', 'd_c': 'column in front of the glass', 'zg': 'top of the girders',
                'zr_t': 'top of the roof', 'zr_b': 'underside of the roof (ceiling)', 'z_tt': 'horizontal mullion',
                'z_mb': 'bottom of the middle glass tier',
                'zg - zr_t': 'girder above the roof', 'z_tt - z_mb': 'middle glass tier',
                'zr_b - z_tt': 'upper glass tier'}},
    {'id': 'robie', 'title': 'Robie House', 'by': 'Frank Lloyd Wright, 1910',
     'spec': 'cases/robie/spec_w1.json', 'result': 'cases/robie/result_w1.json',
     'render': None, 'model': 'robie', 'open_case': True,
     'grades': {'Lw': 'scale'},
     'labels': {'Lw': 'west wall of the enclosure (scale, HABS)', 'Ls': 'south wall of the enclosure',
                'h_ct': 'top of the stone coping', 'h_cb': 'underside of the coping', 'h_b': 'bottom of the brick',
                'rx': 'west edge of the roof', 'rys': 'south edge of the roof', 'ryn': 'north edge of the roof',
                'rzt': 'top of the roof fascia (HABS)'}},
    {'id': 'robie2', 'title': 'Robie House', 'by': 'two photos together',
     'spec': 'cases/robie/spec_w1.json', 'joint': 'cases/robie/joint_w1_w2.json', 'joint_photo': 0,
     'render': None, 'model': 'robie', 'joint_case': True,
     'grades': {'Lw': 'scale'}},
]

data = []
for c in CASES:
    spec = json.load(open(os.path.join(ROOT, c['spec']), encoding='utf-8'))
    if 'joint' in c:
        # the joint solve seen through one of its photos: that photo's camera, the shared parameters
        j = json.load(open(os.path.join(ROOT, c['joint']), encoding='utf-8'))
        ph = j['photos'][c['joint_photo']]
        res = {'camera': ph['camera'], 'principal_point': ph['principal_point'], 'params': j['params'],
               'param_sd': j.get('param_sd', {})}
        c = {**c, 'labels': next(x for x in CASES if x['id'] == 'robie')['labels']}
    else:
        res = json.load(open(os.path.join(ROOT, c['result']), encoding='utf-8'))
    g = build_dag(spec)
    vpath = os.path.join(ROOT, c['spec'].replace('spec_', 'variants_'))
    spread = {}
    if os.path.exists(vpath) and 'joint' not in c:  # the sweep was run on single photos
        spread = {k: v['spread_pct'] for k, v in json.load(open(vpath, encoding='utf-8'))['spread'].items()}
    data.append({**c, 'spec': spec, 'result': res, 'uses': g['uses'], 'dag_report': g['report'], 'spread': spread,
                 'photo': '../' + spec['image'], 'render': '../' + c['render'] if c['render'] else ''})

html = open(os.path.join(ROOT, 'tools', 'demo_template.html'), encoding='utf-8').read()
html = html.replace('/*DATA*/null', json.dumps(data, ensure_ascii=False))
os.makedirs(os.path.join(ROOT, 'demo'), exist_ok=True)
open(os.path.join(ROOT, 'demo', 'index.html'), 'w', encoding='utf-8').write(html)
print('demo/index.html', len(html) // 1024, 'KB')
