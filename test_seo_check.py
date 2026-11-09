import unittest

from seo_check import FAIL, OK, WARN, analyze_html, normalize_url, score

GOOD = """<!doctype html>
<html lang="sl">
<head>
<title>Izdelava spletnih strani za mala podjetja | Primer</title>
<meta name="description" content="Izdelujemo hitre in pregledne spletne strani za mala podjetja po vsej Sloveniji. Pokličite nas za brezplačen posvet.">
<meta name="viewport" content="width=device-width, initial-scale=1">
<link rel="canonical" href="https://primer.si/">
<meta property="og:title" content="Primer">
<meta property="og:description" content="Opis">
<meta property="og:image" content="https://primer.si/slika.jpg">
<script type="application/ld+json">{"@type": "Organization"}</script>
</head>
<body>
<h1>Izdelava spletnih strani</h1>
<img src="a.jpg" alt="Primer strani">
<p>%s</p>
</body>
</html>""" % ("beseda " * 320)


def by_name(checks):
    return {c.name: c for c in checks}


class AnalyzeTests(unittest.TestCase):
    def test_good_page_is_all_ok(self):
        checks = analyze_html(GOOD, "https://primer.si/")
        self.assertTrue(all(c.status == OK for c in checks), [c for c in checks if c.status != OK])
        self.assertEqual(score(checks), 100)

    def test_empty_page(self):
        c = by_name(analyze_html("<html><body><p>Pozdrav</p></body></html>"))
        self.assertEqual(c["Naslov (title)"].status, FAIL)
        self.assertEqual(c["Meta opis"].status, FAIL)
        self.assertEqual(c["Naslov H1"].status, FAIL)
        self.assertEqual(c["Mobilni prikaz (viewport)"].status, FAIL)
        self.assertEqual(c["Jezik strani (lang)"].status, WARN)

    def test_multiple_h1(self):
        c = by_name(analyze_html("<h1>Ena</h1><h1>Dva</h1>"))
        self.assertEqual(c["Naslov H1"].status, WARN)

    def test_images_without_alt(self):
        c = by_name(analyze_html('<img src="a.jpg"><img src="b.jpg" alt=""><img src="c.jpg" alt="c">'))
        self.assertEqual(c["Alt besedila slik"].status, WARN)
        self.assertIn("1 od 3", c["Alt besedila slik"].message)

    def test_noindex(self):
        c = by_name(analyze_html('<meta name="robots" content="noindex, nofollow">'))
        self.assertEqual(c["Indeksiranje"].status, FAIL)

    def test_script_text_is_not_counted(self):
        c = by_name(analyze_html("<script>var a = 'ena dva tri';</script><p>ena dva</p>"))
        self.assertIn("2 besed", c["Količina besedila"].message)

    def test_normalize_url(self):
        self.assertEqual(normalize_url("primer.si"), "https://primer.si")
        self.assertEqual(normalize_url("http://primer.si"), "http://primer.si")


if __name__ == "__main__":
    unittest.main()
