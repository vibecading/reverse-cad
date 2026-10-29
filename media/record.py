"""Record the demo screencast: the page only, captions burned in.

usage: python -I media/record.py [out_dir]     (from the repo root)
Needs Playwright; set CHROMIUM to a browser executable if Playwright's own is
not installed. Writes out_dir/raw.webm; media/encode.sh makes the mp4 and gif.
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
    #cap{position:fixed;left:50%;bottom:42px;transform:translateX(-50%);max-width:1500px;z-index:99;
         background:rgba(16,24,32,.88);color:#fff;font:600 30px/1.3 "Golos Text",system-ui,sans-serif;
         padding:16px 28px;border-radius:8px;text-align:center;transition:opacity .35s}
    #cap small{display:block;font-weight:400;font-size:21px;color:#c9d3dc;margin-top:4px}
    #card{position:fixed;inset:0;z-index:100;background:#15202b;color:#fff;display:flex;flex-direction:column;
          justify-content:center;align-items:center;gap:18px;font-family:"Golos Text",system-ui,sans-serif;transition:opacity .5s}
    #card h1{font-size:64px;margin:0;font-weight:700;letter-spacing:-.01em}
    #card p{font-size:30px;margin:0;color:#c9d3dc;max-width:1300px;text-align:center;line-height:1.35}
    #card code{font-size:28px;color:#7fdbff}
    .rec-hl{outline:3px solid #ffd400;outline-offset:4px;border-radius:4px}`;
  document.head.appendChild(st);
  const c = document.createElement('div'); c.id = 'cap'; c.style.opacity = 0; document.body.appendChild(c);
})()
"""


def run():
    OUT.mkdir(parents=True, exist_ok=True)
    vid = OUT / 'video'
    shutil.rmtree(vid, ignore_errors=True)
    with sync_playwright() as p:
        b = p.chromium.launch(executable_path=os.environ.get('CHROMIUM') or None,
                              args=['--allow-file-access-from-files'])
        ctx = b.new_context(viewport={'width': W, 'height': H}, record_video_dir=str(vid),
                            record_video_size={'width': W, 'height': H})
        pg = ctx.new_page()

        def wait(s):
            pg.wait_for_timeout(int(s * 1000))

        def setup():
            pg.evaluate(OVERLAY)

        def cap(text, sub=''):
            pg.evaluate("([t, s]) => { const c = document.getElementById('cap'); c.innerHTML = t + (s ? '<small>' + s + '</small>' : ''); c.style.opacity = t ? 1 : 0; }", [text, sub])

        def card(title, sub='', code=''):
            pg.evaluate("""([t, s, c]) => { let d = document.getElementById('card');
                if (!d) { d = document.createElement('div'); d.id = 'card'; document.body.appendChild(d); }
                d.innerHTML = '<h1>' + t + '</h1>' + (s ? '<p>' + s + '</p>' : '') + (c ? '<code>' + c + '</code>' : '');
                d.style.opacity = 1; }""", [title, sub, code])

        def uncard():
            pg.evaluate("() => { const d = document.getElementById('card'); if (d) { d.style.opacity = 0; setTimeout(() => d.remove(), 500); } }")

        def case(i):
            pg.evaluate("i => document.querySelectorAll('.cases button')[i].click()", i)
            wait(1.2)

        def slide(name, frac, secs):
            """Move a parameter's slider smoothly from its value by frac of its range."""
            pg.evaluate("""async ([name, frac, ms]) => {
                const inp = document.querySelector('input[aria-label="' + name + '"]');
                const v0 = parseFloat(inp.value), lo = parseFloat(inp.min), hi = parseFloat(inp.max);
                const v1 = v0 + frac * (hi - lo) / 2, n = Math.max(2, Math.round(ms / 40));
                for (let i = 1; i <= n; i++) {
                  inp.value = v0 + (v1 - v0) * (0.5 - Math.cos(Math.PI * i / n) / 2);
                  inp.dispatchEvent(new Event('input')); await new Promise(r => setTimeout(r, 40));
                } }""", [name, frac, int(secs * 1000)])

        def hover(name, on=True):
            pg.evaluate("""([name, on]) => {
                const row = document.querySelector('input[aria-label="' + name + '"]').closest('.param');
                row.dispatchEvent(new MouseEvent(on ? 'mouseenter' : 'mouseleave'));
                row.classList.toggle('rec-hl', on); }""", [name, on])

        # the demo page, zoomed so the photo and the panel fit 1080 px
        pg.goto((ROOT / 'demo' / 'index.html').as_uri())
        pg.evaluate("() => { document.documentElement.style.zoom = '0.8'; window.dispatchEvent(new Event('resize')); }")
        wait(1.5)
        setup()

        card('A building, back from its photos',
             'Recover the camera and a parametric model from ordinary photos,<br>and prove it against measured drawings')
        wait(4.5)
        uncard()
        cap('One photo of Farnsworth House', 'camera and parametric model solved together; scale from one published bay')
        wait(4.5)
        cap('Move a parameter: the model leaves the photo', 'the error over the marks grows from 2 px')
        slide('W', 0.9, 2.5)
        wait(1.2)
        slide('c', -0.9, 2.0)
        wait(1.2)
        pg.click('#reset')
        cap('Reset: back on the photo', '')
        wait(2.0)
        hover('zf_t')
        cap('Each parameter knows which marks measure it', 'the dependency graph, built from the marks')
        wait(3.5)
        hover('zf_t', False)
        cap('Checked against the HABS measured drawings: 0.1–2.9 % off', 'length, width, floor and roof heights')
        pg.evaluate("() => document.getElementById('truth').scrollIntoView({block: 'center'})")
        wait(4.0)
        pg.evaluate("() => document.querySelector('aside').scrollTo(0, 0)")

        cap('Crown Hall, one public-domain photo', 'column bay −1.0 %, girder −2.6 %, ceiling +0.1 % against published figures')
        case(1)
        wait(4.5)

        cap('Robie House, one iPhone photo: fits to 2.5 px…', '…and every internal check is quiet')
        case(2)
        wait(3.5)
        cap('…yet it is 11–18 % off the drawings', 'green dashed: the HABS drawings, seen through the same camera')
        wait(4.5)

        cap('Two photos, solved together: within 1 %', 'coping 2.559 m vs 2.56 · wall 4.05 m vs 4.01')
        case(3)
        wait(5.0)
        cap('')

        # the model as text
        pg.goto((ROOT / 'media' / 'git.html').as_uri())
        wait(1.0)
        setup()
        cap('The model is text, so a change is a diff', 'which parameter moved which element, and which checks broke')
        wait(5.5)
        pg.evaluate('showMerge()')
        cap('Two branches edit different lines. Plain git merges silently.',
            'pg as git’s merge driver stops: the glass wall depends on both edits')
        wait(6.5)
        cap('')
        card('Open source, local first', 'Agent skills · camera solver · Rust core for models in git',
             'github.com/vibecading')
        wait(4.5)

        video = pg.video.path()
        ctx.close()
        b.close()
    shutil.move(video, OUT / 'raw.webm')
    shutil.rmtree(vid, ignore_errors=True)
    print(OUT / 'raw.webm')


if __name__ == '__main__':
    run()
