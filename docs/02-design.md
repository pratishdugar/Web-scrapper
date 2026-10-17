# Phase 2 — Design

```
cli.py ──► crawler.py ──► fetcher.py   (HTTP, robots.txt, retries, rate limit)
   │            └───────► extractors.py (HTML -> dict)
   └───────► exporters.py              (dict -> json/csv/md/txt)
```

| Module | Responsibility |
|--------|----------------|
| `fetcher.py` | Normalise URLs, fetch politely, raise `FetchError` with human messages. |
| `extractors.py` | Pure function `extract(html, url, fields, selector, attr)`; no I/O. |
| `crawler.py` | Breadth-first crawl, same-domain, dedupe, depth/page limits; yields results. |
| `exporters.py` | Serialise results; CSV is a flat `page,type,value,detail` table. |
| `cli.py` | Flags, interactive wizard, progress on stderr, data on stdout. |

## Key decisions
- **Pure extraction** so it is unit-testable without network.
- **Errors per page don't abort a crawl**; they are recorded in the result.
- **Progress to stderr, data to stdout** so output can be piped.
- **Polite defaults** (robots on, 1s delay) require an explicit flag to disable.
- Generator-based crawl lets the CLI show live progress.

## Result shape
```json
{"url": "...", "status": "ok", "title": "...", "description": "...",
 "headings": [{"level": 1, "text": "..."}], "text": "...",
 "links": [{"url": "...", "text": "...", "internal": true}],
 "images": [{"url": "...", "alt": "..."}], "tables": [[["cell"]]],
 "selected": ["..."]}
```
On failure: `{"url": "...", "status": "error", "error": "message"}`.
