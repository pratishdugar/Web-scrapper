import contextlib
import csv
import io
import json
import os
import sys
import tempfile
import unittest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from helpers import PAGES, TestSite  # noqa: E402
from webscraper import FetchError, Fetcher, crawl, export, extract  # noqa: E402
from webscraper.cli import main, parse_fields  # noqa: E402
from webscraper.fetcher import normalize_url  # noqa: E402

ALL = ["title", "description", "headings", "text", "links", "images", "tables"]


def fast(**kw):
    kw.setdefault("delay", 0)
    return Fetcher(**kw)


class ExtractTests(unittest.TestCase):  # F2, F3
    def setUp(self):
        self.r = extract(PAGES["/"], "http://x.test/", ALL, selector="h2")

    def test_title_and_description(self):
        self.assertEqual(self.r["title"], "Home Page")
        self.assertEqual(self.r["description"], "A test site")

    def test_headings(self):
        self.assertEqual(self.r["headings"][0], {"level": 1, "text": "Welcome"})

    def test_text_excludes_scripts(self):
        self.assertIn("Hello world", self.r["text"])
        self.assertNotIn("var x", self.r["text"])

    def test_links_resolved_deduped_and_filtered(self):
        urls = [l["url"] for l in self.r["links"]]
        self.assertEqual(urls.count("http://x.test/a"), 1)
        self.assertFalse(any(u.startswith("mailto") for u in urls))
        ext = [l for l in self.r["links"] if "other.invalid" in l["url"]][0]
        self.assertFalse(ext["internal"])

    def test_images_and_tables(self):
        self.assertEqual(self.r["images"], [{"url": "http://x.test/i.png", "alt": "pic"}])
        self.assertEqual(self.r["tables"], [[["N", "V"], ["a", "1"]]])

    def test_selector_text_and_attr(self):
        self.assertEqual(self.r["selected"], ["Sub"])
        r = extract(PAGES["/"], "http://x.test/", [], selector="a", attr="href")
        self.assertIn("/a", r["selected"])

    def test_bad_selector(self):
        with self.assertRaises(ValueError):
            extract("<p>x</p>", "http://x.test/", [], selector="a[[")


class FetcherTests(unittest.TestCase):  # N1, N2, N3
    def test_normalize(self):
        self.assertEqual(normalize_url("example.com"), "https://example.com")
        for bad in ("", "ftp://x.com", "http://", "not a url!!", "bad host.com"):
            with self.assertRaises(FetchError):
                normalize_url(bad)

    def test_fetch_ok(self):
        with TestSite() as base:
            url, html = fast().get(base + "/")
            self.assertIn("Welcome", html)

    def test_robots_blocks_and_override(self):
        with TestSite() as base:
            with self.assertRaisesRegex(FetchError, "robots.txt"):
                fast().get(base + "/private/x")
            self.assertIn("Secret", fast(respect_robots=False).get(base + "/private/x")[1])

    def test_retry_on_503(self):
        with TestSite() as base:
            _, html = fast().get(base + "/flaky")
            self.assertIn("Recovered", html)

    def test_http_error_message(self):
        with TestSite() as base:
            with self.assertRaisesRegex(FetchError, "404"):
                fast().get(base + "/missing")

    def test_non_html_rejected(self):
        with TestSite() as base:
            with self.assertRaisesRegex(FetchError, "Not a web page"):
                fast().get(base + "/image")

    def test_connection_error_is_friendly(self):
        with self.assertRaisesRegex(FetchError, "connect"):
            fast(retries=0, respect_robots=False, timeout=2).get("http://127.0.0.1:1/")

    def test_delay_enforced(self):
        import time
        with TestSite() as base:
            f = Fetcher(delay=0.3, respect_robots=False)
            f.get(base + "/")
            t = time.monotonic()
            f.get(base + "/a")
            self.assertGreaterEqual(time.monotonic() - t, 0.25)


class CrawlTests(unittest.TestCase):  # F4
    def titles(self, **kw):
        with TestSite() as base:
            return [r.get("title") for r in crawl(fast(), base + "/", ["title"], **kw)]

    def test_depth_zero_is_single_page(self):
        self.assertEqual(self.titles(max_pages=10, max_depth=0), ["Home Page"])

    def test_depth_one_skips_robots_blocked_and_external(self):
        titles = self.titles(max_pages=10, max_depth=1)
        self.assertEqual(titles[0], "Home Page")
        self.assertIn("A", titles)
        self.assertNotIn("B", titles)      # depth 2
        self.assertNotIn("Secret", titles)  # robots

    def test_max_pages(self):
        self.assertEqual(len(self.titles(max_pages=2, max_depth=5)), 2)

    def test_errors_do_not_abort(self):
        with TestSite() as base:
            res = list(crawl(fast(), base + "/missing", ["title"]))
            self.assertEqual(res[0]["status"], "error")


class ExportTests(unittest.TestCase):  # F5
    def setUp(self):
        self.results = [extract(PAGES["/"], "http://x.test/", ALL, selector="h2"),
                        {"url": "http://bad", "status": "error", "error": "boom"}]

    def test_json_roundtrip(self):
        self.assertEqual(json.loads(export(self.results, "json")), self.results)

    def test_csv_is_valid_and_has_error_row(self):
        rows = list(csv.reader(io.StringIO(export(self.results, "csv"))))
        self.assertEqual(rows[0], ["page", "type", "value", "detail"])
        self.assertIn(["http://bad", "error", "boom", ""], rows)

    def test_markdown_and_text(self):
        md = export(self.results, "md")
        self.assertIn("# Home Page", md)
        self.assertIn("| N | V |", md)
        self.assertIn("[title] Home Page", export(self.results, "txt"))

    def test_unknown_format(self):
        with self.assertRaises(ValueError):
            export(self.results, "xml")


class WizardTests(unittest.TestCase):  # F6
    def test_wizard_reprompts_and_runs(self):
        from unittest import mock
        with TestSite() as base, tempfile.TemporaryDirectory() as d:
            out = os.path.join(d, "w.md")
            answers = iter(["not a url!!", base + "/", "bogus", "title", "", "y", "x", "1",
                            "5", "md", out])
            with mock.patch("builtins.input", lambda _p: next(answers)), \
                    mock.patch("sys.stdin.isatty", return_value=True), \
                    contextlib.redirect_stdout(io.StringIO()) as shown, \
                    contextlib.redirect_stderr(io.StringIO()):
                code = main(["--delay", "0"])
            self.assertEqual(code, 0)
            self.assertIn("not a valid", shown.getvalue())
            self.assertIn("Unknown field", shown.getvalue())
            with open(out, encoding="utf-8") as fh:
                self.assertIn("# Home Page", fh.read())


class CliTests(unittest.TestCase):
    def run_cli(self, *argv):
        out, err = io.StringIO(), io.StringIO()
        with contextlib.redirect_stdout(out), contextlib.redirect_stderr(err):
            code = main(list(argv))
        return code, out.getvalue(), err.getvalue()

    def test_stdout_json(self):
        with TestSite() as base:
            code, out, _ = self.run_cli(base + "/", "--delay", "0", "-q")
        self.assertEqual(code, 0)
        self.assertEqual(json.loads(out)[0]["title"], "Home Page")

    def test_output_file_and_progress(self):
        with TestSite() as base, tempfile.TemporaryDirectory() as d:
            path = os.path.join(d, "o.csv")
            code, _, err = self.run_cli(base + "/", "--delay", "0", "-f", "csv", "-o", path)
            self.assertEqual(code, 0)
            self.assertIn("Saved 1 page", err)
            with open(path, encoding="utf-8") as fh:
                self.assertIn("Home Page", fh.read())

    def test_friendly_errors_no_traceback(self):
        for argv in (["x.com", "-e", "bogus"], ["x.com", "--attr", "href"],
                     ["x.com", "--depth", "-1"]):
            code, _, err = self.run_cli(*argv)
            self.assertEqual(code, 2)
            self.assertTrue(err.startswith("Error:"), err)

    def test_failed_scrape_exit_code(self):
        with TestSite() as base:
            code, _, _ = self.run_cli(base + "/missing", "--delay", "0", "-q")
        self.assertEqual(code, 1)

    def test_parse_fields_all(self):
        self.assertEqual(len(parse_fields("all")), 7)


if __name__ == "__main__":
    unittest.main()
