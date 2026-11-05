#!/usr/bin/env python3
"""Validate local links and core content in the public static site; no dependencies."""
from html.parser import HTMLParser
from pathlib import Path
from urllib.parse import unquote, urlsplit
import sys

SITE = (Path(__file__).resolve().parents[1] / "docs").resolve()
PAGES = ["index.html", "eight.html", "notice.html"]

class Links(HTMLParser):
    def __init__(self):
        super().__init__()
        self.links = []
        self.lang = None
        self.titles = 0
        self.ids = []
        self.viewport = False
        self.errors = []

    def handle_starttag(self, tag, attrs):
        attr = dict(attrs)
        if tag == "html":
            self.lang = attr.get("lang")
        if tag == "title":
            self.titles += 1
        if attr.get("id"):
            self.ids.append(attr["id"])
        if tag == "meta" and attr.get("name") == "viewport":
            self.viewport = "width=device-width" in attr.get("content", "")
        if tag == "a" and attr.get("target") == "_blank":
            if "noopener" not in attr.get("rel", "").split():
                self.errors.append("target=_blank requires rel=noopener")
        for key in ("href", "src"):
            if attr.get(key):
                self.links.append(attr[key])

def check():
    errors = []
    for name in PAGES:
        source = SITE / name
        if not source.is_file():
            errors.append(f"Missing page: {name}")
            continue
        data = source.read_text(encoding="utf-8")
        parser = Links()
        parser.feed(data)
        if parser.lang != "zh-CN" or parser.titles != 1:
            errors.append(f"{name}: expected lang=zh-CN and one <title>")
        if not parser.viewport:
            errors.append(f"{name}: missing viewport")
        errors.extend(f"{name}: {error}" for error in parser.errors)
        if len(parser.ids) != len(set(parser.ids)):
            errors.append(f"{name}: duplicate id")
        for link in parser.links:
            url = urlsplit(link)
            if url.scheme or url.netloc:
                if url.scheme != "https":
                    errors.append(f"{name}: expected HTTPS external link: {link}")
                continue
            if url.path.startswith("/"):
                errors.append(f"{name}: root-relative link breaks Pages subpath: {link}")
                continue
            target = (source.parent / unquote(url.path)).resolve() if url.path else source
            try:
                target.relative_to(SITE)
            except ValueError:
                errors.append(f"{name}: local link escapes docs/: {link}")
                continue
            if target.is_dir():
                target = target / "index.html"
            if not target.is_file():
                errors.append(f"{name}: broken relative link: {link}")
            elif url.fragment and target.suffix == ".html":
                target_parser = Links()
                target_parser.feed(target.read_text(encoding="utf-8"))
                if unquote(url.fragment) not in target_parser.ids:
                    errors.append(f"{name}: missing fragment: {link}")
    required = {"index.html": ("八仙神通馆", "传播专题"),
                "eight.html": ("温舟草", "智舟草", "灵舟草", "合舟草"),
                "notice.html": ("中文导读", "English overview", "67,177,185")}
    for name, phrases in required.items():
        p = SITE / name
        if p.exists():
            text = p.read_text(encoding="utf-8")
            for phrase in phrases:
                if phrase not in text:
                    errors.append(f"{name}: missing expected content: {phrase}")
    if errors:
        for e in errors:
            print("FAIL:", e, file=sys.stderr)
        return 1
    print("PASS: local files, fragments, HTTPS links, metadata and content in all 3 pages")
    return 0

if __name__ == "__main__":
    sys.exit(check())
