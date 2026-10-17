"""A friendly, polite web scraper."""

from .crawler import crawl, scrape_page
from .exporters import export
from .extractors import extract
from .fetcher import FetchError, Fetcher

__all__ = ["crawl", "scrape_page", "export", "extract", "FetchError", "Fetcher"]
__version__ = "1.0.0"
