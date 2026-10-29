---
name: reverse-cad
description: Reverse-engineer a real building into an explicit parametric model from every source you can lawfully get (measured drawings, published dimensions, photos), grade every parameter by where it came from, and prove the model against the sources. Use when the user names a building, or gives photos or drawings of one, and wants its design logic, dimensions or a parametric Rhino model.
---

# Reverse-engineer a building

The deliverable is a parametric model whose every number says where it came
from and how sure it is, plus the evidence that the model matches its
sources. A model that looks right but cannot show this is not done.

Grades, used on every parameter, in the spec, the model layers and the report:
- **P** published: read off a measured drawing or a dimensioned source;
- **D** measured from a photo with `/reverse-photo`;
- **I** inferred by a design rule from P or D values;
- **A** assumed, with the reason.

## 1. Gather sources into `sources/<building>/`

Collect before modelling, and log each file in `sources/<building>/SOURCES.md`
with author, licence, URL and what it shows.

- **Measured drawings first.** For US buildings, HABS/HAER/HALS sheets
  (Library of Congress, public domain) are on Wikimedia Commons: search
  Commons for `HABS <building name>`. They beat encyclopedia figures: on
  Farnsworth House, Wikipedia's floor height (1.60 m) was off by 0.24 m, the
  HABS section and two photos agreed on 1.84 m.
- **Published dimensions** with the exact sentence they come from. Note the
  datum: "raised 5 ft", "roof 9.5 ft above the floor" often hide which face is
  meant. Record both readings when unsure.
- **Photos** with EXIF focal length when available
  (`commons.wikimedia.org/w/api.php?action=query&prop=imageinfo&iiprop=metadata`).
- **Licence check.** Commons removes photos of buildings whose architect died
  less than 70 years ago in countries without freedom of panorama for
  buildings (France, Italy among them): there are no usable exterior photos
  of Villa Savoye. Pick buildings in countries with that freedom, or older
  ones. Do not use photos you cannot redistribute.

## 2. Write the design logic

Before any number: name the few parameters the architect chose (module, bay,
cantilever, storey height) and the rules tying the rest to them. Write the
rules as expressions over the parameters. Every rule is a prediction you can
test against a source that was not used to set it.

## 3. Measure

- From drawings: read dimension strings directly (P). Where a dimension is
  only drawn, scale it with the sheet's own scale bar and say so. Check the
  scan's scale in both directions against two dimension strings: the Robie
  sheets are 1.6 % shorter down the sheet than across it, enough to move a
  6.85 m wall by 0.11 m. Read a value on two sheets when you can (plan and
  elevation); where they disagree, the difference is the tolerance.
- From photos: run `/reverse-photo` per photo (D). Fix scale with one P value
  and leave the rest free, so the photo checks the drawings rather than
  copying them.
- Keep P values that a photo also measures out of that photo's solve; they are
  the test.

## 4. Build

Generate the Rhino model from the parameter table with a short Python
generator (see `cases/*/model_rhino.py`). One layer per grade. Save the
`.3dm`, and capture each photo's view with `tools/rhino_capture.py`.

## 5. Prove

All of these, with numbers in the report:
1. **Against drawings:** every D and I parameter versus its P value, in % .
2. **Against photos:** `tools/overlay.py` per photo, plus `tools/control.py`
   on the first photo of each kind.
3. **Between photos:** the same parameter from two photos. Agreement between
   independent photos is evidence even where no drawing exists. Then solve
   them together (`tools/solve_multi.py`): on Robie House two photos, each
   3-18 % off alone, came within 0.1-1 % of the drawings together.
4. **Hold-out:** `solve.py --holdout`; name parameters that rest on one mark.
   Then `tools/variants.py` for the spread across camera models.
5. **Undetermined is a result.** Parameters with a bootstrap spread larger
   than the tolerance go in the report as "not determined by these sources",
   never as a value. On Farnsworth the terrace depth was flagged this way and
   the drawings confirmed the guess was meaningless.
6. **A failed check is a result too.** Robie House photo w1 fits itself to
   2.5 px and passes the hold-out and the camera sweep on the walls, and is
   still 11-18 % off the HABS drawings. Report such a case with the overlay of
   the drawing seen through the solved camera (`cases/robie/draw_overlay.py`)
   and do not average it away.

## 6. Deliver

- `cases/<building>/`: specs, results, `.3dm`, renders, overlays.
- The demo page (`tools/build_demo.py`) for anyone to move the parameters and
  watch the model leave the photo.
- A report table: parameter, value, grade, spread, source value, error.
- The model as text: `python -I tools/to_pg.py spec.json result.json --boxes
  cases/<building>/boxes.pg --out model.pg` writes parameters with grades and
  spreads, the case's boxes and the drawing values as checks. `pg check
  model.pg` (vibecading-model) then fails exactly where the model and the
  drawings disagree, and `pg diff` between two solves shows what changed and
  which checks flipped. Commit it: the model's history is its git log.
- Add the case to `tools/bench.py` and regenerate `BENCH.md`.
