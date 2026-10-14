#!/usr/bin/env python3
"""Rewrite ?v=<hash> on style.css, data.css and check.css links in every static page, so a CSS change busts the 7-day cache."""
import glob, hashlib, os, re
ROOT = os.path.join(os.path.dirname(__file__), "..", "public")
def ver(name):
    return hashlib.sha256(open(os.path.join(ROOT, name), "rb").read()).hexdigest()[:8]
V = {n: ver(n) for n in ("style.css", "data.css", "check.css")}
for f in glob.glob(os.path.join(ROOT, "**", "*.html"), recursive=True):
    t = open(f).read(); o = t
    for n, v in V.items():
        t = re.sub(r'href="/%s(\?v=[0-9a-f]+)?"' % re.escape(n), f'href="/{n}?v={v}"', t)
    if t != o:
        open(f, "w").write(t)
