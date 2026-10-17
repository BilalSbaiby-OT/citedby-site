"""CitedBy home page (EN, FR), rendered per request from engines.json. Standard library only.
Copy: company-memory products/citedby/OFFER-V3-COPY.md (RES-867). The assistant list is data: only an engine whose
last web-grounded test succeeded in the last 24 hours is named anywhere on the page (hero line, sample, Fix Pack card,
FAQ, JSON-LD, meta). An empty list renders the fallback of OFFER-V3.md 3.2 and swaps the buy button for the free check."""
import datetime, html, json, os

E = html.escape
FIX_URL = "https://buy.stripe.com/3cI8wHgJK4q9atr9Y98N200"
MAX_AGE = datetime.timedelta(hours=24)
MONTHS_FR = ["janv.", "févr.", "mars", "avr.", "mai", "juin", "juil.", "août", "sept.", "oct.", "nov.", "déc."]
MONTHS_EN = ["Jan", "Feb", "Mar", "Apr", "May", "Jun", "Jul", "Aug", "Sep", "Oct", "Nov", "Dec"]
HERE = os.path.dirname(os.path.abspath(__file__))
SAMPLE = json.load(open(os.path.join(HERE, "data", "sample.json")))


def parse_ts(s):
    d = datetime.datetime.fromisoformat(s.replace("Z", "+00:00"))
    return d if d.tzinfo else d.replace(tzinfo=datetime.timezone.utc)


def live_engines(path, now=None):
    """Engines whose last successful web-grounded test is under 24 hours old. Bad or missing file: none."""
    now = now or datetime.datetime.now(datetime.timezone.utc)
    try:
        rows = json.load(open(path))["engines"]
    except (OSError, ValueError, KeyError, TypeError):
        return []
    out = []
    for r in rows:
        try:
            if r.get("group", "web") != "web":  # knowledge-only rows (no web search) never join the "web search on" line
                continue
            t = parse_ts(r["tested"])
            if r["name"] and datetime.timedelta(0) <= now - t < MAX_AGE:
                out.append({"name": str(r["name"]), "route": str(r.get("route", "")), "tested": t})
        except (KeyError, ValueError, TypeError, AttributeError):
            continue
    return out


def fmt_date(d, lang):
    return f"{d.day} {MONTHS_FR[d.month - 1]} {d.year}" if lang == "fr" else f"{d.day} {MONTHS_EN[d.month - 1]} {d.year}"


def join_names(names, lang):
    if len(names) <= 1: return "".join(names)
    return ", ".join(names[:-1]) + (" et " if lang == "fr" else " and ") + names[-1]


T = {
 "en": dict(
  path="/", other="/fr", skip="Skip to content", home="CitedBy home", nav=("Free check", "Sample audit", "Prices", "FAQ"),
  title="CitedBy: who do AI assistants name instead of your shop?",
  desc="We ask AI assistants your buyers' questions, count who gets named, fix your pages and count again at day 30. Free check, then a Fix Pack at €390, paid once.",
  ogt="Who do AI assistants name instead of your shop?", ogd="Free check of your shop. Fix Pack €390 paid once, with a recount at day 30.",
  eyebrow="AI assistant visibility for online shops",
  h1="Is an AI assistant sending your customers to a competitor?",
  lede="We ask AI assistants the questions your buyers ask, in their language, and count who gets named. Then we fix what keeps your shop out of the answers and count again 30 days later.",
  engines="Assistants we measured on {date}: {names}. Each one through an API, with web search on.",
  engines_none="We are connecting assistants. Write to us before you buy.",
  go="Check my shop, free", go_scan="Scan my site, free", go_quick="Or run the 10-second crawler check first", sample_link="Read a sample mini-audit",
  micro="Nine AI assistants, about a minute, no email, no card.",
  s_bar="A Belgian coffee roaster's online shop", s_big="Named in {n} of {a} answers. Linked in {l}.",
  s_sub="{assistant} answered {q} buyer questions in French, each asked twice. The roaster was named once and its website was never linked.",
  s_h="Who the assistant names instead of you", s_q="A buyer asks (in French)", s_n="Named instead", s_t="This shop",
  s_of="{n} of 2", s_run="{n} of 2 answers", s_note="API with web search, each question asked twice, {date}. Answers vary between runs. Competitor names are the assistant's own output. Every count in your audit comes with the raw answers.",
  s_more="Read the full sample", s_src="Method",
  how_h="What the Fix Pack does, in order",
  steps=[("40 buyer questions in your market", "We write the questions your buyers type, in up to 2 languages: where to buy, which shop or maker is best, subscriptions, gifts, your city, values such as organic, and the specific need your product meets."),
         ("Every assistant we can measure, each question twice", "That makes 80 answers per assistant. Each answer is saved with its links and the time we asked."),
         ("Who is named instead of you", "A competitor map for each assistant: who is named, who is linked, and which pages the assistant cited."),
         ("The fixes", "We make the changes on your shop, or send them as ready-to-paste files. Crawlers can reach your pages and read your product text. Price, delivery, returns and origin are stated on your own pages. Wrong facts the assistants repeat are corrected. An FAQ answers your buyers' exact questions. Product data and schema come last, as housekeeping."),
         ("Three listing requests", "We write to the guides and lists the assistants cite most in your category. We cannot promise that any of them says yes."),
         ("The recount at day 30", "The same questions, the same assistants, twice each, counted the same way. You get before and after for each assistant, with the raw answers.")],
  how_close="Each assistant has its own count. We never blend them into a score.",
  pr_h="Prices", pr_sub="Start with a free check of your shop. If you want the changes made for you, that is the Fix Pack.",
  fp_price="€390", fp_small="paid once",
  fp=["An audit of every assistant we can measure today: 40 buyer questions in your market, each asked twice, in up to 2 languages", "A competitor map per assistant: who is named instead of you, and the pages it cited",
      "The changes made on your shop within 7 days of access, or each one as a ready-to-paste file", "3 listing requests to the guides your buyers' assistants read",
      "The day-30 recount, before and after per assistant, with every raw answer as a CSV you keep"],
  anchor="For comparison: a GEO audit report starts at €595 at a Belgian agency, and a tracker that re-runs 100 questions costs $189 a month. Neither includes the changes made on your pages. List prices read on 13 Oct 2026; scopes differ.",
  buy="Buy the Fix Pack, €390",
  g_btn="Changes live in 7 days or the €390 is refunded. You do not have to ask.",
  cap="We take 5 Fix Packs a month. If this month is full, we email you your start date before any work begins, and refund in full if you prefer.",
  fc_h="Free check", fc=["16 answers about your category, in your language", "Who is named instead of you", "What the assistants say about you by name", "2 to 3 fixes, checked against your site"],
  mo_h="After your first 30 days: CitedBy Monthly", mo_price="€149", mo_small="/month",
  mo=["Your buyer questions re-run every month on every assistant we measure", "Who gained and who lost, competitor by competitor", "Alerts when an assistant gets a fact about you wrong",
      "2 changes made for you every month, plus 1 listing request", "A one-page report in your language"],
  mo_note="Month 1 is included in your Fix Pack. We send the link with your day-30 recount. Cancel anytime by replying to any report.",
  faq_h="FAQ",
  faq=[("Which assistants do you check?", "The ones we can ask through an API with web search switched on, on the day you order. The line at the top of this page is that list, with its date. We do not script the chat apps themselves: their consumer terms forbid automated extraction, and we will not build your results on an account that can be banned. When we add an assistant, it joins your recount at no charge."),
       ("Is an API answer what my buyer sees in the app?", "Not always. An API call has no chat history and no personal profile, and the app can answer differently. That is why we ask every question twice, show you each answer and count the same way before and after. The count shows change. It does not forecast your traffic."),
       ("Can you guarantee an assistant will recommend us?", "No. Nobody controls what an assistant answers. We guarantee the work: changes live (or files delivered) within 7 days, and if your count does not rise at the day-30 recount, we keep working another 30 days at no charge."),
       ("Do you need access to my shop?", "For the Fix Pack, yes: a Shopify collaborator request or a CMS login, so we can make the changes. If you prefer, we send every change as ready-to-paste files and you apply them."),
       ("Why not just use a tracking tool?", "Trackers tell you whether you show up. They do not rewrite your pages, fix wrong facts or ask the guides the assistants read to list you. That work is what you pay us for."),
       ("Which languages?", "Up to 2 of English, French, Dutch, German, Spanish, Italian and Portuguese."),
       ("How fast?", "The mini-audit arrives within 2 working days. Fix Pack changes go live within 7 days of access, or the files reach you within 7 days, and the recount is at day 30."),
       ("What exactly do you guarantee?", 'Late changes, full refund. If you give us access (a Shopify collaborator request or a CMS login), the changes are live within 7 days. If you choose ready-to-paste files, you get them within 7 days. If we miss either date, we refund the €390. You do not have to ask. No rise at day 30, 30 more days free. We ask the same questions again, each twice, and count the same way as in your first audit. If your shop is named in no more answers than before, we keep working another 30 days at no charge. We do not promise rankings, traffic or sales. Nobody controls what an assistant answers.'),
       ("What happens after I pay?", 'Stripe emails your receipt. We email you for access, or for your choice of ready-to-paste files. The 7 days start the day you give us access, or the day you tell us you want the files. If we miss the date, the refund is automatic. At day 30 you get the recount, before and after for each assistant, with the raw answers. Nothing renews. After the recount you can keep going with CitedBy Monthly (€149 a month, cancel by replying to any report). If you do nothing, you are not charged again.'),
       ("Is Monthly a contract?", "No. You choose it after your day-30 recount, it is billed monthly, and you cancel by replying to any report. Your Fix Pack never turns into Monthly by itself.")],
  faq_multi=("Why several assistants?", "A shop can be named by one assistant and missed by another, so each gets its own count. Your day-30 recount shows which one you moved on."),
  behind_h="Who is behind this",
  behind="CitedBy is a small independent service run from Spain. We sell the fixes, which is why every audit lists the sites each assistant linked in each try: you can check our count yourself.",
  legal="Legal notice", cta_h="See where you stand, free", cta="Send your shop address and get 16 answers about your category, who is named instead of you, and 2 to 3 fixes.",
  foot=(("/data", "Data"), ("/terms", "Terms"), ("/refund", "Refunds"), ("/contact", "Contact"), ("/legal", "Legal notice"), ("/privacy", "Privacy")),
  svc="CitedBy: AI assistant visibility audit and fixes", svc_type="AI search visibility for online shops", free_offer="Free check", fp_offer="Fix Pack (paid once)", locale="en",
 ),
 "fr": dict(
  path="/fr", other="/", skip="Aller au contenu", home="Accueil CitedBy", nav=("Test gratuit", "Exemple d'audit", "Tarifs", "FAQ"),
  title="CitedBy : qui les IA citent-elles à votre place ?",
  desc="Nous posons aux assistants IA les questions de vos acheteurs, comptons qui est cité, corrigeons vos pages. Test gratuit, puis Fix Pack à 390 €, payé une fois.",
  ogt="Qui les assistants IA citent-ils à la place de votre boutique ?", ogd="Test gratuit de votre boutique. Fix Pack à 390 € payé une fois, avec un recomptage à 30 jours.",
  eyebrow="Visibilité dans les assistants IA pour boutiques en ligne",
  h1="Un assistant IA envoie-t-il vos clients chez un concurrent ?",
  lede="Nous posons aux assistants IA les questions de vos acheteurs, dans leur langue, et nous comptons qui est cité. Puis nous corrigeons ce qui vous écarte des réponses et nous recomptons 30 jours plus tard.",
  engines="Assistants mesurés le {date} : {names}. Chacun par une API, recherche web activée.",
  engines_none="Nous connectons des assistants. Écrivez-nous avant d'acheter.",
  go="Tester ma boutique, gratuitement", sample_link="Lire un exemple de mini-audit",
  micro="Le test prend environ 10 secondes, sans e-mail. Vous voulez le mini-audit de 16 réponses ? Laissez votre e-mail après le test ; il arrive sous 2 jours ouvrés.",
  s_bar="La boutique en ligne d'un torréfacteur belge", s_big="Cité dans {n} réponse sur {a}. Lien vers son site dans {l}.",
  s_sub="{assistant} a répondu à {q} questions d'acheteurs en français, chacune posée deux fois. Le torréfacteur a été cité une fois et son site n'a jamais été lié.",
  s_h="Qui l'assistant cite à votre place", s_q="Un acheteur demande (en français)", s_n="Cités à sa place", s_t="Cette boutique",
  s_of="{n} sur 2", s_run="{n} réponses sur 2", s_note="API avec recherche web, chaque question posée deux fois, {date}. Les réponses varient d'un essai à l'autre. Les noms de concurrents viennent de l'assistant lui-même. Chaque chiffre de votre audit est livré avec les réponses brutes.",
  s_more="Lire l'exemple complet", s_src="Méthode",
  how_h="Ce que fait le Fix Pack, dans l'ordre",
  steps=[("40 questions d'acheteurs sur votre marché", "Nous écrivons les questions que vos acheteurs tapent, dans 2 langues au plus : où acheter, quelle boutique ou quel artisan choisir, abonnements, cadeaux, votre ville, valeurs comme le bio, et le besoin précis que votre produit couvre."),
         ("Chaque assistant que nous savons mesurer, chaque question deux fois", "Cela fait 80 réponses par assistant. Chaque réponse est enregistrée avec ses liens et l'heure de la question."),
         ("Qui est cité à votre place", "Une carte des concurrents par assistant : qui est cité, qui est lié, et quelles pages l'assistant a utilisées."),
         ("Les corrections", "Nous faisons les changements sur votre boutique, ou nous vous les envoyons prêts à coller. Les robots accèdent à vos pages et lisent vos fiches produit. Prix, livraison, retours et origine sont écrits sur vos propres pages. Les faits erronés que les assistants répètent sont corrigés. Une FAQ répond aux questions exactes de vos acheteurs. Les données produit et le balisage viennent en dernier, comme entretien."),
         ("Trois demandes de référencement", "Nous écrivons aux guides et aux listes que les assistants citent le plus dans votre catégorie. Nous ne pouvons pas promettre qu'un seul accepte."),
         ("Le recomptage à 30 jours", "Mêmes questions, mêmes assistants, deux fois chacune, comptées de la même façon. Vous recevez l'avant et l'après pour chaque assistant, avec les réponses brutes.")],
  how_close="Chaque assistant a son propre compte. Nous ne les fondons jamais en une note.",
  pr_h="Tarifs", pr_sub="Commencez par un test gratuit de votre boutique. Si vous voulez que nous fassions les changements, c'est le Fix Pack.",
  fp_price="390 €", fp_small="payé une fois",
  fp=["Un audit de chaque assistant que nous savons mesurer aujourd'hui : 40 questions d'acheteurs sur votre marché, chacune posée deux fois, dans 2 langues au plus", "Une carte des concurrents par assistant : qui est cité à votre place, et les pages qu'il a utilisées",
      "Les changements faits sur votre boutique sous 7 jours après l'accès, ou chacun en fichier prêt à coller", "3 demandes de référencement aux guides que les assistants de vos acheteurs lisent",
      "Le recomptage à 30 jours, avant et après par assistant, avec chaque réponse brute en fichier CSV que vous gardez"],
  anchor="À titre de comparaison : un audit GEO commence à 595 € chez une agence belge, et un outil qui relance 100 questions coûte 189 $ par mois. Ni l'un ni l'autre n'inclut les changements faits sur vos pages. Prix catalogue relevés le 13 oct. 2026 ; les périmètres diffèrent.",
  buy="Acheter le Fix Pack, 390 €",
  g_btn="Changements en ligne sous 7 jours, sinon les 390 € vous sont remboursés. Sans rien demander.",
  cap="Nous prenons 5 Fix Packs par mois. Si le mois est complet, nous vous écrivons votre date de début avant tout travail, et nous remboursons en totalité si vous préférez.",
  fc_h="Test gratuit", fc=["16 réponses sur votre catégorie, dans votre langue", "Qui est cité à votre place", "Ce que les assistants disent de vous quand on les interroge par votre nom", "2 à 3 corrections, vérifiées sur votre site"],
  mo_h="Après vos 30 premiers jours : CitedBy Monthly", mo_price="149 €", mo_small="/mois",
  mo=["Les questions de vos acheteurs relancées chaque mois sur chaque assistant que nous mesurons", "Qui gagne et qui perd, concurrent par concurrent", "Des alertes quand un assistant se trompe sur un fait vous concernant",
      "2 changements faits pour vous chaque mois, plus 1 demande de référencement", "Un rapport d'une page dans votre langue"],
  mo_note="Le mois 1 est inclus dans votre Fix Pack. Nous envoyons le lien avec votre recomptage à 30 jours. Résiliation à tout moment en répondant à un rapport.",
  faq_h="FAQ",
  faq=[("Quels assistants vérifiez-vous ?", "Ceux que nous pouvons interroger par une API, recherche web activée, le jour de votre commande. La ligne en haut de cette page est cette liste, avec sa date. Nous ne pilotons pas les applications de chat elles-mêmes : leurs conditions grand public interdisent l'extraction automatisée, et nous ne bâtirons pas vos résultats sur un compte qui peut être banni. Quand nous ajoutons un assistant, il rejoint votre recomptage sans frais."),
       ("Une réponse d'API est-elle ce que voit mon acheteur dans l'application ?", "Pas toujours. Un appel d'API n'a ni historique de conversation ni profil personnel, et l'application peut répondre autrement. C'est pourquoi nous posons chaque question deux fois, vous montrons chaque réponse et comptons de la même façon avant et après. Le compte montre un changement. Il ne prévoit pas votre trafic."),
       ("Pouvez-vous garantir qu'un assistant nous recommandera ?", "Non. Personne ne contrôle ce qu'un assistant répond. Nous garantissons le travail : changements en ligne (ou fichiers livrés) sous 7 jours, et si votre compte n'a pas augmenté au recomptage à 30 jours, nous continuons à travailler 30 jours de plus sans frais."),
       ("Avez-vous besoin d'accéder à ma boutique ?", "Pour le Fix Pack, oui : une demande de collaborateur Shopify ou un accès CMS, afin de faire les changements. Si vous préférez, nous envoyons chaque changement en fichiers prêts à coller et vous les appliquez."),
       ("Pourquoi pas un simple outil de suivi ?", "Un outil de suivi dit si vous apparaissez. Il ne réécrit pas vos pages, ne corrige pas les faits erronés et ne demande pas aux guides que les assistants lisent de vous référencer. Ce travail est ce que vous payez."),
       ("Quelles langues ?", "Deux au plus parmi l'anglais, le français, le néerlandais, l'allemand, l'espagnol, l'italien et le portugais."),
       ("En combien de temps ?", "Le mini-audit arrive sous 2 jours ouvrés. Les changements du Fix Pack sont en ligne sous 7 jours après l'accès, ou les fichiers vous parviennent sous 7 jours, et le recomptage a lieu à 30 jours."),
       ("Que garantissez-vous exactement ?", "Changements en retard, remboursement total. Si vous nous donnez l'accès (une demande de collaborateur Shopify ou un accès CMS), les changements sont en ligne sous 7 jours. Si vous choisissez les fichiers prêts à coller, vous les recevez sous 7 jours. Si nous manquons l'une des deux dates, nous vous remboursons les 390 €. Vous n'avez rien à demander. Pas de hausse à 30 jours, 30 jours de plus offerts. Nous reposons les mêmes questions, deux fois chacune, et comptons comme dans votre premier audit. Si votre boutique n'est pas citée dans plus de réponses qu'avant, nous continuons à travailler 30 jours de plus sans frais. Nous ne promettons ni classement, ni trafic, ni ventes. Personne ne contrôle ce qu'un assistant répond."),
       ("Que se passe-t-il après le paiement ?", "Stripe vous envoie le reçu. Nous vous écrivons pour obtenir l'accès, ou pour que vous choisissiez les fichiers prêts à coller. Les 7 jours commencent le jour où vous donnez l'accès, ou le jour où vous nous dites que vous voulez les fichiers. Si nous manquons la date, le remboursement est automatique. À 30 jours, vous recevez le recomptage, avant et après pour chaque assistant, avec les réponses brutes. Rien ne se renouvelle. Après le recomptage, vous pouvez continuer avec CitedBy Monthly (149 € par mois, résiliation par simple réponse à un rapport). Si vous ne faites rien, vous n'êtes plus débité."),
       ("Monthly est-il un engagement ?", "Non. Vous le choisissez après votre recomptage à 30 jours, il est facturé au mois et vous résiliez en répondant à un rapport. Votre Fix Pack ne devient jamais Monthly tout seul.")],
  faq_multi=("Pourquoi plusieurs assistants ?", "Une boutique peut être citée par un assistant et absente d'un autre : chacun a donc son compte. Votre recomptage à 30 jours montre sur lequel vous avez progressé."),
  behind_h="Qui est derrière CitedBy",
  behind="CitedBy est un petit service indépendant exploité depuis l'Espagne. Nous vendons les corrections, c'est pourquoi chaque audit liste les sites que chaque assistant a liés à chaque essai : vous pouvez vérifier notre compte vous-même.",
  legal="Mentions légales", cta_h="Voyez où vous en êtes, gratuitement", cta="Envoyez l'adresse de votre boutique et recevez 16 réponses sur votre catégorie, qui est cité à votre place, et 2 à 3 corrections.",
  foot=(("/data", "Données"), ("/terms", "Conditions"), ("/refund", "Remboursements"), ("/contact", "Contact"), ("/legal", "Mentions légales"), ("/privacy", "Confidentialité")),
  svc="CitedBy : audit et corrections de visibilité dans les assistants IA", svc_type="Visibilité IA pour boutiques en ligne", free_offer="Test gratuit", fp_offer="Fix Pack (payé une fois)", locale="fr",
 ),
}


def li(items): return "".join(f"<li>{E(x)}</li>" for x in items)


def render(lang, engines, css_ver="", check_css_ver=""):
    t = T[lang]
    live = bool(engines)
    day = max((e["tested"] for e in engines), default=None)
    names = [e["name"] for e in engines]
    if live:
        eline = f'{E(t["engines"].split("{date}")[0])}<time datetime="{day.isoformat(timespec="minutes")}">{E(fmt_date(day, lang))}</time>{E(t["engines"].split("{date}")[1].split("{names}")[0])}<b>{E(join_names(names, lang))}</b>{E(t["engines"].split("{names}")[1])}'
    else:
        eline = E(t["engines_none"])
    s = SAMPLE
    sdate = fmt_date(parse_ts(s["date"] + "T00:00:00"), lang)
    rows = "".join(
        f'<tr><td>{E(r["prompt"])}</td><td>{E(", ".join(n["name"] + (" (" + t["s_of"].format(n=n["runs"]) + ")" if n["runs"] < 2 else "") for n in r["named"]))}</td><td>{E(t["s_of"].format(n=r["shop_runs"]))}</td></tr>'
        for r in s["rows"])
    price_btn = (f'<a class="btn p" href="{FIX_URL}" rel="noopener">{E(t["buy"])}</a>' if live
                 else f'<a class="btn p" href="/check">{E(t["go"])}</a>')
    faq = list(t["faq"])
    if len(engines) >= 2: faq.insert(1, t["faq_multi"])
    faq_html = "".join(f"<details><summary>{E(q)}</summary><p>{E(a)}</p></details>" for q, a in faq)
    steps = "".join(f"<li><div><b>{E(h)}</b>{E(b)}</div></li>" for h, b in t["steps"])
    ld = {"@context": "https://schema.org", "@type": "Service", "name": t["svc"], "serviceType": t["svc_type"],
          "provider": {"@type": "Organization", "name": "CitedBy", "url": "https://citedby.eu"}, "areaServed": "EU", "inLanguage": t["locale"],
          "offers": [{"@type": "Offer", "name": t["free_offer"], "price": "0", "priceCurrency": "EUR", "url": f"https://citedby.eu{t['path']}#prices"}]
          + ([{"@type": "Offer", "name": t["fp_offer"], "price": "390", "priceCurrency": "EUR", "url": FIX_URL}] if live else [])
          + [{"@type": "Offer", "name": "CitedBy Monthly", "price": "149", "priceCurrency": "EUR", "url": f"https://citedby.eu{t['path']}#prices",
              "priceSpecification": {"@type": "UnitPriceSpecification", "price": "149", "priceCurrency": "EUR", "billingDuration": 1, "unitCode": "MON"}}]}
    if live:
        ld["description"] = eline_plain(t, day, names, lang)
    ld_json = json.dumps(ld, ensure_ascii=False).replace("</", "<\\/")
    alts = '<link rel="alternate" hreflang="en" href="https://citedby.eu/"><link rel="alternate" hreflang="fr" href="https://citedby.eu/fr"><link rel="alternate" hreflang="x-default" href="https://citedby.eu/">'
    switch = " / ".join(f'<a href="{p}" hreflang="{l}" lang="{l}"{" aria-current=\"page\"" if l == lang else ""}>{l.upper()}</a>' for l, p in (("en", "/"), ("fr", "/fr")))
    chk = "/check" if lang == "en" else "/fr/check"
    # /instant is English only until RES-1130: FR keeps the crawler check as its primary
    pri, pri_txt = ("/instant", t["go_scan"]) if lang == "en" else (chk, t["go"])
    sec = f'<a class="link" href="{chk}">{E(t["go_quick"])}</a>' if lang == "en" else ""
    L = {"en": ("Sample audit", "Named", "Linked", "Top competitor", "of", "answers", "Real audit of a Belgian coffee roaster, run on "), "fr": ("Audit exemple", "Nommée", "Liée", "Concurrent le plus cité", "sur", "réponses", "Audit réel d'un torréfacteur belge, réalisé sur ")}[lang]
    tot = s["answers"]
    card = (f'<aside class="auditcard" aria-label="{E(L[0])}"><p class="ac-h"><b>{E(L[0])}</b> · {E(sdate)}</p>'
            f'<p class="ac-big"><em>{s["named"]}</em> {E(L[4])} {tot} {E(L[5])}</p>'
            f'<div class="ac-row"><span>{E(L[1])}</span><div class="ac-bar"><i style="width:{s["named"]/tot*100:.0f}%"></i></div><b>{s["named"]}/{tot}</b></div>'
            f'<div class="ac-row"><span>{E(L[2])}</span><div class="ac-bar"><i style="width:{s["linked"]/tot*100:.0f}%"></i></div><b>{s["linked"]}/{tot}</b></div>'
            f'<div class="ac-row rival"><span>{E(L[3])}</span><div class="ac-bar"><i style="width:{s["top_competitor_answers"]/tot*100:.0f}%"></i></div><b>{s["top_competitor_answers"]}/{tot}</b></div>'
            f'<p class="ac-n">{E(L[6])}{E(s["assistant"])}.</p></aside>')
    foot = " &nbsp; ".join(f'<a href="{h}">{E(n)}</a>' for h, n in t["foot"])
    return f'''<!doctype html>
<html lang="{lang}"><head>
<meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<title>{E(t["title"])}</title>
<meta name="description" content="{E(t["desc"])}">
<link rel="canonical" href="https://citedby.eu{t["path"]}">{alts}
<meta property="og:title" content="{E(t["ogt"])}"><meta property="og:description" content="{E(t["ogd"])}"><meta property="og:url" content="https://citedby.eu{t["path"]}"><meta property="og:type" content="website"><meta property="og:locale" content="{"fr_FR" if lang == "fr" else "en_IE"}">
<meta name="twitter:card" content="summary"><meta name="twitter:title" content="{E(t["ogt"])}"><meta name="twitter:description" content="{E(t["ogd"])}">
<meta name="theme-color" content="#0F1B2D">
<link rel="icon" href="/favicon.svg" type="image/svg+xml">
<link rel="preload" href="/fonts/newsreader-latin-600-normal.woff2" as="font" type="font/woff2" crossorigin>
<link rel="stylesheet" href="/style.css?v={css_ver}"><link rel="stylesheet" href="/check.css?v={check_css_ver}">
<script type="application/ld+json">{ld_json}</script>
</head><body>
<a class="skip" href="#main">{E(t["skip"])}</a>
<header class="top"><a class="logo" href="{t["path"]}" aria-label="{E(t["home"])}"><svg class="mark" viewBox="0 0 32 32" width="30" height="30" aria-hidden="true" focusable="false"><rect width="32" height="32" fill="#0F1B2D"/><path d="M9 10h14M9 16h14M9 22h8" stroke="#fff" stroke-width="3"/><rect x="20" y="19" width="6" height="6" fill="#2F6BFF"/></svg><span>CitedBy</span></a><div class="hnav"><nav aria-label="Main"><a class="k" href="{chk}">{E(t["nav"][0])}</a><a href="/sample-audit">{E(t["nav"][1])}</a><a class="k" href="#prices">{E(t["nav"][2])}</a><a href="#faq">{E(t["nav"][3])}</a></nav><span class="lsw" aria-label="Language">{switch}</span></div></header>

<main id="main" class="page">
<section class="sec hero">
<div class="col">
<p class="dateline">{E(t["eyebrow"])}</p>
<h1>{E(t["h1"])}</h1>
<p class="lede">{E(t["lede"])}</p>
<p class="engines" id="engines">{eline}</p>
<div class="actions"><a class="btn p" href="{pri}">{E(pri_txt)}</a>{sec}<a class="link" href="#sample">{E(t["sample_link"])}</a></div>
<p class="note" style="margin:var(--s3) 0 0">{E(t["micro"])}</p>
</div>
{card}
</section>

<section id="sample" class="sec"><div class="col"><p class="dateline">{E(t["s_bar"])} · {E(sdate)}</p><h2>{E(t["s_h"])}</h2>
<p class="bigline"><span class="zero"><em>{E(t["s_big"].format(n=s["named"], a=s["answers"], l=s["linked"]))}</em></span></p>
<p>{E(t["s_sub"].format(assistant=s["assistant"], q=s["questions"]))}</p>
<div class="tw"><table><thead><tr><th scope="col">{E(t["s_q"])}</th><th scope="col">{E(t["s_n"])}</th><th scope="col">{E(t["s_t"])}</th></tr></thead><tbody>{rows}</tbody></table></div>
<p class="note">{E(t["s_note"].format(date=sdate))}</p>
<p><a class="link" href="/sample-audit">{E(t["s_more"])}</a></p></div></section>

<section id="how" class="sec"><div class="col"><h2>{E(t["how_h"])}</h2>
<ol class="steps">{steps}</ol><p>{E(t["how_close"])}</p></div></section>

<section id="prices" class="sec"><div class="col"><h2>{E(t["pr_h"])}</h2><p class="sub">{E(t["pr_sub"])}</p>
<div class="ledger">
<div class="row hl"><div><h3>Fix Pack</h3>
<ul>{li(t["fp"])}</ul>
<p class="note">{E(t["anchor"])}</p></div>
<div class="buy"><div class="price">{E(t["fp_price"])} <small>{E(t["fp_small"])}</small></div>{price_btn}<p class="note" style="margin:var(--s3) 0 0"><b>{E(t["g_btn"])}</b></p><p class="note" style="margin:var(--s3) 0 0">{E(t["cap"])}</p></div></div>

<div class="row"><div><h3>{E(t["fc_h"])}</h3>
<ul>{li(t["fc"])}</ul></div>
<div class="buy"><div class="price">{"€0" if lang == "en" else "0 €"}</div><a class="btn g" href="{chk}">{E(t["go"])}</a></div></div>

<div class="row"><div><h3>{E(t["mo_h"])}</h3>
<ul>{li(t["mo"])}</ul></div>
<div class="buy"><div class="price">{E(t["mo_price"])}<small>{E(t["mo_small"])}</small></div><p class="note" style="margin:var(--s3) 0 0">{E(t["mo_note"])}</p></div></div>
</div>
</div></section>

<section id="faq" class="sec"><div class="col"><h2>{E(t["faq_h"])}</h2>
{faq_html}
</div></section>

<section id="behind" class="sec"><div class="col"><h2>{E(t["behind_h"])}</h2>
<p>{E(t["behind"])} <a href="/legal">{E(t["legal"])}</a>.</p></div></section>

<section class="sec cta"><div class="col"><h2>{E(t["cta_h"])}</h2><p class="lede">{E(t["cta"])}</p><div class="actions"><a class="btn p" href="{pri}">{E(pri_txt)}</a></div></div></section>
</main>

<footer><span>© 2026 CitedBy. hello@citedby.eu</span><span>{foot}</span></footer>
</body></html>
'''


def eline_plain(t, day, names, lang):
    return t["engines"].format(date=fmt_date(day, lang), names=join_names(names, lang))
