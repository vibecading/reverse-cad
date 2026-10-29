"""Screenshot a page with Playwright: python -I shot.py URL out.png [width] [js-to-run-first].
Set CHROMIUM to a browser executable if Playwright's own is not installed."""
import os
import sys
from playwright.sync_api import sync_playwright
url, out = sys.argv[1], sys.argv[2]
w = int(sys.argv[3]) if len(sys.argv) > 3 else 1500
with sync_playwright() as p:
    b = p.chromium.launch(executable_path=os.environ.get('CHROMIUM') or None, args=['--allow-file-access-from-files'])
    pg = b.new_page(viewport={'width': w, 'height': 950})
    logs = []
    pg.on('console', lambda m: logs.append(m.type + ': ' + m.text))
    pg.on('pageerror', lambda e: logs.append('pageerror: ' + str(e)))
    pg.goto(url)
    pg.wait_for_timeout(2500)
    if len(sys.argv) > 4:
        pg.evaluate(sys.argv[4])
        pg.wait_for_timeout(500)
    pg.screenshot(path=out, full_page=True)
    print('\n'.join(logs) or 'no console output')
    b.close()
