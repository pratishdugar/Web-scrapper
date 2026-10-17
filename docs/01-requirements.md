# Phase 1 — Requirements

## Problem
Non-experts need to pull useful data out of web pages without writing code,
and without accidentally hammering or violating a site.

## Users
- **Casual user**: runs a guided wizard, gets a file.
- **Power user / scripter**: one-line CLI with flags; imports the library.

## Functional requirements
| ID | Requirement |
|----|-------------|
| F1 | Scrape a single URL (scheme optional: `example.com` works). |
| F2 | Extract: title, meta description, headings, text, links, images, tables. |
| F3 | Extract custom data with a CSS selector (text or an attribute). |
| F4 | Optional crawl of same-site links with depth and page limits. |
| F5 | Export to JSON, CSV, Markdown or plain text; stdout or file. |
| F6 | Interactive wizard when run with no arguments. |

## Non-functional requirements
| ID | Requirement |
|----|-------------|
| N1 | Polite by default: obeys robots.txt, per-host delay, identifies itself. |
| N2 | Resilient: timeouts, retries with backoff, size cap. |
| N3 | Friendly errors: plain-language messages, no tracebacks for expected failures. |
| N4 | Minimal dependencies (`requests`, `beautifulsoup4`). |
| N5 | Fully testable offline (tests use a local HTTP server). |

## Out of scope
JavaScript rendering, login/CAPTCHA handling, proxies.

## Acceptance criteria
Each F/N item has a matching test in `tests/` (see `docs/04-test-report.md`).
