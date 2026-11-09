#!/usr/bin/env python3
"""Hitri SEO pregled spletne strani.

Uporaba:
    python seo_check.py https://primer.si
    python seo_check.py primer.si --json

Skripta uporablja samo standardno knjižnico Pythona (3.9+).
"""
from __future__ import annotations

import argparse
import json
import sys
import time
from dataclasses import asdict, dataclass
from html.parser import HTMLParser
from urllib.error import HTTPError, URLError
from urllib.parse import urljoin, urlparse
from urllib.request import Request, urlopen

OK, WARN, FAIL = "ok", "opozorilo", "napaka"
SYMBOLS = {OK: "✓", WARN: "!", FAIL: "✗"}
USER_AGENT = "seo-hitri-pregled/1.0 (+https://github.com/)"
MAX_BYTES = 5 * 1024 * 1024

TITLE_MIN, TITLE_MAX = 30, 60
DESC_MIN, DESC_MAX = 70, 160
MIN_WORDS = 300
SLOW_SECONDS = 1.5


@dataclass
class Check:
    name: str
    status: str
    message: str


class PageParser(HTMLParser):
    """Iz HTML-ja pobere podatke, pomembne za SEO."""

    def __init__(self) -> None:
        super().__init__(convert_charrefs=True)
        self.title = ""
        self.lang: str | None = None
        self.metas: dict[str, str] = {}
        self.canonical: str | None = None
        self.h1: list[str] = []
        self.images = 0
        self.images_no_alt = 0
        self.json_ld = 0
        self.words = 0
        self._in_title = False
        self._in_h1 = False
        self._h1_buf: list[str] = []
        self._skip = 0

    def handle_starttag(self, tag, attrs):
        a = {k.lower(): (v or "") for k, v in attrs}
        if tag == "html" and a.get("lang"):
            self.lang = a["lang"].strip()
        elif tag == "title":
            self._in_title = True
        elif tag == "meta":
            key = (a.get("name") or a.get("property") or "").lower().strip()
            if key and key not in self.metas:
                self.metas[key] = a.get("content", "").strip()
        elif tag == "link":
            if "canonical" in a.get("rel", "").lower().split() and a.get("href"):
                self.canonical = a["href"].strip()
        elif tag == "h1":
            self._in_h1 = True
            self._h1_buf = []
        elif tag == "img":
            self.images += 1
            if "alt" not in a:
                self.images_no_alt += 1
        elif tag in ("script", "style"):
            if tag == "script" and a.get("type", "").lower() == "application/ld+json":
                self.json_ld += 1
            self._skip += 1

    def handle_endtag(self, tag):
        if tag == "title":
            self._in_title = False
        elif tag == "h1" and self._in_h1:
            self._in_h1 = False
            self.h1.append(" ".join("".join(self._h1_buf).split()))
        elif tag in ("script", "style") and self._skip:
            self._skip -= 1

    def handle_data(self, data):
        if self._in_title:
            self.title += data
            return
        if self._skip:
            return
        if self._in_h1:
            self._h1_buf.append(data)
        self.words += len(data.split())


def _length_check(name: str, text: str, lo: int, hi: int) -> Check:
    n = len(text)
    if not text:
        return Check(name, FAIL, "Manjka.")
    if n < lo:
        return Check(name, WARN, f"Prekratek ({n} znakov, priporočeno {lo}–{hi}): »{text}«")
    if n > hi:
        return Check(name, WARN, f"Predolg ({n} znakov, priporočeno {lo}–{hi}).")
    return Check(name, OK, f"{n} znakov: »{text}«")


def analyze_html(html: str, url: str = "") -> list[Check]:
    """Pregleda HTML ene strani in vrne seznam preverjanj."""
    p = PageParser()
    p.feed(html)
    p.close()
    checks: list[Check] = []

    checks.append(_length_check("Naslov (title)", " ".join(p.title.split()), TITLE_MIN, TITLE_MAX))
    checks.append(_length_check("Meta opis", p.metas.get("description", ""), DESC_MIN, DESC_MAX))

    if len(p.h1) == 1 and p.h1[0]:
        checks.append(Check("Naslov H1", OK, f"»{p.h1[0]}«"))
    elif not p.h1:
        checks.append(Check("Naslov H1", FAIL, "Stran nima naslova H1."))
    elif len(p.h1) > 1:
        checks.append(Check("Naslov H1", WARN, f"Stran ima {len(p.h1)} naslovov H1, priporočen je eden."))
    else:
        checks.append(Check("Naslov H1", WARN, "Naslov H1 je prazen."))

    if p.images == 0:
        checks.append(Check("Alt besedila slik", OK, "Na strani ni slik."))
    elif p.images_no_alt == 0:
        checks.append(Check("Alt besedila slik", OK, f"Vseh {p.images} slik ima atribut alt."))
    else:
        status = FAIL if p.images_no_alt > p.images / 2 else WARN
        checks.append(Check("Alt besedila slik", status,
                            f"{p.images_no_alt} od {p.images} slik nima atributa alt."))

    if p.lang:
        checks.append(Check("Jezik strani (lang)", OK, f"lang=\"{p.lang}\""))
    else:
        checks.append(Check("Jezik strani (lang)", WARN, "Oznaka <html> nima atributa lang."))

    if "viewport" in p.metas:
        checks.append(Check("Mobilni prikaz (viewport)", OK, "Meta viewport je nastavljen."))
    else:
        checks.append(Check("Mobilni prikaz (viewport)", FAIL, "Manjka meta viewport."))

    if p.canonical:
        checks.append(Check("Kanonični URL", OK, urljoin(url, p.canonical) if url else p.canonical))
    else:
        checks.append(Check("Kanonični URL", WARN, "Manjka <link rel=\"canonical\">."))

    robots = p.metas.get("robots", "").lower()
    if "noindex" in robots:
        checks.append(Check("Indeksiranje", FAIL, f"Stran prepoveduje indeksiranje (robots: {robots})."))
    else:
        checks.append(Check("Indeksiranje", OK, "Stran dovoli indeksiranje."))

    missing_og = [k for k in ("og:title", "og:description", "og:image") if not p.metas.get(k)]
    if missing_og:
        checks.append(Check("Open Graph (deljenje)", WARN, "Manjka: " + ", ".join(missing_og)))
    else:
        checks.append(Check("Open Graph (deljenje)", OK, "og:title, og:description in og:image so nastavljeni."))

    if p.json_ld:
        checks.append(Check("Strukturirani podatki", OK, f"Najdenih blokov JSON-LD: {p.json_ld}."))
    else:
        checks.append(Check("Strukturirani podatki", WARN, "Ni strukturiranih podatkov (JSON-LD)."))

    if p.words >= MIN_WORDS:
        checks.append(Check("Količina besedila", OK, f"Približno {p.words} besed."))
    else:
        checks.append(Check("Količina besedila", WARN,
                            f"Približno {p.words} besed (priporočeno vsaj {MIN_WORDS})."))
    return checks


def fetch(url: str, timeout: float = 15.0) -> tuple[int, str, str, float]:
    """Vrne (statusna koda, končni URL, vsebina, čas v sekundah)."""
    req = Request(url, headers={"User-Agent": USER_AGENT, "Accept": "*/*"})
    start = time.monotonic()
    try:
        with urlopen(req, timeout=timeout) as resp:
            raw = resp.read(MAX_BYTES)
            charset = resp.headers.get_content_charset() or "utf-8"
            status, final = resp.status, resp.geturl()
    except HTTPError as e:
        return e.code, url, "", time.monotonic() - start
    elapsed = time.monotonic() - start
    try:
        body = raw.decode(charset, errors="replace")
    except LookupError:
        body = raw.decode("utf-8", errors="replace")
    return status, final, body, elapsed


def _exists(url: str, timeout: float) -> bool:
    try:
        status, _, body, _ = fetch(url, timeout)
    except (URLError, OSError, ValueError):
        return False
    return status == 200 and bool(body.strip())


def check_site(url: str, timeout: float = 15.0) -> list[Check]:
    """Prenese stran in opravi vsa preverjanja."""
    status, final, body, elapsed = fetch(url, timeout)
    checks: list[Check] = []

    if status == 200:
        checks.append(Check("Dostopnost", OK, f"HTTP {status}"))
    else:
        checks.append(Check("Dostopnost", FAIL, f"Strežnik je vrnil HTTP {status}."))
        return checks

    if urlparse(final).scheme == "https":
        checks.append(Check("HTTPS", OK, "Stran uporablja varno povezavo."))
    else:
        checks.append(Check("HTTPS", FAIL, "Stran ne uporablja HTTPS."))

    speed = OK if elapsed <= SLOW_SECONDS else WARN
    checks.append(Check("Odzivni čas strežnika", speed, f"{elapsed:.2f} s"))

    checks.extend(analyze_html(body, final))

    root = f"{urlparse(final).scheme}://{urlparse(final).netloc}"
    for name, path in (("robots.txt", "/robots.txt"), ("Zemljevid strani (sitemap.xml)", "/sitemap.xml")):
        if _exists(root + path, timeout):
            checks.append(Check(name, OK, root + path))
        else:
            checks.append(Check(name, WARN, f"Ni najdeno na {root + path}."))
    return checks


def score(checks: list[Check]) -> int:
    """Ocena 0–100: ok = 1 točka, opozorilo = pol točke, napaka = 0."""
    if not checks:
        return 0
    points = sum({OK: 1.0, WARN: 0.5, FAIL: 0.0}[c.status] for c in checks)
    return round(100 * points / len(checks))


def normalize_url(url: str) -> str:
    url = url.strip()
    return url if "://" in url else "https://" + url


def print_report(url: str, checks: list[Check]) -> None:
    print(f"\nSEO pregled: {url}\n" + "-" * 60)
    for c in checks:
        print(f" {SYMBOLS[c.status]}  {c.name}: {c.message}")
    counts = {s: sum(c.status == s for c in checks) for s in (OK, WARN, FAIL)}
    print("-" * 60)
    print(f"Ocena: {score(checks)}/100   "
          f"(v redu: {counts[OK]}, opozorila: {counts[WARN]}, napake: {counts[FAIL]})\n")


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description="Hitri SEO pregled spletne strani.")
    ap.add_argument("url", help="naslov strani, npr. https://primer.si")
    ap.add_argument("--json", action="store_true", help="izpis v obliki JSON")
    ap.add_argument("--timeout", type=float, default=15.0, help="časovna omejitev v sekundah (privzeto 15)")
    args = ap.parse_args(argv)

    url = normalize_url(args.url)
    try:
        checks = check_site(url, args.timeout)
    except (URLError, OSError, ValueError) as e:
        print(f"Strani {url} ni bilo mogoče odpreti: {e}", file=sys.stderr)
        return 2

    if args.json:
        print(json.dumps({"url": url, "ocena": score(checks),
                          "preverjanja": [asdict(c) for c in checks]},
                         ensure_ascii=False, indent=2))
    else:
        print_report(url, checks)
    return 1 if any(c.status == FAIL for c in checks) else 0


if __name__ == "__main__":
    sys.exit(main())
