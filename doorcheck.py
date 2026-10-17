"""Step 1 of the CitedBy check: a plain-HTTP door check of one shop. Standard library only.
Returns machine-readable results (ids and statuses); the page turns them into plain-language fixes per language.
Method label shown to users: plain HTTP fetch, no JavaScript, no bot user-agent.
"""
import json, re, time, urllib.robotparser
from concurrent.futures import ThreadPoolExecutor
from urllib.parse import urljoin, urlsplit

import safefetch

BOTS = ["OAI-SearchBot", "GPTBot", "PerplexityBot", "Google-Extended", "Bingbot"]
ORG_TYPES = {"Organization", "LocalBusiness", "Store", "OnlineStore", "OnlineBusiness", "CafeOrCoffeeShop", "Corporation"}
PRODUCT_PATH = re.compile(r"/(products?|produits?|producten|shop/[^/]+)/[^/?#]+", re.I)


def normalize(raw):
    raw = (raw or "").strip()
    if not raw or len(raw) > 300 or re.search(r"\s", raw):
        raise safefetch.Blocked("url")
    if not re.match(r"(?i)^[a-z][a-z0-9+.-]*:", raw):
        raw = "https://" + raw
    u, _ = safefetch.parse(raw)  # scheme, port, userinfo
    return f"{u.scheme}://{u.netloc}"


def visible_text(html):
    html = re.sub(r"(?is)<(script|style|noscript|svg|template)[^>]*>.*?</\1>", " ", html)
    return re.sub(r"\s+", " ", re.sub(r"(?s)<[^>]+>", " ", html)).strip()


def jsonld_nodes(html):
    nodes = []
    def walk(x):
        if isinstance(x, list):
            for i in x: walk(i)
        elif isinstance(x, dict):
            nodes.append(x)
            for k in ("@graph", "mainEntity", "itemListElement", "item", "hasVariant"):
                if k in x: walk(x[k])
    for m in re.finditer(r'(?is)<script[^>]+type=["\']application/ld\+json["\'][^>]*>(.*?)</script>', html):
        try:
            walk(json.loads(m.group(1).strip()))
        except ValueError:
            pass
    return nodes


def types_of(node):
    t = node.get("@type", [])
    return {t} if isinstance(t, str) else {x for x in t if isinstance(x, str)}


def product_facts(html):
    """Return (has_product, price, availability, gtin) from Product JSON-LD on a page."""
    has = price = avail = gtin = False
    for n in jsonld_nodes(html):
        if types_of(n) & {"Product", "ProductGroup"}:
            has = True
            if any(n.get(k) for k in ("gtin", "gtin8", "gtin12", "gtin13", "gtin14", "isbn")):
                gtin = True
            offers = n.get("offers")
            for o in ([offers] if isinstance(offers, dict) else offers or []):
                if isinstance(o, dict):
                    for node in [o] + ([o["priceSpecification"]] if isinstance(o.get("priceSpecification"), dict) else []):
                        if node.get("price") not in (None, "") or node.get("lowPrice") not in (None, ""):
                            price = True
                    if o.get("availability"):
                        avail = True
                    if any(o.get(k) for k in ("gtin", "gtin8", "gtin12", "gtin13", "gtin14")):
                        gtin = True
    return has, price, avail, gtin


def find_product_url(root, home_html, fetch):
    host = urlsplit(root).netloc
    links = [urljoin(root + "/", h).split("?")[0] for h in re.findall(r'href=["\']([^"\'#]+)', home_html)]
    links = [l for l in links if urlsplit(l).netloc == host]
    for l in links:  # a product the shop itself links from its homepage is the best sample
        if re.search(r"/products?/[^/]+/?$", urlsplit(l).path, re.I):
            return l
    r = fetch(root + "/products.json?limit=1")
    if r["status"] == 200:
        try:
            return f"{root}/products/{json.loads(r['body'])['products'][0]['handle']}"
        except (ValueError, KeyError, IndexError, TypeError):
            pass
    return next((l for l in links if PRODUCT_PATH.search(urlsplit(l).path)), "")


def run(raw_url, lang="en", timeout=18):
    root = normalize(raw_url)
    deadline = time.monotonic() + timeout
    f = lambda url: safefetch.fetch(url, deadline=deadline, accept_lang=lang)
    with ThreadPoolExecutor(3) as ex:
        fr, fh, fl = ex.submit(f, root + "/robots.txt"), ex.submit(f, root + "/"), ex.submit(f, root + "/llms.txt")
        robots, home, llms = fr.result(), fh.result(), fl.result()
    out = {"site": root, "checks": [], "reachable": home["status"] == 200}
    add = lambda cid, status, **d: out["checks"].append({"id": cid, "status": status, **d})
    if home["status"] != 200:
        out["error"] = "refused" if home["status"] in (401, 403, 429, 503) else ("timeout" if home["error"] == "timeout" else "unreachable")
        out["home_status"] = home["status"]
        return out
    final_host = urlsplit(home["url"]).netloc
    if final_host != urlsplit(root).netloc:
        out["redirected_to"] = f"{urlsplit(home['url']).scheme}://{final_host}"
    # 1. AI crawlers in robots.txt
    rp = urllib.robotparser.RobotFileParser()
    rp.parse(robots["body"].splitlines() if robots["status"] == 200 else [])
    blocked = [b for b in BOTS if robots["status"] == 200 and not rp.can_fetch(b, root + "/")]
    add("crawlers", "fail" if blocked else "pass", blocked=blocked, checked=BOTS, robots_found=robots["status"] == 200)
    # 2. text in the raw HTML. A 200 with no readable text is a fetch we cannot judge (server answered us an empty body), never a verdict on the shop.
    words = len(visible_text(home["body"]).split())
    unreadable = words == 0
    add("raw_text", "unknown" if unreadable else "pass" if words >= 200 else "warn" if words >= 50 else "fail", words=words)
    # 3. Organization / Product JSON-LD on the homepage
    types = set().union(*[types_of(n) for n in jsonld_nodes(home["body"])]) if jsonld_nodes(home["body"]) else set()
    add("org_schema", "unknown" if unreadable else "pass" if types & ORG_TYPES else "fail", found=sorted(types)[:8])
    # 4. product page: Product JSON-LD, price, availability, GTIN
    purl = find_product_url(root, home["body"], f)
    if purl and time.monotonic() < deadline:
        page = f(purl)
        has, price, avail, gtin = product_facts(page["body"]) if page["status"] == 200 else (False,) * 4
        out["product_page"] = purl
        add("product_schema", "pass" if has else "fail")
        add("product_price", "pass" if price else "fail")
        add("product_availability", "pass" if avail else "fail")
        add("product_gtin", "pass" if gtin else "warn")
    else:
        add("product_schema", "na"); add("product_price", "na"); add("product_availability", "na"); add("product_gtin", "na")
    # 5. llms.txt: hygiene only
    ok = llms["status"] == 200 and len(llms["body"]) > 50 and "<html" not in llms["body"][:500].lower()
    add("llms_txt", "pass" if ok else "info")
    st = [c["status"] for c in out["checks"]]
    out["summary"] = {"pass": st.count("pass"), "fail": st.count("fail"), "warn": st.count("warn"), "na": st.count("na")}
    return out
