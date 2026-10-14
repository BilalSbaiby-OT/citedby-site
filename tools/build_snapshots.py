#!/usr/bin/env python3
"""Build data/snapshots.json from the raw cell answers (cells/*.jsonl), not from the prospect summaries.
A shop counts once per valid answer whose shop-link chips include its domain (aliases merged, non-shops dropped).
Valid answer = unique id, no error, non-empty text. The date is the newest answer timestamp.
usage: tools/build_snapshots.py ~/work/ventures/citedby/cells [--report]"""
import collections, json, os, sys
CELLS = {  # file -> (country, language, niche)
    "be-coffee-fr": ("BE", "fr", "coffee"), "be-coffee-nl": ("BE", "nl", "coffee"),
    "fr-coffee-fr": ("FR", "fr", "coffee"), "fr-tea-fr": ("FR", "fr", "tea"),
    "fr-beauty-fr": ("FR", "fr", "beauty"), "fr-mattress-fr": ("FR", "fr", "mattress"),
    "fr-supp-fr": ("FR", "fr", "supplements"), "ie-coffee-en": ("IE", "en", "coffee"),
}
ALIASES = {"caffeenation.be": "caffenation.be", "shop.bearmarket.ie": "bearmarket.ie"}
NOT_SHOPS = {"quechoisir.org", "laredoute.fr", "japan-food.jetro.go.jp", "mapbox.com", "wikipedia.org", "google.com", "youtube.com", "reddit.com", "lindfield.biz"}
NAMES = {  # as the shops spell themselves; a domain with no entry is shown as the domain
    "orcoffee.be": "OR Coffee Roasters", "mokcoffee.be": "MOK Specialty Coffee", "wideawake.coffee": "Wide Awake Coffee", "caffenation.be": "Caffenation",
    "andy-roasters.be": "Andy Roasters", "torrefactory.coffee": "Torrefactory", "way.gent": "WAY Coffee Roasters", "dewittezwaan.be": "De Witte Zwaan",
    "bellevillebrulerie.com": "Belleville Brûlerie", "coutumecafe.com": "Coutume", "terresdecafe.com": "Terres de Café",
    "palaisdesthes.com": "Palais des Thés", "dammann.fr": "Dammann Frères", "mariagefreres.com": "Mariage Frères", "kusmitea.com": "Kusmi Tea",
    "nutriandco.com": "Nutri&Co", "novoma.com": "Novoma", "aime.co": "Aime", "tediber.com": "Tediber", "emma.fr": "Emma", "kipli.com": "Kipli", "hypnia.fr": "Hypnia",
    "nutripure.fr": "Nutripure", "arkopharma.com": "Arkopharma", "dynveo.fr": "Dynveo",
    "cloudpickercoffee.ie": "Cloud Picker Coffee", "3fe.com": "3fe Coffee", "calendarcoffee.ie": "Calendar Coffee", "belllane.ie": "Bell Lane Coffee",
    "ponaire.ie": "Ponaire Coffee", "typo.ie": "Typo Coffee", "bearmarket.ie": "Bear Market",
    "lomi.coffee": "Lomi", "coffao.com": "Coffao", "greenwhey.com": "Greenwhey", "slome.fr": "Slome", "mello-matelas.fr": "Mello", "oenobiol.com": "Oenobiol", "rosscoffee.be": "ROSS Specialty Coffee Roastery",
}
MIN_ANSWERS, MAX_SHOPS = 3, 5
src = os.path.expanduser(sys.argv[1]); out = {}
for name, (cc, lang, niche) in CELLS.items():
    rows = {}
    for line in open(os.path.join(src, name + ".jsonl")):
        r = json.loads(line)
        if "error" not in r and r.get("answer"):
            rows[r["id"]] = r
    valid = list(rows.values())
    c = collections.Counter()
    for r in valid:
        ds = {ALIASES.get(d, d) for d in (x.lower().removeprefix("www.") for x in r.get("domains", []))}
        c.update(d for d in ds if d not in NOT_SHOPS)
    top = [{"name": NAMES.get(d, d), "host": d, "named": n} for d, n in sorted(c.items(), key=lambda kv: (-kv[1], NAMES.get(kv[0], kv[0]).lower())) if n >= MIN_ANSWERS][:MAX_SHOPS]
    prompts = {r["prompt"] for r in valid}
    out[f"{cc}|{lang}|{niche}"] = {"date": max(r["ts"] for r in valid)[:10], "runs": len(valid), "questions": len(prompts), "top": top}
    if "--report" in sys.argv:
        print(name, len(valid), "answers,", len(prompts), "questions,", out[f"{cc}|{lang}|{niche}"]["date"], [(t["name"], t["named"]) for t in top])
json.dump(out, open(os.path.join(os.path.dirname(__file__), "..", "data", "snapshots.json"), "w"), ensure_ascii=False, indent=1)
