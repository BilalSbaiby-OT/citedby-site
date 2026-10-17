import os, re, pathlib, tempfile
os.environ.setdefault("OPTIN_SECRET", "x" * 40); os.environ.setdefault("BASE_URL", "http://t"); os.environ.setdefault("DATA_DIR", tempfile.mkdtemp())
import server
L = (pathlib.Path(__file__).parent / "public" / "legal.html").read_text()

def test_mail_footer_names_no_other_brand_and_links_the_legal_notice():
    for lang, label in (("en", "Legal notice"), ("fr", "Mentions légales"), ("nl", "Juridische informatie")):
        body = server.TXT[lang]["body"]
        assert "Resale IQ" not in body, lang
        assert f"CitedBy · {label}: https://citedby.eu/legal" in body.replace(" :", ":"), lang

def test_legal_page_has_the_operator_block_and_no_other_brand():
    assert "Resale IQ" not in L
    assert "LSSI-CE art. 10" in L and "hello@citedby.eu" in L and "Postal address:" in L
    assert re.search(r"is operated by [A-Z]\w+ [A-Z]\w+, an individual resident in Spain", L)  # LSSI-CE art. 10: the operator is named here and nowhere else
