---
name: reverse-photo
description: Recover a building's design parameters from one photo and rebuild it as a parametric Rhino model, proven by overlaying the model on the photo. Use when the user gives a photo of a building (or names a well-known one) and wants its dimensions, proportions or a parametric model, not just a mesh.
---

# Reverse a building from one photo

The photo is the ground truth. Every number you report must come from marks on
the photo, a stated design rule, or a labelled assumption, and the model must
land on the photo when rendered from the recovered camera. Never print a
PASS, a check mark or a score you did not compute.

Tools live in `tools/` next to this skill's repo root. Run Python with `-I`.
Rhino 8 must be running with the MCP server started (`MCPStart`).

## 1. Choose the photo and the frame

- Prefer a photo where two faces of the building, a ground contact and at least
  two repeated elements (columns, bays, mullions) are visible.
- Record author, licence and source in `photos/CREDITS.md` before using it.
- Fix a model frame and write it into the spec: origin at a building corner on
  grade, x along the main facade, z up, metres.

## 2. Name the parameters before marking anything

Write the design logic first: the few numbers a designer would choose
(bay, cantilever, floor-to-floor, slab depth, set-backs) and the rules that tie
the rest to them (length = 2 × cantilever + n × bay). Rules are where the
reverse engineering lives: a rule can predict a dimension the photo does not
show, and that prediction is a test.

## 3. Mark the photo

- `python -I tools/grid.py photo.jpg out.jpg x0 y0 x1 y1 --step 10` draws a
  labelled pixel grid on a crop. Read marks only from crops at 3× zoom or more;
  reading the full frame is off by 10–20 px.
- Point marks: identifiable corners, each tied to a 3D expression over the
  parameters. Line marks: a 3D segment that must fall on the 2D line through two
  pixels; use these for long edges and for verticals.
- **Mark at least one point on the ground (z = 0).** Without it the height above
  grade is free and the solver can lift the whole building by tens of metres
  while every residual stays small.
- **Fix exactly one dimension for scale** (a published bay, a door, a riser),
  and say which. A single photo gives proportions; scale has to come from
  somewhere.
- **Decide which edge a mark is before marking it**, on the drawing first.
  Layered trim makes this the largest error: on Gamble House the drawing's
  window lines are the outer casing with the sill board, the photo marks were
  the frame inside it, and every window came out about 20 % too small. Prefer
  marks with one obvious edge (wall corners, a ridge apex, a slab end) and,
  for trim, mark the same line the drawing draws.
- **Check the camera's side of the model.** Set the starting camera where the
  photographer stood and make sure x runs left to right in the photo as seen
  from there. Mirrored, the solve starts hundreds of pixels off and runs to
  infinity; `solve.py` now warns about both.
- Put things you assume but cannot see (a hidden post's set-back) in
  `priors` with a sigma in metres, never as silent constants.
- **Check the frame's origin is in the photo.** If every mark is written
  relative to a parameter (all x as `c + ...`), that parameter is a gauge and
  slides freely with the camera. Move the origin to something visible and
  report the hidden dimension as undetermined.
- **Perspective-corrected photos.** If verticals are exactly vertical but the
  horizon (where receding horizontals meet) is far from mid-height, the photo
  was shot with a shift lens or keystone-corrected. Set
  `camera.free_principal_point` to `"y"`. Do not free `x`: it trades off
  against yaw and quietly rescales the heights (seen on Crown Hall: +30 %).

Spec format: see the docstring of `tools/solve.py`. Keep published values in
`truth`; the solver never reads them, they are only for the comparison.

- **Second reader for line marks:** `python -I tools/snap.py spec.json
  snapped.json --tol 3 --ang 3 --report` refits each line mark to the photo's
  own edge segments within 3 px. Solve both and keep the one with the lower
  hold-out error. A mark that moves more than ~3 px, or has a single short
  supporting segment, is ambiguous (two flanges, a gravel stop over a fascia):
  re-read it on a crop. A 6 px window grabbed neighbouring parallel edges on
  both test buildings and made the fit worse.

- **Head-on photos** (one facade, little perspective) cannot tell a near wide
  lens from a far long one; the solver will run to an absurd camera. Take the
  focal length from EXIF (Commons: `prop=imageinfo&iiprop=metadata`;
  `f_px = FocalLength_mm × FocalPlaneXResolution / 25.4 × width_used / width_original`,
  or from the 35 mm equivalent: `f_px = f35 / 36 × width`) and give it as
  `camera.f_px_prior` with `sigma_frac` 0.03. On oblique photos EXIF is a check
  instead: the solved focal length landed within 1.5 % (Crown Hall) and 9 %
  (Farnsworth, probably lens-profile correction) of it.

- **Phone photos.** Modern phones correct their lens in software but a wide
  main camera still leaves some barrel distortion: a long straight eave bends
  by 10 px across the frame. Set `camera.free_distortion: true` to solve one
  radial term `k1` (reported per unit radius at the half-width; Robie w1 gave
  -0.033). Check the file size against the camera's native frame: a file
  smaller than the native width is a crop, possibly off-centre, and the EXIF
  focal length then only bounds the true one.
- **Look at the dependencies before solving:** `python -I tools/dag.py
  spec.json` lists free parameters no mark touches (the photo cannot see them)
  and parameters held by a single mark (one misread pixel moves them freely).

## 4. Solve

`python -I tools/solve.py spec.json --boot 100 --out result.json`

Read three things:
- `rms_px` and `per_mark_px`: one mark far above the rest is a misread mark.
  Re-read it on a tighter crop rather than dropping it.
- `unobserved`: free parameters no mark responds to. The optimiser leaves
  them anywhere (a synthetic test saw one drift from 7.0 to 4.0), so never
  quote them; add a mark or fix them as an assumption.
- `param_sd` from the bootstrap: a parameter with a large spread is not
  determined by this photo. Report it as undetermined; do not quote its value.
- `vs_truth`: errors against published dimensions. Report them all, including
  the bad ones. If a published figure cannot be what you compared it with
  (Crown Hall's window tiers add up to more than the storey), say so instead
  of picking the reading that fits.
- `--holdout` re-solves without each mark and reports how far the model then
  misses it. A typical mark should be predicted within a few pixels. A mark
  with a huge hold-out error is the only evidence for some parameter: that
  parameter rests on one reading and the report must say which.
- **Camera-assumption sweep:** `python -I tools/variants.py spec.json`
  re-solves with a plain pinhole, a keystone shift, a radial distortion, and a
  loose and tight focal prior, keeps the variants that fit and have a
  plausible camera, and reports how far each parameter moves between them. The
  bootstrap cannot see this: it jitters marks under one camera model. On
  Farnsworth the sweep flagged exactly the terrace edges that the drawings
  later showed to be undetermined; on Robie w1 it flagged the roof (off by
  0.4-2 m) while the bootstrap gave it +-0.2 m.
- **What none of these checks catch.** Robie w1 fitted to 2.5 px with a 2.9 px
  hold-out, and the sweep called its wall heights stable to 1 %, yet they are
  11 % above the HABS drawings, which agree with each other across three
  sheets. A systematic error in how a mark was read (which corner, which edge
  of a coping) or in what the photo is (an edited crop) passes every internal
  check. Only an independent source finds it: a drawing or a second photo.
  Never present an internally consistent solve as a measurement until one of
  those agrees. On Robie the second photo (w2, from the north-west) did catch
  it with no drawings at all: the same heights came out 13-17 % lower than in
  w1, with the drawings in between.
- `camera.free_aspect` solves a non-square pixel ratio, for photos that were
  stretched by an editor. With only a horizontal scale and parallel verticals
  it trades off one for one against every height (Robie: ratio 1.21 and 1.35,
  no better fit), so use it only when both a height and a length are known.

## 5. Build and capture in Rhino

Write the model as a short Rhino Python generator over the solved parameters.
Put geometry on three layers: `solved` (measured from the photo), `rule`
(placed by a design rule) and `assumed` (neither). These are the same grades
as D / I / A (measured / inferred / assumed) used by other photo-to-parametric
tools; keep the names in the report so readers can compare. Then run
`tools/rhino_capture.py` with `RESULT`, `SIZE` (the photo's size) and `OUT`
in globals: it sets the viewport frustum from the focal length in pixels, so
the capture is pixel-aligned with the photo. Save the `.3dm` next to it.

## 6. Prove it

`python -I tools/overlay.py photo.jpg render.png spec.json result.json overlay.jpg`

The score counts model edge pixels lying within 3 px of a photo edge running
the same direction, with vertical and horizontal edges scored apart; the
headline is the worse of the two. Look at the overlay picture as well as the
number: a part that misses the photo is either a misread mark or a wrong rule.

Run `python -I tools/control.py photo.jpg render.png spec.json result.json`
once per new kind of photo. It re-scores the render shifted by 5–40 px; if the
score barely drops, the metric is not measuring fit on this photo (usually
foliage or repetitive facades) and you must say so.

## 7. Cross-check with a second photo

Where a second photo from another side exists, solve it on its own and
compare the shared parameters. Two photos that agree with each other but not
with a published figure usually mean the publication measured from another
datum (Farnsworth: both photos give the floor at 1.80–1.84 m above the grade
at the columns, the article says 1.60 m). This check needs no published data
at all, so it is the one to use for buildings nobody has measured. It is
also the only check that caught Robie House w1, whose hold-out and camera
sweep were both quiet.

Then solve the photos **together**: `python -I tools/solve_multi.py
spec_a.json spec_b.json --boot 30`. Parameters with the same name are one
unknown, each photo keeps its own camera. A single photo is weak along its own
depth direction; two photos from different sides cover each other's weak
direction. On Robie, w1 alone was 11-18 % off the drawings and w2 alone 3-9 %
the other way; together they came within 0.1 % on the coping heights and 1 %
on the wall length. The output lists each photo's rms in the joint solve next
to its rms alone: a photo whose rms jumps does not agree with the others, and
its marks are the first to re-read.

## 8. Report

One table: parameter, value, bootstrap spread, published value, error. Then the
overlay image, the two overlay scores, what was ruled or assumed, and what this
photo cannot determine. Keep the spec, result, render, overlay and `.3dm` in
`cases/<building>/`.
