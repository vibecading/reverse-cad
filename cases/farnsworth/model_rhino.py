# Farnsworth House as a parametric model, run inside Rhino 8 (Python 3).
# Expects PARAMS (solved from the photo) and ASSUMED (not seen in the photo) in globals.
# Layers say which is which, so an overlay never passes off an assumption as a measurement.
import Rhino
import Rhino.Geometry as rg
import System.Drawing as sd

doc = __rhino_doc__
P = PARAMS
A = ASSUMED

# design rules, not measurements: Mies made the plan symmetric about the bays
L = 2 * P['c'] + 3 * P['s']
col = 0.2  # W8 column flange width


def layer(name, rgb):
    idx = doc.Layers.FindByFullPath(name, -1)
    if idx < 0:
        lay = Rhino.DocObjects.Layer()
        lay.Name = name
        lay.Color = sd.Color.FromArgb(*rgb)
        idx = doc.Layers.Add(lay)
    return idx


def box(x0, x1, y0, y1, z0, z1, lay, name):
    b = rg.Box(rg.Plane.WorldXY, rg.Interval(x0, x1), rg.Interval(y0, y1), rg.Interval(z0, z1))
    attr = Rhino.DocObjects.ObjectAttributes()
    attr.LayerIndex = lay
    attr.Name = name
    doc.Objects.AddBrep(b.ToBrep(), attr)


doc.ModelUnitSystem = Rhino.UnitSystem.Meters
for o in list(doc.Objects):
    if o.Attributes.Name and o.Attributes.Name.startswith('fw_'):
        doc.Objects.Delete(o, True)

solved = layer('farnsworth::solved', (30, 30, 30))
rule = layer('farnsworth::rule', (40, 90, 200))
assumed = layer('farnsworth::assumed', (220, 60, 140))

box(0, L, 0, P['W'], P['zf_b'], P['zf_t'], solved, 'fw_floor_slab')
box(0, L, 0, P['W'], P['zr_b'], P['zr_t'], solved, 'fw_roof_slab')
for i in range(4):
    x = P['c'] + i * P['s']
    lay = solved if i < 2 else rule  # only the two west bays are in the photo
    box(x - col / 2, x + col / 2, -col, 0, 0, P['zr_t'] - 0.03, lay, 'fw_col_S%d' % (i + 1))
    box(x - col / 2, x + col / 2, P['W'], P['W'] + col, 0, P['zr_t'] - 0.03, lay, 'fw_col_N%d' % (i + 1))

# glass enclosure: west wall and south set-back solved; east and north walls
# take the same set-back by rule
gy = P['g_y']
box(P['g_x'], L - gy, gy, P['W'] - gy, P['zf_t'], P['zr_b'], solved, 'fw_glass')

# terrace: east end, top and fascia solved; west end out of frame
box(P['x_te'] - A['terrace_len'], P['x_te'], P['y_tf'], P['y_tn'],
    P['h_t'] - P['d_t'], P['h_t'], solved, 'fw_terrace')

doc.Views.Redraw()
print('built, L =', round(L, 3))
