# Web Scraper

A friendly, polite website scraper for Python. Run it with no arguments for a
guided wizard, or use flags for scripting. Built following an ADLC
(application development life cycle) flow — see [`docs/`](docs).

## Install
```bash
pip install -r requirements.txt   # requests + beautifulsoup4, Python 3.9+
```

## Quick start
```bash
python -m webscraper                       # guided wizard: answers a few questions
python -m webscraper example.com           # title, description, headings, links as JSON
python -m webscraper example.com -e text,images -f md -o page.md
python -m webscraper example.com -s "h2 a" --attr href          # custom CSS selector
python -m webscraper example.com --depth 1 --max-pages 10 -f csv -o site.csv
```
Progress goes to stderr and data to stdout, so `python -m webscraper site.com -q | jq` works.

| Option | Meaning |
|--------|---------|
| `-e, --extract` | `title,description,headings,text,links,images,tables` or `all` |
| `-s, --selector` / `--attr` | CSS selector; optionally read an attribute (e.g. `href`) |
| `-f, --format` | `json` (default), `csv`, `md`, `txt` |
| `-o, --output` | write to a file |
| `--depth`, `--max-pages` | same-site crawl limits (default: single page / 10 pages) |
| `--delay`, `--timeout` | seconds between requests (1.0) / request timeout (15) |
| `--ignore-robots` | skip robots.txt — only with the site owner's permission |

Exit codes: `0` at least one page scraped, `1` all pages failed, `2` bad input.

## Use as a library
```python
from webscraper import Fetcher, crawl, export
results = list(crawl(Fetcher(), "example.com", ["title", "links"], max_pages=5, max_depth=1))
print(export(results, "csv"))
```

## Being a good citizen
Defaults obey `robots.txt`, wait 1s between requests, retry with backoff, cap
pages at 5 MB and identify themselves. Check a site's terms before scraping.
JavaScript-rendered content is not supported.

## Tests
```bash
python -m unittest discover -s tests -v    # offline: uses a local HTTP server
```

## ADLC artifacts
1. [Requirements](docs/01-requirements.md) 2. [Design](docs/02-design.md)
3. Build: `webscraper/` 4. [Test report](docs/04-test-report.md)
5. Deploy/maintain: this README, `requirements.txt`
