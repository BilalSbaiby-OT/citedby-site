#!/usr/bin/env python3
"""Build data/snapshots.json from the CitedBy cell summaries (real logged-out ChatGPT answers).
usage: tools/build_snapshots.py ~/work/ventures/citedby/cells"""
import json, os, sys, time
CELLS = {  # file -> (country, language, niche)
    "be-coffee-fr": ("BE", "fr", "coffee"), "be-coffee-nl": ("BE", "nl", "coffee"),
    "fr-coffee-fr": ("FR", "fr", "coffee"), "fr-tea-fr": ("FR", "fr", "tea"),
    "fr-beauty-fr": ("FR", "fr", "beauty"), "fr-mattress-fr": ("FR", "fr", "mattress"),
    "fr-supp-fr": ("FR", "fr", "supplements"), "ie-coffee-en": ("IE", "en", "coffee"),
}
src = os.path.expanduser(sys.argv[1]); out = {}
for name, (cc, lang, niche) in CELLS.items():
    p = os.path.join(src, name + ".summary.json")
    d = json.load(open(p))
    shops = sorted(d["shops"], key=lambda s: -s["named"])[:5]
    out[f"{cc}|{lang}|{niche}"] = {
        "date": time.strftime("%Y-%m-%d", time.gmtime(os.path.getmtime(p))), "runs": d["runs"], "questions": len(d["prompts"]),
        "top": [{"name": s["name"], "host": s["host"], "named": s["named"]} for s in shops if s["named"] >= 2]}
json.dump(out, open(os.path.join(os.path.dirname(__file__), "..", "data", "snapshots.json"), "w"), ensure_ascii=False, indent=1)
print({k: [(s["name"], s["named"]) for s in v["top"]][:3] for k, v in out.items()})
