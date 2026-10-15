"""Home page render rules (RES-873). Run: python3 test_home.py"""
import datetime, json, os, re, tempfile, unittest
import home

NOW = datetime.datetime(2026, 10, 16, 9, 0, tzinfo=datetime.timezone.utc)

def engines_file(rows):
    f = tempfile.NamedTemporaryFile("w", suffix=".json", delete=False); json.dump({"engines": rows}, f); f.close(); return f.name

def live(*names, hours=2):
    t = (NOW - datetime.timedelta(hours=hours)).isoformat()
    return home.live_engines(engines_file([{"name": n, "route": "API", "tested": t} for n in names]), NOW)

class T(unittest.TestCase):
    def test_no_chatgpt_when_not_live(self):
        for lang in ("en", "fr"):
            self.assertEqual(home.render(lang, live("Claude")).lower().count("chatgpt"), 0)

    def test_chatgpt_only_in_engines_rendered_lines(self):
        h = home.render("en", live("Claude", "ChatGPT"))
        lines = [l for l in h.splitlines() if "chatgpt" in l.lower()]
        self.assertTrue(lines)
        self.assertTrue(all('id="engines"' in l or "application/ld+json" in l for l in lines), lines)  # hero line and JSON-LD description, both from engines.json

    def test_every_live_name_present_with_date(self):
        h = home.render("en", live("Claude", "Gemini"))
        self.assertIn("<b>Claude and Gemini</b>", h)
        self.assertIn("16 Oct 2026", h)
        self.assertIn("Why several assistants?", h)

    def test_single_engine_has_no_several_faq(self):
        self.assertNotIn("Why several assistants?", home.render("en", live("Claude")))

    def test_stale_engine_dropped(self):
        self.assertEqual(live("Claude", hours=25), [])

    def test_future_or_garbage_dropped(self):
        self.assertEqual(live("Claude", hours=-3), [])
        self.assertEqual(home.live_engines("/nonexistent.json", NOW), [])
        self.assertEqual(home.live_engines(engines_file([{"name": "X", "tested": "not a date"}, {"tested": "2026-10-16T08:00:00Z"}]), NOW), [])

    def test_empty_renders_fallback_and_no_buy_button(self):
        h = home.render("en", [])
        self.assertIn("We are connecting assistants", h)
        self.assertNotIn("buy.stripe.com/8x2dR17ri7C06p44cX0oM08", h)
        self.assertNotIn('"price": "390"', h)
        self.assertIn('href="/check"', h)

    def test_prices_and_guarantees(self):
        h = home.render("en", live("Claude"))
        for s in ("€390", "€149", "buy.stripe.com/8x2dR17ri7C06p44cX0oM08", "Late changes, full refund.", "No rise at day 30"):
            self.assertIn(s, h)
        f = home.render("fr", live("Claude"))
        for s in ("390 €", "149 €"):
            self.assertIn(s, f)

    def test_no_retired_blocks(self):
        h = home.render("en", live("Claude"))
        for s in ("127", "Logged-out", "logged-out"):
            self.assertNotIn(s, h)

    def test_sample_numbers_match_data(self):
        s = json.load(open(os.path.join(os.path.dirname(__file__), "data", "sample.json")))
        h = home.render("en", live("Claude"))
        self.assertIn(f"Named in {s['named']} of {s['answers']} answers. Linked in {s['linked']}.", h)
        self.assertNotIn("corica", h.lower())

if __name__ == "__main__":
    unittest.main()
