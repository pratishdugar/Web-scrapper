"""Command-line interface and interactive wizard."""

import argparse
import re
import sys
from urllib.parse import urlparse

from .crawler import crawl
from .exporters import FORMATS, export
from .extractors import DEFAULT_FIELDS, FIELDS
from .fetcher import DEFAULT_USER_AGENT, FetchError, Fetcher, normalize_url

EXAMPLES = """examples:
  python -m webscraper                      guided wizard (no arguments)
  python -m webscraper example.com          title, description, headings, links
  python -m webscraper example.com -e text,images -f md -o page.md
  python -m webscraper example.com -s "h2 a" --attr href
  python -m webscraper example.com --depth 1 --max-pages 10 -f csv -o site.csv
"""


def build_parser():
    p = argparse.ArgumentParser(
        prog="webscraper", description="Friendly, polite website scraper.",
        epilog=EXAMPLES, formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument("url", nargs="?", help="page to scrape (omit to start the wizard)")
    p.add_argument("-e", "--extract", default=",".join(DEFAULT_FIELDS),
                   help=f"comma-separated fields: {', '.join(FIELDS)} or 'all' "
                        f"(default: {','.join(DEFAULT_FIELDS)})")
    p.add_argument("-s", "--selector", help="CSS selector for custom extraction")
    p.add_argument("--attr", help="with --selector, return this attribute (e.g. href)")
    p.add_argument("-f", "--format", choices=FORMATS, default="json", help="output format")
    p.add_argument("-o", "--output", help="write to this file instead of the screen")
    p.add_argument("--depth", type=int, default=0, help="follow same-site links this deep")
    p.add_argument("--max-pages", type=int, default=10, help="crawl page limit (default 10)")
    p.add_argument("--delay", type=float, default=1.0, help="seconds between requests")
    p.add_argument("--timeout", type=float, default=15, help="request timeout in seconds")
    p.add_argument("--user-agent", default=DEFAULT_USER_AGENT)
    p.add_argument("--ignore-robots", action="store_true",
                   help="do NOT obey robots.txt (only with permission)")
    p.add_argument("-q", "--quiet", action="store_true", help="no progress messages")
    return p


def parse_fields(value):
    if value.strip().lower() == "all":
        return list(FIELDS)
    fields = [f.strip().lower() for f in value.split(",") if f.strip()]
    bad = [f for f in fields if f not in FIELDS]
    if bad:
        raise ValueError(f"Unknown field(s): {', '.join(bad)}. Choose from: {', '.join(FIELDS)}")
    return fields


def run(args, log):
    """Execute a scrape from parsed args; returns (output_text, results)."""
    fields = parse_fields(args.extract)
    if args.attr and not args.selector:
        raise ValueError("--attr needs --selector.")
    if args.depth < 0 or args.max_pages < 1:
        raise ValueError("--depth must be >= 0 and --max-pages >= 1.")
    if not fields and not args.selector:
        raise ValueError("Nothing to extract.")
    normalize_url(args.url)
    fetcher = Fetcher(args.user_agent, args.timeout, args.delay,
                      respect_robots=not args.ignore_robots)
    results = []
    for result in crawl(fetcher, args.url, fields, args.selector, args.attr,
                        args.max_pages, args.depth):
        mark = "ok " if result["status"] == "ok" else "ERR"
        detail = "" if result["status"] == "ok" else f" - {result['error']}"
        log(f"  [{mark}] {result['url']}{detail}")
        results.append(result)
    return export(results, args.format), results


def ask(prompt, default=None):
    suffix = f" [{default}]" if default is not None else ""
    answer = input(f"{prompt}{suffix}: ").strip()
    return answer or (default if default is not None else "")


def ask_int(prompt, default):
    while True:
        try:
            value = int(ask(prompt, default))
            if value >= 0:
                return value
        except ValueError:
            pass
        print("  Please enter a whole number.")


def wizard():
    print("Web Scraper — guided mode (Ctrl+C to quit)\n")
    args = build_parser().parse_args([])
    args.url = ""
    while not args.url:
        try:
            normalize_url(url := ask("Website URL"))
            args.url = url
        except FetchError as exc:
            print(f"  {exc}")
    print(f"\nAvailable data: {', '.join(FIELDS)} (or 'all')")
    while True:
        args.extract = ask("What to extract", ",".join(DEFAULT_FIELDS))
        try:
            parse_fields(args.extract)
            break
        except ValueError as exc:
            print(f"  {exc}")
    selector = ask("Custom CSS selector (blank to skip)", "")
    args.selector = selector or None
    if selector:
        args.attr = ask("Attribute to read instead of text, e.g. href (blank = text)", "") or None
    if ask("Follow links on the same site? (y/n)", "n").lower().startswith("y"):
        args.depth = ask_int("How many levels deep", 1)
        args.max_pages = ask_int("Maximum pages", 10)
    args.format = ask(f"Format ({'/'.join(FORMATS)})", "json")
    host = re.sub(r"\W+", "_", urlparse(normalize_url(args.url)).netloc)
    out = ask("Save to file (blank = print)", f"{host}.{args.format}")
    args.output = out or None
    print()
    return args


def main(argv=None):
    parser = build_parser()
    args = parser.parse_args(argv)
    log = (lambda _m: None) if args.quiet else (lambda m: print(m, file=sys.stderr))
    try:
        if not args.url:
            if not sys.stdin.isatty():
                parser.print_help()
                return 2
            args = wizard()
            log = lambda m: print(m, file=sys.stderr)
        output, results = run(args, log)
    except (ValueError, FetchError) as exc:
        print(f"Error: {exc}", file=sys.stderr)
        return 2
    except (KeyboardInterrupt, EOFError):
        print("\nCancelled.", file=sys.stderr)
        return 130

    if args.output:
        with open(args.output, "w", encoding="utf-8", newline="") as fh:
            fh.write(output)
        log(f"\nSaved {len(results)} page(s) to {args.output}")
    else:
        print(output)
    return 0 if any(r["status"] == "ok" for r in results) else 1
