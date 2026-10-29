# S. R. Crown Hall as a parametric model, run inside Rhino 8 (Python 3).
# Expects PARAMS (solved from the photo) in globals. Origin on the girder 1 column axis.
import Rhino
import Rhino.Geometry as rg
import System.Drawing as sd

doc = __rhino_doc__
P = PARAMS

# design rules, not measurements
cant = 2 * P['b']          # Mies' 10 ft module: 20 ft cantilever = 2 bays (not visible in this photo)
D = 12 * P['b']            # 120 ft depth = 12 bays (north facade not visible)
x0, x1 = -cant, 3 * P['s'] + cant
girder_w = 0.5


def layer(name, rgb):
    idx = doc.Layers.FindByFullPath(name, -1)
    if idx < 0:
        lay = Rhino.DocObjects.Layer()
        lay.Name = name
        lay.Color = sd.Color.FromArgb(*rgb)
        idx = doc.Layers.Add(lay)
    return idx


def box(xa, xb, ya, yb, za, zb, lay, name):
    b = rg.Box(rg.Plane.WorldXY, rg.Interval(xa, xb), rg.Interval(ya, yb), rg.Interval(za, zb))
    attr = Rhino.DocObjects.ObjectAttributes()
    attr.LayerIndex = lay
    attr.Name = name
    doc.Objects.AddBrep(b.ToBrep(), attr)


doc.ModelUnitSystem = Rhino.UnitSystem.Meters
for o in list(doc.Objects):
    if o.Attributes.Name and o.Attributes.Name.startswith(('fw_', 'ch_')):
        doc.Objects.Delete(o, True)

solved = layer('crownhall::solved', (30, 30, 30))
rule = layer('crownhall::rule', (40, 90, 200))

# roof slab with its fascia, glass box from the middle-tier bottom up to the roof
box(x0, x1, 0, D, P['zr_b'], P['zr_t'], solved, 'ch_roof')
box(x0, x1, 0, D, P['z_mb'], P['zr_b'], rule, 'ch_glass_box')
box(x0, x1, 0, D, P['z_tt'] - 0.03, P['z_tt'] + 0.03, solved, 'ch_transom')
for k in range(4):
    x = k * P['s']
    lay = solved if k in (0, 1, 2) else rule
    # girder above the roof, spanning the depth, on a column at each facade
    box(x - girder_w / 2, x + girder_w / 2, -P['d_c'], D + P['d_c'], P['zr_t'], P['zg'], lay, 'ch_girder_%d' % (k + 1))
    for y0, y1 in ((-P['d_c'], -P['d_c'] + P['wc']), (D + P['d_c'] - P['wc'], D + P['d_c'])):
        box(x - P['wc'] / 2, x + P['wc'] / 2, y0, y1, 0, P['zg'], lay, 'ch_col_%d' % (k + 1))
# mullions on the south facade every bay
n = int(round((x1 - x0) / P['b']))
for i in range(n + 1):
    x = x0 + i * P['b']
    box(x - 0.06, x + 0.06, -0.12, 0, P['z_mb'], P['zr_b'], solved, 'ch_mullion_%d' % i)

doc.Views.Redraw()
print('built', round(x1 - x0, 2), 'x', round(D, 2))
