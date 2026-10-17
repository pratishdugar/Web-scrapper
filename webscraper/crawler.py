"""Breadth-first, same-site crawling built on Fetcher + extract."""

from collections import deque
from urllib.parse import urldefrag, urlparse

from bs4 import BeautifulSoup

from .extractors import extract, extract_links
from .fetcher import FetchError, normalize_url


def scrape_page(fetcher, url, fields, selector=None, attr=None):
    """Fetch and extract one page. Returns (result, internal_links)."""
    try:
        final_url, html = fetcher.get(url)
        result = extract(html, final_url, fields, selector, attr)
        links = [l["url"] for l in extract_links(BeautifulSoup(html, "html.parser"),
                                                 final_url) if l["internal"]]
        return result, links
    except FetchError as exc:
        return {"url": url, "status": "error", "error": str(exc)}, []


def crawl(fetcher, start_url, fields, selector=None, attr=None,
          max_pages=1, max_depth=0):
    """Yield one result per page. max_depth=0 scrapes only start_url."""
    start = urldefrag(normalize_url(start_url))[0]
    host = urlparse(start).netloc
    queue, seen, count = deque([(start, 0)]), {start}, 0
    while queue and count < max_pages:
        url, depth = queue.popleft()
        result, links = scrape_page(fetcher, url, fields, selector, attr)
        count += 1
        yield result
        if depth < max_depth:
            for link in links:
                if link not in seen and urlparse(link).netloc == host:
                    seen.add(link)
                    queue.append((link, depth + 1))
