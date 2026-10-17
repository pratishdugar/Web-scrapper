"""Polite HTTP fetching: robots.txt, rate limiting, retries, friendly errors."""

import re
import time
from urllib import robotparser
from urllib.parse import urlparse

import requests

DEFAULT_USER_AGENT = "WebScraperBot/1.0 (+educational; respects robots.txt)"
MAX_BYTES = 5 * 1024 * 1024


class FetchError(Exception):
    """A fetch failed; the message is safe to show to end users."""


def normalize_url(url):
    """Add https:// when missing and validate the result."""
    url = (url or "").strip()
    if not url:
        raise FetchError("Please provide a URL.")
    if "://" not in url:
        url = "https://" + url
    parsed = urlparse(url)
    host = parsed.hostname or ""
    if (parsed.scheme not in ("http", "https") or not host
            or re.search(r"\s", url) or not re.fullmatch(r"[A-Za-z0-9.\-_:\[\]]+", host)):
        raise FetchError(f"'{url}' is not a valid http(s) URL.")
    return url


class Fetcher:
    def __init__(self, user_agent=DEFAULT_USER_AGENT, timeout=15, delay=1.0,
                 retries=2, respect_robots=True):
        self.user_agent = user_agent
        self.timeout = timeout
        self.delay = delay
        self.retries = retries
        self.respect_robots = respect_robots
        self._session = requests.Session()
        self._session.headers["User-Agent"] = user_agent
        self._robots = {}
        self._last_request = {}

    def allowed(self, url):
        if not self.respect_robots:
            return True
        parsed = urlparse(url)
        origin = f"{parsed.scheme}://{parsed.netloc}"
        if origin not in self._robots:
            parser = robotparser.RobotFileParser()
            try:
                resp = self._session.get(origin + "/robots.txt", timeout=self.timeout)
                if resp.status_code == 200:
                    parser.parse(resp.text.splitlines())
                elif resp.status_code in (401, 403):
                    parser.disallow_all = True
                else:
                    parser.parse([])  # no robots.txt -> everything allowed
            except requests.RequestException:
                parser.parse([])
            self._robots[origin] = parser
        return self._robots[origin].can_fetch(self.user_agent, url)

    def _wait(self, host):
        elapsed = time.monotonic() - self._last_request.get(host, 0)
        if elapsed < self.delay:
            time.sleep(self.delay - elapsed)
        self._last_request[host] = time.monotonic()

    def get(self, url):
        """Return (final_url, html). Raises FetchError with a readable message."""
        url = normalize_url(url)
        if not self.allowed(url):
            raise FetchError("Blocked by the site's robots.txt (use --ignore-robots "
                             "only if you have permission).")
        host = urlparse(url).netloc
        last_error = None
        for attempt in range(self.retries + 1):
            self._wait(host)
            try:
                resp = self._session.get(url, timeout=self.timeout, stream=True)
            except requests.exceptions.Timeout:
                last_error = f"The site did not respond within {self.timeout}s."
            except requests.exceptions.SSLError:
                raise FetchError("Secure connection (SSL) failed for this site.")
            except requests.exceptions.ConnectionError:
                last_error = "Could not connect. Check the address and your internet connection."
            except requests.RequestException as exc:
                raise FetchError(f"Request failed: {exc}")
            else:
                if resp.status_code in (429, 500, 502, 503, 504) and attempt < self.retries:
                    last_error = f"Server returned {resp.status_code}."
                    resp.close()
                elif resp.status_code >= 400:
                    resp.close()
                    raise FetchError(f"Server returned HTTP {resp.status_code}.")
                else:
                    return self._read(resp)
            if attempt < self.retries:
                time.sleep(min(2 ** attempt, 5))
        raise FetchError(last_error or "Unknown network error.")

    @staticmethod
    def _read(resp):
        ctype = resp.headers.get("Content-Type", "")
        if ctype and "html" not in ctype and "xml" not in ctype and "text" not in ctype:
            resp.close()
            raise FetchError(f"Not a web page (content type: {ctype.split(';')[0]}).")
        body = b""
        for chunk in resp.iter_content(65536):
            body += chunk
            if len(body) > MAX_BYTES:
                resp.close()
                raise FetchError("Page is larger than 5 MB; skipped.")
        encoding = resp.encoding if "charset" in ctype.lower() else None
        return resp.url, body.decode(encoding or "utf-8", errors="replace")
