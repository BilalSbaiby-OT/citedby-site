#!/usr/bin/env python3
"""Render public/fr/{terms,refund,legal,privacy,contact,sample-audit}.html (RES-1172). French wording follows the English pages in public/ clause by clause; change both together."""
import hashlib, html, json, os
E = html.escape
ROOT = os.path.join(os.path.dirname(__file__), "..")
PUB = os.path.join(ROOT, "public")
def ver(n): return hashlib.sha256(open(os.path.join(PUB, n), "rb").read()).hexdigest()[:8]
CSS = ver("style.css")
FOOT_LINKS = (("/data", "Données"), ("/fr/terms", "Conditions"), ("/fr/refund", "Remboursements"), ("/fr/contact", "Contact"), ("/fr/legal", "Mentions légales"), ("/fr/privacy", "Confidentialité"))
FOOT = '<span>' + " &nbsp; ".join(f'<a href="{h}">{t}</a>' for h, t in FOOT_LINKS) + '</span>'
EN_OF = {"terms": "/terms", "refund": "/refund", "legal": "/legal", "privacy": "/privacy", "contact": "/contact", "sample-audit": "/sample-audit"}

def alts(slug):
    return (f'<link rel="canonical" href="https://citedby.eu/fr/{slug}"><link rel="alternate" hreflang="fr" href="https://citedby.eu/fr/{slug}">'
            f'<link rel="alternate" hreflang="en" href="https://citedby.eu{EN_OF[slug]}"><link rel="alternate" hreflang="x-default" href="https://citedby.eu{EN_OF[slug]}">')

def doc(slug, title, desc, body, mail=True):
    d = f'<meta name="description" content="{E(desc)}">' if desc else ""
    return (f'<!doctype html><html lang="fr"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><title>{E(title)}. CitedBy</title>{d}{alts(slug)}'
            f'<link rel="icon" href="/favicon.svg"><link rel="stylesheet" href="/style.css?v={CSS}"></head><body><header class="top"><a class="logo" href="/fr">CitedBy<i aria-hidden="true">1</i></a></header>'
            f'<main class="doc">{body}</main><footer><span>© 2026 CitedBy.{" hello@citedby.eu" if mail else ""}</span>{FOOT}</footer></body></html>\n')

PAGES = {}
PAGES["terms"] = ("Conditions", "Conditions de service des audits CitedBy : ce que nous vendons, les prix, la livraison, les remboursements et vos droits.", """<h1>Conditions</h1>
<h2>1. Ce que nous vendons</h2>
<p>CitedBy vérifie ce que les assistants IA répondent au sujet de votre boutique en ligne et corrige ce qui les empêche de vous citer. Le test gratuit sur /fr/check ne coûte rien. Les produits payants sont le Fix Pack (390 €, payé une seule fois) et CitedBy Monthly (149 € par mois, proposé après votre recomptage à J+30). Le contenu de chacun est décrit sur la <a href="/fr#prices">page d'accueil</a>.</p>
<h2>2. Ce que nous promettons, et ce que nous ne promettons pas</h2>
<p>Nous promettons le travail et la mesure : modifications en ligne, ou fichiers livrés, dans les 7 jours suivant le jour où vous nous donnez l'accès ou nous dites vouloir les fichiers, et un recomptage à J+30 compté de la même façon que votre premier audit. Personne ne contrôle ce que répond un assistant ; nous ne promettons donc ni classement, ni mentions, ni chiffre d'affaires. Les réponses des assistants IA varient d'une exécution à l'autre ; nos comptes sont un échantillon, pas une garantie.</p>
<h2>3. Prix et paiement</h2>
<p>Les paiements sont traités par Stripe ; nous ne voyons jamais les données de votre carte. Le prix affiché sur la page au moment de l'achat est le prix que vous payez. Les prix sont des prix finaux : la TVA éventuellement applicable est incluse et rien n'est ajouté au paiement. Les professionnels peuvent demander une facture à hello@citedby.eu. Le Fix Pack est un paiement unique et ne se renouvelle pas. CitedBy Monthly se renouvelle chaque mois jusqu'à ce que vous résiliiez en répondant à n'importe quel rapport, et la résiliation arrête le prélèvement suivant.</p>
<h2>4. Accès à votre boutique</h2>
<p>Si vous nous donnez un accès (une demande de collaborateur Shopify ou un identifiant de CMS), nous ne l'utilisons que pour les modifications de votre Fix Pack et vous pouvez le retirer à tout moment. Nous ne modifions ni les prix, ni les produits, ni le paiement.</p>
<h2>5. Remboursements et rétractation</h2>
<p>Voir <a href="/fr/refund">Remboursements</a>. En bref : si nous manquons le délai de 7 jours, vous êtes remboursé automatiquement, et vous pouvez annuler avant le début du travail pour un remboursement complet.</p>
<h2>6. Responsabilité</h2>
<p>Nous sommes responsables du travail livré tel que décrit ci-dessus. Nous ne sommes pas responsables des ventes que vous faites ou non, ni de ce que dit un assistant tiers. Rien ici ne limite les droits dont vous disposez en tant que consommateur en vertu du droit de l'Union européenne ou du droit espagnol.</p>
<h2>7. Modifications</h2>
<p>Nous pouvons mettre à jour ces conditions. Les conditions en vigueur le jour de votre achat s'appliquent à cet achat.</p>
<h2>8. Qui nous sommes</h2>
<p>CitedBy est un service indépendant établi en Espagne. Les informations sur le prestataire exigées par la loi espagnole figurent dans les <a href="/fr/legal">mentions légales</a>. Questions : <a href="/fr/contact">contact</a>. Le droit espagnol s'applique, sans retirer les protections impératives du consommateur du pays où vous vivez.</p>""".replace("ou nous dites vouloir", "ou le jour où vous nous dites vouloir"))
PAGES["refund"] = ("Remboursements", "Comment fonctionnent les remboursements CitedBy : la garantie de livraison à 7 jours, le droit de rétractation de 14 jours et comment le demander.", """<h1>Remboursements</h1>
<h2>Retard : remboursement complet, automatique</h2>
<p>Si vous nous donnez l'accès, les modifications du Fix Pack sont en ligne dans les 7 jours. Si vous choisissez les fichiers prêts à coller, vous les recevez dans les 7 jours. Les 7 jours commencent le jour où vous nous donnez l'accès, ou le jour où vous nous dites vouloir les fichiers. Si nous manquons la date, nous remboursons les 390 € et vous n'avez rien à demander. Si nous manquons la date, vous pouvez aussi demander le remboursement plutôt que d'attendre la livraison tardive.</p>
<h2>Annulation avant le début du travail : remboursement complet</h2>
<p>Vous pouvez vous rétracter dans les 14 jours suivant le paiement, comme le prévoit le droit européen de la consommation. Si vous annulez avant que nous ayons commencé le travail, tout vous est rendu. Si vous nous demandez de commencer pendant ces 14 jours puis annulez, nous conservons la part du travail déjà réalisée, calculée au prorata, et remboursons le reste. Nous ne commençons pendant les 14 jours que si vous nous le demandez.</p>
<h2>Mois complet</h2>
<p>Nous prenons 5 Fix Packs par mois. Si le mois est complet, nous vous envoyons votre date de début par e-mail avant tout travail, et vous pouvez obtenir à la place un remboursement complet.</p>
<h2>Ce qu'est la garantie à J+30</h2>
<p>Si, à J+30, votre boutique n'est citée dans pas plus de réponses qu'avant, nous continuons à travailler 30 jours de plus sans frais. C'est du travail supplémentaire, pas un remboursement.</p>
<h2>CitedBy Monthly</h2>
<p>Résiliez en répondant à n'importe quel rapport. Le prélèvement suivant s'arrête et le mois déjà payé va jusqu'à son terme. Pour votre premier paiement Monthly, le droit de rétractation de 14 jours ci-dessus s'applique aussi : si vous annulez dans les 14 jours après nous avoir demandé de commencer, nous conservons la part déjà réalisée, au prorata, et remboursons le reste.</p>
<h2>Comment le demander</h2>
<p>Écrivez à <a href="mailto:hello@citedby.eu?subject=Remboursement">hello@citedby.eu</a> en indiquant l'adresse de votre boutique. Nous répondons sous 2 jours ouvrés et remboursons sur le moyen de paiement d'origine via Stripe, dans les 14 jours suivant votre demande.</p><h2>Modèle de formulaire de rétractation</h2>
<p>Pour vous rétracter du contrat, envoyez-nous ce texte par e-mail (directive 2011/83/UE, annexe I, partie B). Vous n'êtes pas obligé de l'utiliser.</p>
<blockquote><p>À l'attention de CitedBy, hello@citedby.eu :<br>Je vous notifie par la présente ma rétractation du contrat portant sur la prestation de services suivante : [service commandé].<br>Commandé le [date]. Nom du consommateur : [nom]. Adresse du consommateur : [adresse, uniquement si vous souhaitez une réponse postale]. Date : [date].</p></blockquote>""")
PAGES["legal"] = ("Mentions légales", "", """<h1>Mentions légales</h1><p>CitedBy (citedby.eu) est exploité par Bilal Sbaiby, personne physique résidant en Espagne (LSSI-CE, art. 10). Adresse postale : Travesia del Nuevo Alamin 11, 2D, 19005 Guadalajara, Espagne. Contact : hello@citedby.eu.</p>""")
PAGES["privacy"] = ("Confidentialité", "", """<h1>Confidentialité</h1><p>Les pages publiques ne déposent aucun cookie et n'exécutent aucun script tiers. Un seul cookie existe : si vous vous connectez à un compte, nous déposons <code>ci_session</code>. Il vous garde connecté 30 jours, est strictement nécessaire à cela, est HttpOnly, et n'est jamais utilisé pour le suivi ni la publicité. Notre serveur conserve des journaux d'accès standard (adresse IP, page, heure) pour la sécurité et pour compter les visites ; ils ne sont conservés que le temps nécessaire à ces finalités.</p><p>Si vous nous écrivez ou achetez l'audit, nous utilisons l'adresse de votre boutique et votre adresse e-mail uniquement pour livrer l'audit et vous répondre. Les paiements sont traités par Stripe, qui gère les données de carte ; nous ne les voyons jamais. Nous comptons des événements anonymes par jour et par langue (test lancé, test terminé, e-mail envoyé, lien Fix Pack cliqué), sans adresse IP ni identifiant. Si vous demandez le mini-audit par e-mail, nous conservons votre adresse e-mail, l'adresse de votre boutique, votre pays, votre langue et votre secteur, et nous envoyons d'abord un e-mail de confirmation (double opt-in). Nous ne vous écrivons qu'à propos de cet audit et d'un seul message de suivi, supprimons les demandes non confirmées après 7 jours et toutes les demandes après 12 mois, et vous pouvez supprimer la vôtre à tout moment avec le lien de désinscription de nos e-mails. Notre serveur enregistre brièvement votre adresse IP pour limiter les abus. Pour accéder à vos données ou les supprimer, écrivez à hello@citedby.eu.</p><p>Si vous enregistrez un comptage dans un compte, nous conservons votre adresse e-mail, la langue choisie, le nom et l'adresse de votre boutique, les comptages enregistrés (quels assistants ont cité votre boutique, quels concurrents ils ont cités) et, si vous vous abonnez, l'identifiant d'abonnement Stripe et le forfait. Nous vous envoyons un lien de connexion par e-mail ; il fonctionne une seule fois et pendant 15 minutes, et nous ne le conservons que sous forme de hash. Nous tenons un journal des e-mails envoyés, qui contient l'adresse et l'objet mais pas le lien de connexion. Stripe conserve de son côté les enregistrements de paiement et de facturation.</p><p>Vous pouvez exporter les données de votre compte depuis votre tableau de bord et supprimer votre compte. La suppression annule d'abord tout abonnement actif, puis efface le compte, la boutique, les comptages enregistrés et les rapports de recomptage, les liens de connexion, et votre adresse dans le journal des e-mails. Le test gratuit conserve aussi l'adresse de la boutique et le comptage produit dans notre file de tests ; écrivez à hello@citedby.eu pour les faire supprimer.</p>""")
PAGES["contact"] = ("Contact", "Contacter CitedBy : une seule adresse e-mail, réponse sous 2 jours ouvrés.", """<h1>Contact</h1>
<p>Écrivez à <a href="mailto:hello@citedby.eu">hello@citedby.eu</a>. Nous répondons sous 2 jours ouvrés.</p>
<ul><li>Questions sur un audit ou le Fix Pack : indiquez l'adresse de votre boutique.</li><li>Remboursements et annulations : voir <a href="/fr/refund">Remboursements</a>, puis utilisez la même adresse.</li><li>Vos données (accès ou suppression) : <a href="/fr/privacy">Confidentialité</a>.</li><li>Agences et freelances : <a href="/partners">Conditions partenaires</a> (en anglais).</li></ul>
<p>Les informations sur le prestataire exigées par la loi espagnole figurent dans les <a href="/fr/legal">mentions légales</a>.</p>""")

def sample():
    s = json.load(open(os.path.join(ROOT, "data", "sample.json")))
    day = "15 oct. 2026"
    rows = "".join(
        f'<tr><td>{E(r["prompt"])}</td><td data-label="Sites liés, essai 1">{E(", ".join(r["linked"][0]) or "aucun")}</td>'
        f'<td data-label="Sites liés, essai 2">{E(", ".join(r["linked"][1]) or "aucun")}</td><td data-label="Cette boutique">citée {r["shop_named"]} sur 2, liée 0 sur 2</td></tr>' for r in s["all_rows"])
    n, a, q = s["named"], s["answers"], s["questions"]
    return f'''<!doctype html>
<html lang="fr"><head>
<meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<title>Exemple d'audit : un torréfacteur belge cité dans {n} réponse sur {a} des assistants IA | CitedBy</title>
<meta name="description" content="Un exemple complet d'audit CitedBy, boutique anonymisée : {q} questions d'acheteur posées deux fois, chaque site lié par l'assistant et les réponses brutes en CSV.">
{alts("sample-audit")}
<meta property="og:title" content="Exemple d'audit : cité dans {n} réponse sur {a} des assistants IA"><meta property="og:description" content="{q} questions d'acheteur posées deux fois, chaque site lié, réponses brutes en CSV. Boutique anonymisée."><meta property="og:url" content="https://citedby.eu/fr/sample-audit"><meta property="og:type" content="article">
<meta name="theme-color" content="#0F1B2D">
<link rel="icon" href="/favicon.svg" type="image/svg+xml">
<link rel="preload" href="/fonts/newsreader-latin-600-normal.woff2" as="font" type="font/woff2" crossorigin>
<link rel="stylesheet" href="/style.css?v={CSS}"><link rel="stylesheet" href="/data.css?v={ver("data.css")}">
</head><body class="dp">
<header class="top"><a class="logo" href="/fr" aria-label="CitedBy accueil">CitedBy<i aria-hidden="true">1</i></a><nav aria-label="Principal"><a class="k" href="/data">Données</a><a class="k" href="/fr/check">Test gratuit</a></nav></header>
<main class="doc wide">
<p class="crumb"><a href="/fr">CitedBy</a> / Exemple d'audit</p>
<p class="dateline">Exemple d'audit. Boutique anonymisée, réponses réelles. Réalisé le {day}.</p>
<h1>Un torréfacteur belge en ligne, cité dans {n} réponse sur {a}</h1>
<p class="ans">Nous avons posé à {s["assistant"]} {q} questions qu'un acheteur poserait, en français, chacune deux fois. Chaque réponse est conservée. La boutique a été citée dans {n} d'entre elles et liée dans {s["linked"]}. La boutique concurrente la plus citée apparaît dans {s["top_competitor_answers"]} réponses sur {a}.</p>
<p class="src">API avec recherche web, {day}. Les réponses varient d'une exécution à l'autre. Les sites ci-dessous sont ceux que l'assistant a liés, pas notre avis. Ceci montre le format du rapport ; le vôtre porte sur votre boutique et votre marché. <a href="/sample-audit.csv">Les {a} réponses en CSV</a>, avec liens et horaires, nom de la boutique retiré.</p>

<section><h2>1. Sites liés par Claude, question par question</h2>
<div class="tw"><table><thead><tr><th scope="col">Un acheteur demande</th><th scope="col">Sites liés, essai 1</th><th scope="col">Sites liés, essai 2</th><th scope="col">Cette boutique</th></tr></thead><tbody>
{rows}
</tbody></table></div>
<p class="src">Règle de comptage : une boutique est comptée comme citée quand son nom ou son domaine apparaît dans le texte de la réponse ou dans les liens. Une boutique reste une boutique quelle que soit son écriture : « Café du Jour » et fr.cafedujour.be comptent ensemble. « Citée 1 fois sur 2 » n'est jamais arrondi en « recommandée ».</p></section>

<section><h2>2. Ce que le rapport Fix Pack ajoute</h2>
<ul><li>40 questions d'acheteur, chacune posée deux fois, au lieu de 8.</li><li>Le même comptage sur chaque assistant que nous pouvons mesurer ce jour-là, chacun avec son propre chiffre.</li><li>Une carte des concurrents : qui est cité, qui est lié, quelles pages ont été citées.</li><li>Les modifications faites sur votre boutique, ou en fichiers prêts à coller.</li><li>Le recomptage à J+30, avant et après, avec les réponses brutes.</li></ul>
<p class="src">Chaque audit vérifie aussi les bases techniques de votre page d'accueil : si robots.txt laisse entrer les robots de recherche IA, si le texte produit figure dans le HTML brut, et si la page dit qui vous êtes. Nous les vérifions parce qu'un échec bloquerait tout le reste, pas parce que les réussir suffit à être cité.</p></section>

<section class="cta"><h2>Voyez votre boutique dans ce tableau</h2><p class="lede">Le test gratuit prend environ 10 secondes et ne demande pas d'e-mail. Le mini-audit complet suit par e-mail sous 2 jours ouvrés.</p><div class="actions"><a class="btn p" href="/fr/check">Tester ma boutique, gratuit</a></div></section>
</main>
<footer><span>© 2026 CitedBy. hello@citedby.eu</span>{FOOT}</footer>
</body></html>
'''

if __name__ == "__main__":
    os.makedirs(os.path.join(PUB, "fr"), exist_ok=True)
    for slug, (title, desc, body) in PAGES.items():
        open(os.path.join(PUB, "fr", slug + ".html"), "w").write(doc(slug, title, desc, body, mail=slug not in ("legal", "privacy")))
    open(os.path.join(PUB, "fr", "sample-audit.html"), "w").write(sample())
    print("wrote", len(PAGES) + 1, "pages in public/fr")
