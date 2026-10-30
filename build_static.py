#!/usr/bin/env python3
"""Build the three hand-authored public pages (privacy, list-your-truck, 404) from pages_src/static_pages.json.

WHY: these pages had no builder, so their nav, footer and social tags drifted from the rest of the site (the 404
still linked to an old /whereeatin-site/ path). The JSON keeps only each page's own content - title, description,
its own styles and main body. The shared chrome (canonical, og/twitter cards, nav, footer) comes from site_base,
so every page gets the same block.

Usage: python build_static.py [--check]
"""
from __future__ import annotations

import html as H
import json
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import site_base  # noqa: E402

SRC = os.path.join(HERE, "pages_src", "static_pages.json")


def render(p: dict) -> str:
    canon = site_base.url(p["path"])
    robots = '<meta name="robots" content="noindex">' if p.get("noindex") else ""
    title = H.escape(p["title"], quote=True)
    desc = H.escape(p["description"], quote=True)
    return f"""<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>{title}</title>
<meta name="description" content="{desc}">
<link rel="canonical" href="{canon}">
{robots}
<meta name="theme-color" content="#d81f26">
<link rel="icon" href="/assets/favicon.svg" type="image/svg+xml">
{site_base.og_block(p["title"], p["description"], p["path"])}
{p["head_extra"]}
<style>{site_base.NAV_CSS}</style>
</head>
<body>
{site_base.nav_block("/" + p["path"] if p["path"].endswith("/") else "")}
<main>{p["main"]}</main>
{site_base.footer_block()}
<script>{site_base.NAV_JS}</script>
</body>
</html>
"""


def targets(pages: dict):
    for key, p in pages.items():
        out = p["path"] if p["path"].endswith(".html") else p["path"] + "index.html"
        yield os.path.join(HERE, out), render(p)


def main() -> int:
    pages = json.load(open(SRC, encoding="utf-8"))
    check = "--check" in sys.argv
    stale = 0
    for path, page in targets(pages):
        cur = open(path, encoding="utf-8").read() if os.path.isfile(path) else ""
        if site_base.same(page, cur):
            continue
        if check:
            stale += 1
            print("  STALE", os.path.relpath(path, HERE))
            continue
        os.makedirs(os.path.dirname(path), exist_ok=True)
        with open(path, "w", encoding="utf-8", newline="\n") as fh:
            fh.write(page)
        print("  wrote", os.path.relpath(path, HERE))
    if check:
        print("STALE" if stale else "CURRENT", f"- {stale} page(s) would change")
        return 1 if stale else 0
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
