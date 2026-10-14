#!/usr/bin/env python3
"""Render public/check.html, public/fr/check.html, public/nl/check.html from tools/i18n.py."""
import hashlib, html, json, os, sys
sys.path.insert(0, os.path.dirname(__file__))
from i18n import S, COUNTRIES, NICHES, PRICE_URL
ROOT = os.path.join(os.path.dirname(__file__), "..", "public")
E = html.escape
def ver(name):
    return hashlib.sha256(open(os.path.join(ROOT, name), "rb").read()).hexdigest()[:8]

def opts(values, labels, sel=None):
    return "".join(f'<option value="{v}"{" selected" if v == sel else ""}>{E(labels[v])}</option>' for v in values)

def render(lang):
    t = S[lang]
    default_country = {"en": "IE", "fr": "FR", "nl": "BE"}[lang]
    alts = "".join(f'<link rel="alternate" hreflang="{l}" href="https://citedby.eu{S[l]["path"]}">' for l in S) + '<link rel="alternate" hreflang="x-default" href="https://citedby.eu/check">'
    data = json.dumps({"lang": lang, "price_url": PRICE_URL, "countries": t["countries"], "niches": t["niches"], "langs": t["langs"], "js": t["js"]}, ensure_ascii=False).replace("</", "<\\/")
    nav = {"en": ("Home", "/", "Prices", "/#prices"), "fr": ("Accueil", "/", "Tarifs", "/#prices"), "nl": ("Home", "/", "Prijzen", "/#prices")}[lang]
    switch = " · ".join(f'<a href="{S[l]["path"]}" hreflang="{l}" lang="{l}"{" aria-current=\"page\"" if l == lang else ""}>{l.upper()}</a>' for l in S)
    return f'''<!doctype html>
<html lang="{lang}"><head>
<meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<title>{E(t["title"])}</title>
<meta name="description" content="{E(t["desc"])}">
<link rel="canonical" href="https://citedby.eu{t["path"]}">{alts}
<meta property="og:title" content="{E(t["title"])}"><meta property="og:description" content="{E(t["desc"])}"><meta property="og:url" content="https://citedby.eu{t["path"]}"><meta property="og:type" content="website">
<meta name="theme-color" content="#0b0d10">
<link rel="icon" href="/favicon.svg" type="image/svg+xml">
<link rel="stylesheet" href="/style.css?v={ver("style.css")}">
</head><body>
<div class="w"><header class="top"><a class="logo" href="/">Cited<span>By</span></a><nav><a href="{nav[1]}">{nav[0]}</a><a href="{nav[3]}">{nav[2]}</a><span class="lsw">{switch}</span></nav></header>
<main class="chk">
<h1>{E(t["h1"])}</h1>
<p class="lede">{E(t["lede"])}</p>
<form id="cf" class="cform" novalidate>
<label class="full">{E(t["f_url"])}<input id="f-url" name="url" type="text" inputmode="url" autocomplete="url" autocapitalize="off" spellcheck="false" placeholder="{E(t["f_url_ph"])}" required></label>
<label>{E(t["f_country"])}<select id="f-country" name="country">{opts(COUNTRIES, t["countries"], default_country)}</select></label>
<label>{E(t["f_lang"])}<select id="f-lang" name="lang">{opts(["en", "fr", "nl"], t["langs"], lang)}</select></label>
<label>{E(t["f_niche"])}<select id="f-niche" name="niche">{opts(NICHES, t["niches"], "other")}</select></label>
<div class="act"><button class="btn p" id="f-go" type="submit">{E(t["go"])}</button></div>
</form>
<p class="note">{E(t["note"])} {E(t["more"])}</p>
<p id="status" class="status" role="status" aria-live="polite"></p>
<section id="result" class="res" hidden tabindex="-1"></section>
</main></div>
<footer><div class="w"><span>© 2026 CitedBy · <a href="mailto:hello@citedby.eu">hello@citedby.eu</a></span><span><a href="/legal">Legal notice</a> · <a href="/privacy">Privacy</a></span></div></footer>
<script type="application/json" id="i18n">{data}</script>
<script src="/check.js?v={ver("check.js")}"></script>
</body></html>
'''

for lang in S:
    path = os.path.join(ROOT, S[lang]["path"].lstrip("/") + ".html")
    os.makedirs(os.path.dirname(path), exist_ok=True)
    open(path, "w").write(render(lang))
    print("wrote", os.path.relpath(path))
