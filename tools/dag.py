"""Dependency graph of a spec: parameters -> marks and rules -> checks.

usage: python -I dag.py spec.json [out.json] [--svg out.svg]

The spec already is the model's logic: every mark and every check is an
expression over named parameters. This reads those expressions and writes the
graph explicitly, so it can be drawn, diffed and checked:

  param  (grade P drawing/published, A assumed or gauge, D solved from the photo)
    -> mark   (a point or line on the photo whose 3D position uses the param)
    -> rule   (a derived quantity such as "2*c + 3*s")
    -> check  (a truth value the solve never saw)

It also prints what the graph alone can tell before any solve: free parameters
no mark touches (the photo cannot determine them) and parameters held by one
mark only (a misread mark moves them freely; see --holdout in solve.py).
"""
import ast
import json
import sys

P_WORDS = ('habs', 'drawing', 'published', 'sheet', 'plan', 'elevation', 'dimension')


def names(expr):
    return {n.id for n in ast.walk(ast.parse(str(expr), mode='eval')) if isinstance(n, ast.Name) and n.id != 'math'}


def grade(name, p):
    if 'grade' in p:
        return p['grade']
    if 'fixed' not in p:
        return 'D'
    note = p.get('note', '').lower()
    return 'P' if any(w in note for w in P_WORDS) else 'A'


def build(spec):
    params = spec['params']
    nodes, edges = [], []
    for k, p in params.items():
        nodes.append({'id': k, 'kind': 'param', 'grade': grade(k, p), 'note': p.get('note', '')})
    uses = {k: [] for k in params}
    for kind in ('points', 'lines'):
        for m in spec.get(kind, []):
            mid = 'mark:' + m['id']
            nodes.append({'id': mid, 'kind': 'mark', 'shape': kind[:-1], 'label': m['id']})
            exprs = m['xyz'] if kind == 'points' else [e for end in m['xyz'] for e in end]
            for n in sorted(set().union(*(names(e) for e in exprs)) & set(params)):
                edges.append([n, mid])
                uses[n].append(m['id'])
    for pr in spec.get('priors', []):
        pid = 'prior:' + pr['expr']
        nodes.append({'id': pid, 'kind': 'prior', 'label': pr['expr'], 'value': pr['value']})
        for n in sorted(names(pr['expr']) & set(params)):
            edges.append([n, pid])
    for t, v in spec.get('truth', {}).items():
        src = t
        if t not in params:  # a rule: a derived quantity checked as a whole
            src = 'rule:' + t
            nodes.append({'id': src, 'kind': 'rule', 'label': t})
            for n in sorted(names(t) & set(params)):
                edges.append([n, src])
        cid = 'check:' + t
        nodes.append({'id': cid, 'kind': 'check', 'label': t, 'value': v})
        edges.append([src, cid])
    free = [k for k, p in params.items() if 'fixed' not in p]
    report = {
        'free_without_marks': [k for k in free if not uses[k]],
        'free_on_one_mark': {k: uses[k][0] for k in free if len(uses[k]) == 1},
        'fixed_unused': [k for k, p in params.items() if 'fixed' in p and not uses[k]],
        'checked': sorted({n for t in spec.get('truth', {}) for n in names(t)} & set(params)),
    }
    report['free_unchecked'] = [k for k in free if k not in report['checked']]
    return {'nodes': nodes, 'edges': edges, 'uses': uses, 'report': report}


COL = {'P': '#2f7d4f', 'D': '#e0218a', 'A': '#f2b705', 'I': '#4f8cff'}


def svg(g, title=''):
    """Three columns: parameters, marks and rules, checks. Edges are drawn faint;
    a parameter's colour is its grade."""
    cols = {'param': [], 'mark': [], 'prior': [], 'rule': [], 'check': []}
    for n in g['nodes']:
        cols[n['kind']].append(n)
    left = cols['param']
    mid = cols['mark'] + cols['prior'] + cols['rule']
    right = cols['check']
    rowh, top = 22, 40
    H = top + rowh * max(len(left), len(mid), len(right), 1) + 20
    X = {'l': 20, 'm': 300, 'r': 600}
    pos = {}
    for x, col in ((X['l'], left), (X['m'], mid), (X['r'], right)):
        for i, n in enumerate(col):
            pos[n['id']] = (x, top + i * rowh)
    out = ['<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 820 %d" font-family="system-ui, sans-serif" font-size="12">' % H,
           '<rect width="100%" height="100%" fill="#fff"/>',
           '<text x="20" y="22" font-size="14" font-weight="700">%s</text>' % title]
    for a, b in g['edges']:
        (x1, y1), (x2, y2) = pos[a], pos[b]
        out.append('<path d="M%d %d C%d %d %d %d %d %d" fill="none" stroke="#8795a1" stroke-opacity=".35"/>'
                   % (x1 + 150, y1, x1 + 220, y1, x2 - 70, y2, x2 - 6, y2))
    for n in g['nodes']:
        x, y = pos[n['id']]
        if n['kind'] == 'param':
            out.append('<circle cx="%d" cy="%d" r="5" fill="%s"/>' % (x + 4, y - 4, COL.get(n['grade'], '#999')))
            out.append('<text x="%d" y="%d">%s <tspan fill="#5b6875">%s</tspan></text>' % (x + 14, y, n['id'], n['grade']))
        elif n['kind'] == 'check':
            out.append('<text x="%d" y="%d">%s = %s</text>' % (x, y, n['label'], n['value']))
        else:
            mark = {'mark': '◦', 'prior': '≈', 'rule': 'ƒ'}[n['kind']]
            out.append('<text x="%d" y="%d"><tspan fill="#5b6875">%s</tspan> %s</text>' % (x, y, mark, n['label']))
    out.append('</svg>')
    return '\n'.join(out)


def main():
    spec = json.load(open(sys.argv[1], encoding='utf-8'))
    g = build(spec)
    args = [a for a in sys.argv[2:] if not a.startswith('--')]
    if '--svg' in sys.argv:
        p = sys.argv[sys.argv.index('--svg') + 1]
        args = [a for a in args if a != p]
        open(p, 'w', encoding='utf-8').write(svg(g, spec.get('image', '')))
    if args:
        json.dump(g, open(args[0], 'w', encoding='utf-8'), indent=1, ensure_ascii=False)
    print(json.dumps(g['report'], indent=1, ensure_ascii=False))


if __name__ == '__main__':
    main()
