# SEO hitri pregled

Majhno orodje za ukazno vrstico, ki v nekaj sekundah preveri osnovne SEO elemente spletne strani in izpiše pregledno poročilo z oceno od 0 do 100.

Deluje s samim Pythonom (3.9 ali novejši), brez nameščanja dodatnih knjižnic.

## Uporaba

```bash
python seo_check.py https://primer.si
```

Primer izpisa:

```
SEO pregled: https://primer.si
------------------------------------------------------------
 ✓  Dostopnost: HTTP 200
 ✓  HTTPS: Stran uporablja varno povezavo.
 ✓  Odzivni čas strežnika: 0.42 s
 !  Naslov (title): Prekratek (12 znakov, priporočeno 30–60): »Primer d.o.o.«
 ✗  Meta opis: Manjka.
 ✓  Naslov H1: »Izdelava spletnih strani«
 !  Alt besedila slik: 3 od 14 slik nima atributa alt.
 ...
------------------------------------------------------------
Ocena: 73/100   (v redu: 9, opozorila: 4, napake: 2)
```

### Možnosti

| Možnost | Opis |
| --- | --- |
| `--json` | Izpis v obliki JSON (za nadaljnjo obdelavo) |
| `--timeout 30` | Časovna omejitev za prenos strani v sekundah (privzeto 15) |

Izhodna koda je `0`, če ni napak, `1`, če je najdena vsaj ena napaka, in `2`, če strani ni mogoče odpreti. Tako lahko orodje uporabiš tudi v avtomatiziranih preverjanjih.

## Kaj preverja

| Preverjanje | Kaj je v redu |
| --- | --- |
| Dostopnost | Strežnik vrne HTTP 200 |
| HTTPS | Stran teče na varni povezavi |
| Odzivni čas strežnika | Do 1,5 s |
| Naslov (title) | 30–60 znakov |
| Meta opis | 70–160 znakov |
| Naslov H1 | Natanko en H1 |
| Alt besedila slik | Vse slike imajo atribut `alt` |
| Jezik strani | `<html lang="...">` je nastavljen |
| Mobilni prikaz | Meta `viewport` obstaja |
| Kanonični URL | `<link rel="canonical">` obstaja |
| Indeksiranje | Stran nima `noindex` |
| Open Graph | `og:title`, `og:description`, `og:image` |
| Strukturirani podatki | Vsaj en blok JSON-LD |
| Količina besedila | Vsaj 300 besed |
| robots.txt | Datoteka obstaja |
| sitemap.xml | Datoteka obstaja na `/sitemap.xml` |

Ocena: vsako preverjanje v redu šteje 1 točko, opozorilo pol točke, napaka 0.

## Omejitve

- Pregleda eno stran (URL, ki ga podaš), ne celotnega spletnega mesta.
- Ne izvaja JavaScripta, zato pri straneh, ki vsebino naložijo šele v brskalniku, vidi le začetni HTML.
- Zemljevid strani išče samo na `/sitemap.xml`.
- To je hiter prvi pregled, ne nadomestilo za celovito SEO analizo.

## Testi

```bash
python -m unittest
```

## Licenca

MIT – glej datoteko [LICENSE](LICENSE).
