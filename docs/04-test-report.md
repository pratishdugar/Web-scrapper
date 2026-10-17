# Phase 4 — Test report

Run: `python -m unittest discover -s tests -v` — 29 tests, all passing, fully offline.

| Requirement | Covered by |
|-------------|-----------|
| F1 URL handling | `FetcherTests.test_normalize`, `test_fetch_ok` |
| F2 extraction | `ExtractTests.*` |
| F3 selector/attr | `test_selector_text_and_attr`, `test_bad_selector` |
| F4 crawl | `CrawlTests.*` (depth, limit, external/robots skipped, errors don't abort) |
| F5 export | `ExportTests.*`, `CliTests.test_output_file_and_progress` |
| F6 wizard | `WizardTests.test_wizard_reprompts_and_runs` |
| N1 politeness | `test_robots_blocks_and_override`, `test_delay_enforced` |
| N2 resilience | `test_retry_on_503`, `test_non_html_rejected` |
| N3 friendly errors | `test_http_error_message`, `test_connection_error_is_friendly`, `test_friendly_errors_no_traceback` |

## Defects found during verification (fixed)
- `"not a url!!"` was accepted as a valid host → stricter URL validation.
- Wizard aborted on an invalid field or non-numeric depth → now re-prompts.

## Known limitations
No JavaScript rendering; live-internet behaviour was not exercised in CI
(sandbox blocks external hosts) — only the local test server.
