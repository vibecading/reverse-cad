# Skills

Agent skills for turning a real building into an explicit parametric model.
Each is a `SKILL.md` an agent loads on demand; the tools they call are in
`../tools/`.

| skill | use it when | main tools |
|---|---|---|
| [reverse-cad](reverse-cad/SKILL.md) | a building is named or its sources are given and a graded parametric model is wanted; it runs the other two | all of them |
| [reverse-photo](reverse-photo/SKILL.md) | photos of a building: recover the cameras and the design parameters, prove the fit on each photo | `solve.py`, `solve_multi.py`, `variants.py`, `dag.py`, `grid.py`, `segments.py`, `snap.py`, `rhino_capture.py`, `overlay.py`, `control.py` |
| [reverse-plan](reverse-plan/SKILL.md) | scanned measured drawings: read dimensions into a table of drawing values with tolerances | `sheet.py` |

Grades used everywhere: **P** read off a drawing or a dimensioned source,
**D** measured from a photo, **I** inferred by a design rule, **A** assumed.

Cases that exercised the skills: `../cases/farnsworth` (two photos, HABS
drawings: within 4.1 %, the terrace edges not fixed), `../cases/crownhall` (one photo, published
figures), `../cases/robie` (two phone photos, HABS drawings: each photo alone is
self-consistent and up to 18 % off; solved together the walls and coping land
within 1 %, the brick plinth 5.4 % off).

Tests: `python -I -m pytest tests -q` runs synthetic checks of the solvers (a
known building, known cameras): single and joint solves recover it, distortion
is recovered, and an invisible parameter is reported as unobserved, not as a
value.
