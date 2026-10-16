#!/usr/bin/env python3
"""Per-shop CSV of every answer: assistant, question, run, time, whether the shop was named, whether it was linked, links, answer text.
usage: export_csv.py <answers.json|answers.jsonl> [more files] --shop "Corica" --domain corica.be [--out file.csv]
Input rows have engine, prompt (or q + prompt), run, ts, answer, links (list of urls or {url}). A recount .json with recount.answers also works.
Rows with an error key are skipped. 'named' is a case-insensitive match of the shop name or its domain in the answer text or links."""
import argparse, csv, json, re, sys

def load(path):
    if path.endswith(".jsonl"):
        return [json.loads(l) for l in open(path) if l.strip()]
    d = json.load(open(path))
    return d["recount"]["answers"] if isinstance(d, dict) and "recount" in d else d

def urls(row):
    return [l if isinstance(l, str) else l.get("url", "") for l in row.get("links") or []]

def rows_for(answers, shop, domain, anonymise=False):
    name_re = re.compile(re.escape(shop), re.I)
    dom_re = re.compile(re.escape(domain), re.I)
    out = []
    for r in answers:
        if "error" in r or not r.get("answer"): continue
        u = urls(r)
        hide = (lambda t: dom_re.sub("[this shop]", name_re.sub("[this shop]", t))) if anonymise else (lambda t: t)
        out.append({
            "assistant": r.get("engine", ""),
            "question": r.get("prompt", ""),
            "run": r.get("run", r.get("id", "")),
            "asked_at": r.get("ts", ""),
            "shop_named": "yes" if name_re.search(r["answer"]) or dom_re.search(r["answer"]) or any(dom_re.search(x) for x in u) else "no",
            "shop_linked": "yes" if any(dom_re.search(x) for x in u) else "no",
            "links": hide(" | ".join(u)),
            "answer": hide(r["answer"]),
        })
    return out

def main(argv=None):
    ap = argparse.ArgumentParser()
    ap.add_argument("files", nargs="+")
    ap.add_argument("--shop", required=True)
    ap.add_argument("--domain", required=True)
    ap.add_argument("--out", default="-")
    ap.add_argument("--anonymise", action="store_true", help="replace the shop name and domain with [this shop] (public samples)")
    a = ap.parse_args(argv)
    rows = []
    for f in a.files: rows += rows_for(load(f), a.shop, a.domain, a.anonymise)
    f = sys.stdout if a.out == "-" else open(a.out, "w", newline="", encoding="utf-8")
    w = csv.DictWriter(f, fieldnames=["assistant", "question", "run", "asked_at", "shop_named", "shop_linked", "links", "answer"])
    w.writeheader(); w.writerows(rows)
    if f is not sys.stdout: f.close()
    return rows

if __name__ == "__main__":
    main()
