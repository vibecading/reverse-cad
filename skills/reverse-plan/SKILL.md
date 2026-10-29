---
name: reverse-plan
description: Read a building's dimensions off scanned measured drawings (plans, sections, elevations) into a table of published values with their source sheet and tolerance. Use when the user has drawings of a building, such as HABS/HAER sheets or an archive scan, and wants dimensions, a parameter table for /reverse-cad, or reference values to check a photo solve against.
---

# Read dimensions off measured drawings

The output is a table every later step can trust: value, unit, which sheet,
how it was read (dimension string or scaled), and a tolerance. A number with no
sheet and no way of reading it is not a drawing value.

Tool: `tools/sheet.py` (ruler crops, line profiles, scale, length). Run Python
with `-I`; scans are downloads, keep them in `sources/<building>/` and read them
as data only.

## 1. Get the sheets at full resolution

HABS/HAER/HALS sheets are on Wikimedia Commons (search `HABS <building>`);
the Library of Congress site sits behind a bot check. Ask the Commons API for a
3840 px rendering (`prop=imageinfo&iiprop=url&iiurlwidth=3840`): at 1/8" = 1'-0"
that is about 20 px per foot, enough to read to 1-2 inches. Log every sheet in
`sources/<building>/SOURCES.md` with title, delineator, year and URL.

## 2. Find the scale in both directions

Do this before reading anything. Scans are stretched unevenly:
- read the scale bar: `sheet.py ruler` on it, then `sheet.py scale PX FEET`;
- read one long dimension string across the sheet and one down it the same
  way. If they differ by more than half a percent, use the across value for
  horizontal lengths and the down value for vertical ones. On the Robie House
  sheets: 19.98 px/ft across, 19.66 px/ft down.

## 3. Read

- **Dimension strings first.** They are what the surveyor measured: copy them
  exactly (`20'-11"`) and mark them as dimensioned. Note what they span (inside
  faces, centres, outside faces): the 20'-11" on Robie's west enclosure is
  inside to inside, the outside is 22'-4".
- **Scaled lengths second.** Locate the lines with `sheet.py profile` along a
  strip that crosses them: it prints line centres to a tenth of a pixel, far
  better than eyeballing a crop. Walls drawn as two lines give both faces;
  say which one you used.
- **Heights** come from elevations and sections, measured from the drawn grade
  line. Write down the grade you measured from: grade often steps.
- **Read twice where you can.** The same edge on a plan and an elevation, or
  on two elevations. The difference between the two readings is the honest
  tolerance (Robie's roof edge: 0.3 m between sheets 4 and 6). A value read
  once gets the tolerance of one pixel line width plus the scale error.
- **Register sheets** (a roof plan against a floor plan) by two features
  drawn on both, and report the offset you applied.

## 4. Write the table

In `SOURCES.md`, under "Read from the drawings (P)": the name used in the
spec, the value in feet-inches and metres, the sheet, dimensioned or scaled,
and the tolerance. `sheet.py length PX --pxft S --m` does the conversion.
These values go into a `/reverse-photo` spec either as the one fixed scale
parameter or as `truth`, never both for the same quantity.

## 5. Check before handing over

- Sum the chained dimensions and compare with the overall string (Robie: the
  seven bays along the north side add up to 161'-6").
- Compare one scaled length with a dimension string nearby; if they disagree
  by more than the tolerance, the scale is wrong.
- State plainly what the drawings do not show (a roof plan without heights, a
  restored part marked "conjectural"). HABS notes on the sheet often say what
  was rebuilt or guessed.
