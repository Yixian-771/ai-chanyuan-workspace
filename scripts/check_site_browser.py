#!/usr/bin/env python3
"""Check the three pages in clean Chromium contexts at the Pages subpath.

Requires Playwright only for acceptance checks, never for the website itself.
Without --base-url, serves docs/ locally at /ai-chanyuan-workspace/.
--base-url can check a published site using the same assertions.
"""
import argparse
import json
import os
from datetime import datetime, timezone
from functools import partial
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer
from importlib.metadata import version
from pathlib import Path
from threading import Thread
from urllib.parse import urljoin, urlsplit

from playwright.sync_api import sync_playwright

ROOT = Path(__file__).resolve().parents[1]
PREFIX = "/ai-chanyuan-workspace/"
PAGES = ("index.html", "eight.html", "notice.html")


class SiteHandler(SimpleHTTPRequestHandler):
    def do_GET(self):
        if not self.path.startswith(PREFIX):
            self.send_error(404)
            return
        self.path = "/" + self.path[len(PREFIX):]
        super().do_GET()

    def log_message(self, *_args):
        pass


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--base-url", help="Actual published URL, ending in /")
    parser.add_argument("--output-dir", default="work/site-check")
    parser.add_argument("--browser-executable", help="Optional installed Chromium path")
    parser.add_argument("--axe-path", help="Optional local axe.min.js, used by CI")
    args = parser.parse_args()
    output = Path(args.output_dir)
    output.mkdir(parents=True, exist_ok=True)
    server = None
    if args.base_url:
        base = args.base_url.rstrip("/") + "/"
    else:
        server = ThreadingHTTPServer(
            ("127.0.0.1", 0), partial(SiteHandler, directory=str(ROOT / "docs")))
        Thread(target=server.serve_forever, daemon=True).start()
        base = f"http://127.0.0.1:{server.server_port}{PREFIX}"
    report = {"checked_at_utc": datetime.now(timezone.utc).isoformat(),
              "base_url": base, "public_site": bool(args.base_url),
              "playwright": version("playwright"), "results": [], "errors": []}
    try:
        with sync_playwright() as p:
            launch = {"headless": True}
            if args.browser_executable:
                launch["executable_path"] = args.browser_executable
            if args.base_url and os.environ.get("HTTPS_PROXY"):
                launch["proxy"] = {"server": os.environ["HTTPS_PROXY"]}
            browser = p.chromium.launch(**launch)
            report["browser"] = browser.version
            for width in (375, 1366):
                # New contexts have no saved cookies, credentials or storage.
                context = browser.new_context(viewport={"width": width, "height": 900})
                page = context.new_page()
                request_errors = []
                page.on("requestfailed", lambda req: request_errors.append(
                    f"{req.url}: {req.failure}"))
                page.on("response", lambda res: request_errors.append(
                    f"{res.url}: HTTP {res.status}") if res.status >= 400 else None)
                page.on("pageerror", lambda error: request_errors.append(str(error)))
                homepage = page.goto(base, wait_until="networkidle")
                assert homepage and homepage.status == 200, "Homepage /: not HTTP 200"
                assert page.locator(".actions a[href='eight.html']").count() == 1
                for name in PAGES:
                    response = page.goto(urljoin(base, name), wait_until="networkidle")
                    assert response and response.status == 200, f"{name}: not HTTP 200"
                    assert not context.cookies(), f"{name}: unexpected cookies"
                    assert page.locator("main h1").count() == 1, f"{name}: expected one h1"
                    assert page.locator("nav[aria-label] a[aria-current=page]").count() == 1
                    assert page.locator("input, form, script[src]").count() == 0
                    dimensions = page.evaluate("""() => ({
                        scroll: document.documentElement.scrollWidth,
                        client: document.documentElement.clientWidth,
                        body: document.body.scrollWidth
                    })""")
                    assert dimensions["scroll"] <= dimensions["client"], dimensions
                    assert dimensions["body"] <= dimensions["client"], dimensions
                    page.keyboard.press("Tab")
                    assert page.locator(".skip").evaluate("el => el === document.activeElement")
                    page.keyboard.press("Enter")
                    assert page.locator("main").evaluate("el => el === document.activeElement")
                    # Exercise every relative anchor and the favicon/CSS over HTTP.
                    links = page.locator("a[href], link[href]").evaluate_all(
                        "els => els.map(el => el.href)")
                    same_origin = sorted({url.split("#")[0] for url in links
                                          if urlsplit(url).netloc == urlsplit(base).netloc})
                    for url in same_origin:
                        result = context.request.get(url)
                        assert result.status == 200, f"{url}: HTTP {result.status}"
                    if name == "index.html":
                        assert page.locator(".actions a[href='eight.html']").count() == 1
                        assert page.locator(".actions a[href='notice.html']").count() == 1
                    elif name == "eight.html":
                        assert page.get_by_text("作品待展示", exact=True).count() == 4
                        assert "不等于作品已上线" in page.locator("main").inner_text()
                    else:
                        assert page.locator("article[lang=en]").is_visible()
                        assert "不是通告全文译文" in page.locator("main").inner_text()
                        assert page.locator("a[href^='https://smcy.xyz/']").count() == 1
                    a11y = None
                    if args.axe_path:
                        page.add_script_tag(path=args.axe_path)
                        a11y = page.evaluate("""async () => {
                            const result = await axe.run(document, {runOnly: {
                                type: 'tag', values: ['wcag2a','wcag2aa','wcag21a','wcag21aa']
                            }});
                            return {version: axe.version, violations: result.violations.map(v => ({
                                id: v.id, targets: v.nodes.map(n => n.target)
                            }))};
                        }""")
                    page.screenshot(path=str(output / f"{Path(name).stem}-{width}.png"), full_page=True)
                    row = {"page": name, "viewport": width, "http_status": response.status,
                           "homepage_status": homepage.status,
                           "dimensions": dimensions, "local_resources": len(same_origin),
                           "keyboard_skip": "PASS", "axe": a11y,
                           "request_errors": request_errors.copy()}
                    report["results"].append(row)
                    assert not request_errors, request_errors
                    assert not a11y or not a11y["violations"], a11y
                # Follow each navigation item as a real browser link.
                for name in PAGES:
                    page.locator(f"nav .links a[href='{name}']").click()
                    page.wait_for_load_state("networkidle")
                    assert page.url.split("#")[0] == urljoin(base, name)
                assert not request_errors, request_errors
                context.close()
            browser.close()
    except Exception as error:
        report["errors"].append(str(error))
    finally:
        if server:
            server.shutdown()
        report["status"] = "FAIL" if report["errors"] else "PASS"
        (output / "results.json").write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n")
    print(f"{report['status']}: {len(report['results'])}/6 page/viewport checks; evidence: {output}")
    for error in report["errors"]:
        print(error)
    return bool(report["errors"])


if __name__ == "__main__":
    raise SystemExit(main())
