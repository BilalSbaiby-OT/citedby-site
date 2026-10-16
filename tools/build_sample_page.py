#!/usr/bin/env python3
"""Render public/sample-audit.html from data/sample.json (built by tools/build_sample.py from the raw answers). Every number is in the CSV beside it."""
import html, json, os
E = html.escape
ROOT = os.path.join(os.path.dirname(__file__), "..")
s = json.load(open(os.path.join(ROOT, "data", "sample.json")))
day = "15 Oct 2026"
rows = "".join(
    f'<tr><td>{E(r["prompt"])}</td><td data-label="Sites linked, try 1">{E(", ".join(r["linked"][0]) or "none")}</td>'
    f'<td data-label="Sites linked, try 2">{E(", ".join(r["linked"][1]) or "none")}</td><td data-label="This shop">named {r["shop_named"]} of 2, linked 0 of 2</td></tr>'
    for r in s["all_rows"])
page = f'''<!doctype html>
<html lang="en"><head>
<meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<title>Sample audit: a Belgian coffee roaster named in {s["named"]} of {s["answers"]} AI assistant answers | CitedBy</title>
<meta name="description" content="A full CitedBy audit sample with the shop anonymised: {s["questions"]} buyer questions, each asked twice, every site the assistant linked, and the raw answers as a CSV.">
<link rel="canonical" href="https://citedby.eu/sample-audit">
<meta property="og:title" content="Sample audit: named in {s["named"]} of {s["answers"]} AI assistant answers"><meta property="og:description" content="{s["questions"]} buyer questions, each asked twice, every linked site, raw answers in a CSV. Shop anonymised."><meta property="og:url" content="https://citedby.eu/sample-audit"><meta property="og:type" content="article">
<meta name="theme-color" content="#0F1B2D">
<link rel="icon" href="/favicon.svg" type="image/svg+xml">
<link rel="preload" href="/fonts/newsreader-latin-600-normal.woff2" as="font" type="font/woff2" crossorigin>
<link rel="stylesheet" href="/style.css?v=0"><link rel="stylesheet" href="/data.css?v=0">
</head><body class="dp">
<header class="top"><a class="logo" href="/" aria-label="CitedBy home">CitedBy<i aria-hidden="true">1</i></a><nav aria-label="Main"><a class="k" href="/data">Data</a><a class="k" href="/check">Free check</a></nav></header>
<main class="doc wide">
<p class="crumb"><a href="/">CitedBy</a> / Sample audit</p>
<p class="dateline">Sample audit. Shop anonymised, answers real. Run {day}.</p>
<h1>A Belgian online coffee roaster, named in {s["named"]} of {s["answers"]} answers</h1>
<p class="ans">We asked {s["assistant"]} {s["questions"]} questions a buyer would ask, in French, each twice. Every answer is kept. The shop was named in {s["named"]} of them and linked in {s["linked"]}. The most-named competitor shop appeared in {s["top_competitor_answers"]} of {s["answers"]}.</p>
<p class="src">API with web search, {day}. Answers vary between runs. The sites below are the ones the assistant linked, not our opinion. This shows the report format; yours covers your own shop and your own market. <a href="/sample-audit.csv">All {s["answers"]} answers as a CSV</a>, with links and times, shop name removed.</p>

<section><h2>1. Sites {E(s["assistant"])} linked, question by question</h2>
<div class="tw"><table><thead><tr><th scope="col">A buyer asks</th><th scope="col">Sites linked, try 1</th><th scope="col">Sites linked, try 2</th><th scope="col">This shop</th></tr></thead><tbody>
{rows}
</tbody></table></div>
<p class="src">Counting rule: a shop counts as named when its name or its domain appears in the answer text or in the links. One shop is one shop however it is written: "Café du Jour" and fr.cafedujour.be count together. "Named in 1 of 2" is never rounded up to "recommended".</p></section>

<section><h2>2. What the Fix Pack report adds</h2>
<ul><li>40 buyer questions, each asked twice, instead of 8.</li><li>The same count on every assistant we can measure that day, each with its own number.</li><li>A competitor map: who is named, who is linked, which pages were cited.</li><li>The changes made on your shop, or as ready-to-paste files.</li><li>The day-30 recount, before and after, with the raw answers.</li></ul>
<p class="src">Every audit also checks the technical basics on your homepage: whether robots.txt lets AI search crawlers in, whether product text is in the raw HTML, and whether the page says who you are. We check them because a failure would block everything else, not because passing them gets you named.</p></section>

<section class="cta"><h2>See your own shop in this table</h2><p class="lede">The free check takes about 10 seconds and needs no email. The full mini-audit follows by email within 2 working days.</p><div class="actions"><a class="btn p" href="/check">Check my shop, free</a></div></section>
</main>
<footer><span>© 2026 CitedBy. hello@citedby.eu</span><span><a href="/data">Data</a> &nbsp; <a href="/terms">Terms</a> &nbsp; <a href="/refund">Refunds</a> &nbsp; <a href="/contact">Contact</a> &nbsp; <a href="/legal">Legal notice</a> &nbsp; <a href="/privacy">Privacy</a></span></footer>
</body></html>
'''
open(os.path.join(ROOT, "public", "sample-audit.html"), "w").write(page)
print("wrote public/sample-audit.html")
