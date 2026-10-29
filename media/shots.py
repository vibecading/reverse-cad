"""Screenshots of the studio for the README: media/shots/*.jpg at 1600 px.

usage: python -I media/shots.py      (from the repo root; CHROMIUM as for record.py)
"""
import os
import pathlib

import cv2
from playwright.sync_api import sync_playwright

ROOT = pathlib.Path(__file__).resolve().parent.parent
OUT = ROOT / 'media' / 'shots'

SHOTS = [
    ('1-model', "studio.select(0); studio.view('3d', 0); studio.orbit.az = -0.75; studio.orbit.el = 0.42", 2600),
    ('2-plan', "studio.view('plan', 0)", 700),
    ('3-graph', "studio.view('graph', 0); studio.hot('s')", 700),
    ('4-photo', "studio.hot(null); studio.view('photo', 0)", 1500),
    ('5-review', "studio.view('review', 0); studio.review(0); studio.accept(); studio.review(1)", 1200),
    ('6-gamble', "studio.view('3d', 0); studio.select(4); studio.view('photo', 0)", 2200),
    ('7-robie', "studio.truth(true); studio.select(3); studio.view('photo', 0)", 2200),
]


def main():
    OUT.mkdir(parents=True, exist_ok=True)
    with sync_playwright() as p:
        b = p.chromium.launch(executable_path=os.environ.get('CHROMIUM') or None, args=['--allow-file-access-from-files'])
        pg = b.new_page(viewport={'width': 1920, 'height': 1080})
        pg.goto((ROOT / 'studio' / 'index.html').as_uri())
        pg.wait_for_function('window.studio !== undefined')
        pg.wait_for_timeout(2500)
        for name, js, ms in SHOTS:
            pg.evaluate(js)
            pg.wait_for_timeout(ms)
            png = str(OUT / (name + '.png'))
            pg.screenshot(path=png)
            im = cv2.imread(png)
            cv2.imwrite(str(OUT / (name + '.jpg')), cv2.resize(im, (1600, 900), interpolation=cv2.INTER_AREA), [cv2.IMWRITE_JPEG_QUALITY, 88])
            os.remove(png)
            print(name)
        b.close()


if __name__ == '__main__':
    main()
