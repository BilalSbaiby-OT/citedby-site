#!/usr/bin/env python3
"""Build data/sample.json (the home page sample) from a recount file, and fail if any shown number or name is not in the raw answers.
usage: build_sample.py <real_recount_corica.json>
The three rows are chosen by question id; the competitor names are listed here and each is checked against the raw answer text per run.
A shop is one shop however it is written: name and domain are merged (Café du Jour = cafedujour.be)."""
import json, re, sys
from urllib.parse import urlparse

SHOP = re.compile(r"corica", re.I)
ROWS = {  # question id -> {display name: regex that matches the shop under any spelling or domain}
    "q1": {"Café du Jour": r"caf[eé]\s*du\s*jour|cafedujour", "Másalto": r"m[aá]salto", "Cafés Storme": r"storm[eé]"},
    "q4": {"JAVA Coffee": r"java\s*coffee|javacoffee", "Másalto": r"m[aá]salto", "Café du Jour": r"caf[eé]\s*du\s*jour|cafedujour"},
    "q8": {"Artisan du Café": r"artisan\s*du\s*caf[eé]|artisanducafe", "Arduina": r"arduina", "Torrefactory": r"torrefactory"},
}
TOP = {"Café du Jour": r"caf[eé]\s*du\s*jour|cafedujour", "Másalto": r"m[aá]salto"}

def blob(a): return a["answer"] + " " + json.dumps(a["links"])

def main(path, out="data/sample.json"):
    d = json.load(open(path))
    ans = [a for a in d["recount"]["answers"] if "error" not in a]
    assert len(ans) == 16 and {a["engine"] for a in ans} == {"claude"}, "expected 16 Claude answers"
    named = sum(bool(SHOP.search(blob(a))) for a in ans)
    linked = sum(any(SHOP.search(l if isinstance(l, str) else l.get("url", "")) for l in a["links"]) for a in ans)
    assert (named, linked) == (d["counts"]["claude"]["named"], d["counts"]["claude"]["linked"]), "counts differ from the recount file"
    rows = []
    for q, names in ROWS.items():
        qa = [a for a in ans if a["q"] == q]
        assert len(qa) == 2
        rows.append({
            "prompt": qa[0]["prompt"],
            "named": [{"name": n, "runs": sum(bool(re.search(rx, blob(a), re.I)) for a in qa)} for n, rx in names.items()],
            "shop_runs": sum(bool(SHOP.search(blob(a))) for a in qa),
        })
        assert all(x["runs"] >= 1 for x in rows[-1]["named"]), f"{q}: a listed name is not in the raw answers"
    def doms(a):
        out = []
        for l in a["links"]:
            h = urlparse(l if isinstance(l, str) else l.get("url", "")).netloc.lower().removeprefix("www.")
            if h and h not in out: out.append(h)
        return out
    allrows = []
    for q in sorted({a["q"] for a in ans}):
        qa = sorted((a for a in ans if a["q"] == q), key=lambda a: a["run"])
        allrows.append({"prompt": qa[0]["prompt"], "linked": [doms(a) for a in qa], "shop_named": sum(bool(SHOP.search(blob(a))) for a in qa)})
    assert not any(SHOP.search(d) for r in allrows for ds in r["linked"] for d in ds), "the shop's own domain is linked: sample would name it"
    top = {n: sum(bool(re.search(rx, blob(a), re.I)) for a in ans) for n, rx in TOP.items()}
    day = ans[0]["ts"][:10]
    assert all(a["ts"][:10] == day for a in ans)
    s = {"assistant": "Claude", "date": day, "answers": 16, "questions": 8, "named": named, "linked": linked,
         "top_competitor_answers": max(top.values()), "rows": rows, "all_rows": allrows, "source": "_evidence-res661/real_recount_corica.json"}
    json.dump(s, open(out, "w"), ensure_ascii=False, indent=1)
    print(json.dumps(s, ensure_ascii=False)[:600])

if __name__ == "__main__":
    main(sys.argv[1])
