"""Record the studio walkthrough: photo in, parametric model out. Page only, captions burned in.

usage: python -I media/record_studio.py [out_dir]     (from the repo root)
Needs Playwright with its ffmpeg (PLAYWRIGHT_BROWSERS_PATH) and network access
for three.js; set CHROMIUM to a browser executable if Playwright's own is not
installed. Writes out_dir/studio_raw.webm; media/encode.sh studio makes the mp4.
"""
import os
import pathlib
import shutil
import sys

from playwright.sync_api import sync_playwright

ROOT = pathlib.Path(__file__).resolve().parent.parent
OUT = pathlib.Path(sys.argv[1] if len(sys.argv) > 1 else ROOT / 'media' / 'build')
W, H = 1920, 1080

OVERLAY = """
(() => {
  if (document.getElementById('cap')) return;
  const st = document.createElement('style');
  st.textContent = `
    #cap{position:fixed;left:calc(50% + 170px);bottom:38px;transform:translateX(-50%);max-width:1300px;z-index:99;
         background:rgba(16,24,32,.9);color:#fff;font:600 29px/1.3 "Golos Text",system-ui,sans-serif;
         padding:15px 28px;border-radius:8px;text-align:center;transition:opacity .35s;pointer-events:none}
    #cap small{display:block;font-weight:400;font-size:20px;color:#c9d3dc;margin-top:4px}
    #card{position:fixed;inset:0;z-index:100;background:#15202b;color:#fff;display:flex;flex-direction:column;
          justify-content:center;align-items:center;gap:18px;font-family:"Golos Text",system-ui,sans-serif;transition:opacity .5s}
    #card h1{font-size:64px;margin:0;font-weight:700;letter-spacing:-.01em}
    #card p{font-size:30px;margin:0;color:#c9d3dc;max-width:1300px;text-align:center;line-height:1.35}
    #card code{font-size:28px;color:#7fdbff}
    #cursor{position:fixed;z-index:98;width:26px;height:26px;pointer-events:none;left:-40px;top:-40px;transition:transform .08s}
    #cursor.down{transform:scale(.85)}`;
  document.head.appendChild(st);
  const c = document.createElement('div'); c.id = 'cap'; c.style.opacity = 0; document.body.appendChild(c);
  // a visible pointer: headless recordings have none
  const k = document.createElement('div'); k.id = 'cursor';
  k.innerHTML = '<svg viewBox="0 0 26 26" width="26" height="26"><path d="M3 2 L3 21 L8 16 L12 24 L15 23 L11 15 L18 15 Z" fill="#fff" stroke="#15202b" stroke-width="1.6" stroke-linejoin="round"/></svg>';
  document.body.appendChild(k);
  addEventListener('mousemove', e => { k.style.left = e.clientX - 3 + 'px'; k.style.top = e.clientY - 2 + 'px'; }, true);
  addEventListener('mousedown', () => k.classList.add('down'), true);
  addEventListener('mouseup', () => k.classList.remove('down'), true);
})()
"""


def run():
    OUT.mkdir(parents=True, exist_ok=True)
    vid = OUT / 'video_studio'
    shutil.rmtree(vid, ignore_errors=True)
    with sync_playwright() as p:
        b = p.chromium.launch(executable_path=os.environ.get('CHROMIUM') or None,
                              args=['--allow-file-access-from-files', '--ignore-gpu-blocklist'])
        ctx = b.new_context(viewport={'width': W, 'height': H}, record_video_dir=str(vid),
                            record_video_size={'width': W, 'height': H})
        pg = ctx.new_page()
        wait = lambda s: pg.wait_for_timeout(int(s * 1000))
        js = lambda code, arg=None: pg.evaluate(code, arg)

        def cap(text, sub=''):
            js("([t, s]) => { const c = document.getElementById('cap'); c.innerHTML = t + (s ? '<small>' + s + '</small>' : ''); c.style.opacity = t ? 1 : 0; }", [text, sub])

        def card(title, sub='', code=''):
            js("""([t, s, c]) => { let d = document.getElementById('card');
                if (!d) { d = document.createElement('div'); d.id = 'card'; document.body.appendChild(d); }
                d.innerHTML = '<h1>' + t + '</h1>' + (s ? '<p>' + s + '</p>' : '') + (c ? '<code>' + c + '</code>' : '');
                d.style.opacity = 1; }""", [title, sub, code])

        def uncard():
            js("() => { const d = document.getElementById('card'); if (d) { d.style.opacity = 0; setTimeout(() => d.remove(), 500); } }")

        def animate(k, to, ms):
            js("([k, v, ms]) => { studio.animate(k, v, ms); }", [k, to, int(ms)])  # do not wait for it

        def center(sel):
            bb = pg.locator(sel).first.bounding_box()
            return bb['x'] + bb['width'] / 2, bb['y'] + bb['height'] / 2

        def click(sel, steps=18):
            x, y = center(sel)
            pg.mouse.move(x, y, steps=steps); wait(0.25); pg.mouse.down(); wait(0.12); pg.mouse.up()

        def drag(sel, dx, dy, ms):
            x, y = center(sel)
            pg.mouse.move(x, y, steps=15); wait(0.2); pg.mouse.down()
            n = max(10, int(ms / 40))
            for i in range(1, n + 1):
                pg.mouse.move(x + dx * i / n, y + dy * i / n); pg.wait_for_timeout(40)
            wait(0.3); pg.mouse.up()

        def open_case(i, title, sub):
            """A photo comes in, then the model builds itself from it."""
            js("i => { studio.view('3d', 0); studio.spin(false); studio.select(i); }", i)
            cap(title, sub)
            js("() => { studio.reference(2400); }")
            wait(2.6)
            js("i => { studio.select(i); studio.spin(true); }", i)  # select again: the build-up starts as the reference closes

        pg.goto((ROOT / 'studio' / 'index.html').as_uri())
        pg.wait_for_function('window.studio !== undefined', timeout=30000)
        wait(1.5)
        js(OVERLAY)
        card('Photo in, parametric model out',
             'Four real buildings, rebuilt from ordinary photos<br>and checked against their measured drawings')
        wait(4.5)
        uncard()

        # Farnsworth: the full tour
        open_case(0, 'A photo comes in: Farnsworth House', 'Mies van der Rohe, 1951 · one photo, CC BY-SA')
        cap('Camera and design parameters, solved together', 'every element is a formula over named parameters')
        wait(4.0)
        cap('The design logic comes back with it', 'length = 2 × cantilever + bays × column bay')
        animate('n', 5, 2600)
        wait(3.0)
        animate('c', 3.2, 1600)
        wait(2.0)
        js('() => studio.reset()')
        wait(0.8)
        js("() => { studio.spin(false); studio.view('graph', 0); studio.hot('W'); }")
        cap('Which parameter moves which element', 'the dependency graph, read off the model itself')
        wait(4.0)
        js("() => { studio.hot('n'); }")
        wait(2.0)
        js("() => { studio.hot(null); studio.view('plan', 0); }")
        cap('The plan is parametric too', 'dimensions in metres, measured from the photo')
        wait(2.5)
        cap('Drag a grip: plan, 3D and the checks follow', 'and the error on the photo shows how far you left the building')
        drag('#plan circle.grip[data-k="s"]', 150, 0, 2400)
        wait(1.4)
        drag('#plan circle.grip[data-k="W"]', 0, -70, 1400)
        wait(1.4)
        js('() => studio.reset()')
        pg.mouse.move(1900, 1060, steps=10)
        js("() => { studio.view('3d', 0); }")
        wait(0.6)
        js("() => studio.view('photo', 2200)")
        cap('Back through the recovered camera', 'the model lands on the photo')
        wait(3.4)
        cap('2.0 px on the photo · within 4 % of the HABS drawings', 'where one photo fixes a value; the rest is marked not fixed')
        wait(4.0)

        # Crown Hall: the bays again
        open_case(1, 'S. R. Crown Hall', 'Mies van der Rohe, 1956 · one public-domain photo')
        cap('Same recipe, a 66 m clear span', 'add girder bays: the rule keeps the cantilevers at 2 × 10 ft')
        animate('n', 5, 2400)
        wait(2.8)
        js('() => studio.reset()')
        js("() => studio.view('photo', 2000)")
        wait(3.2)

        # Gamble: pitched roofs
        open_case(4, 'Pitched roofs too: Gamble House', 'Greene & Greene, 1908 · two phone photos')
        cap('Roof pitch, overhang, ridge: all parameters', 'raise the ridge and the pitch follows')
        animate('zap', 8.6, 2200)
        wait(2.4)
        animate('ov', 2.4, 1500)
        wait(1.8)
        js('() => studio.reset()')
        js("() => studio.view('photo', 2000)")
        cap('Checked against the 1908 drawings', 'within 5–15 %: layered trim makes the marks the hard part')
        wait(4.2)

        # Robie: why one photo is not enough
        js("() => { studio.truth(true); studio.select(2); }")
        cap('Robie House, one iPhone photo: 2.5 px on the photo…', '…and 11–18 % off the drawings (green dashed)')
        wait(5.0)
        js("() => studio.select(3)")
        cap('Two photos, solved together: within 1 %', 'one building, two cameras, shared parameters')
        wait(5.0)
        cap('')

        # versions and review, for people who do not use git
        js("() => { studio.truth(false); studio.select(0); studio.view('review', 0); studio.spin(true); }")
        cap('A model with a history', 'proposals from colleagues and agents, reviewed before they land')
        wait(3.0)
        click('#info .rv[data-i="0"]')
        cap('An agent proposes: set the glass back 0.45 m', 'what moves and why, in 3D and in words')
        wait(3.6)
        click('#accept')
        cap('Accepted: version 2', '')
        wait(1.6)
        click('#info .rv[data-i="1"]')
        cap('A colleague changed the bays, on the old version', 'plain git would merge it silently; here it is a design conflict')
        wait(5.0)
        click('#reject')
        wait(0.6)
        cap('Carport instead of the terrace', 'added in green, removed in red, before anyone accepts it')
        click('#info .rv[data-i="2"]')
        wait(4.0)
        cap('')

        # the same, for BIM managers and CI
        # do not wait for the web fonts: on a slow link the 'load' event froze the recording for seconds
        pg.goto((ROOT / 'media' / 'git.html').as_uri(), wait_until='domcontentloaded')
        wait(1.0)
        js(OVERLAY)
        js("() => { document.getElementById('cap').style.left = '50%'; showMerge(); }")
        cap('The same engine in the terminal and in CI', 'pg diff, pg merge as git’s merge driver, a GitLab template')
        wait(4.5)
        cap('')
        card('Open source, local first', 'Agent skills · camera solver · studio · Rust core for models in git',
             'github.com/vibecading')
        wait(4.5)

        video = pg.video.path()
        ctx.close()
        b.close()
    shutil.move(video, OUT / 'studio_raw.webm')
    shutil.rmtree(vid, ignore_errors=True)
    print(OUT / 'studio_raw.webm')


if __name__ == '__main__':
    run()
