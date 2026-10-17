"""Pure HTML -> data extraction (no network access)."""

from urllib.parse import urldefrag, urljoin, urlparse

from bs4 import BeautifulSoup

FIELDS = ("title", "description", "headings", "text", "links", "images", "tables")
DEFAULT_FIELDS = ("title", "description", "headings", "links")


def _clean(text):
    return " ".join(text.split())


def extract(html, url, fields=DEFAULT_FIELDS, selector=None, attr=None):
    """Extract the requested fields from HTML.

    fields   -- subset of FIELDS
    selector -- optional CSS selector; matches go to result["selected"]
    attr     -- with selector, return this attribute (e.g. "href") instead of text
    """
    soup = BeautifulSoup(html, "html.parser")
    result = {"url": url, "status": "ok"}
    host = urlparse(url).netloc

    if "title" in fields:
        result["title"] = _clean(soup.title.get_text()) if soup.title else ""
    if "description" in fields:
        tag = soup.find("meta", attrs={"name": "description"}) or \
            soup.find("meta", attrs={"property": "og:description"})
        result["description"] = _clean(tag.get("content", "")) if tag else ""
    if "headings" in fields:
        result["headings"] = [
            {"level": int(h.name[1]), "text": _clean(h.get_text())}
            for h in soup.find_all(["h1", "h2", "h3", "h4", "h5", "h6"])
            if _clean(h.get_text())
        ]
    if "links" in fields:
        result["links"] = extract_links(soup, url, host)
    if "images" in fields:
        result["images"] = [
            {"url": urljoin(url, img["src"]), "alt": _clean(img.get("alt", ""))}
            for img in soup.find_all("img", src=True)
        ]
    if "tables" in fields:
        result["tables"] = [
            [[_clean(c.get_text()) for c in row.find_all(["th", "td"])]
             for row in table.find_all("tr")]
            for table in soup.find_all("table")
        ]
    if selector:
        result["selected"] = _select(soup, selector, attr)
    if "text" in fields:  # last: it strips script/style from the soup
        for tag in soup(["script", "style", "noscript"]):
            tag.decompose()
        result["text"] = _clean(soup.get_text(" "))
    return result


def extract_links(soup, url, host=None):
    host = host or urlparse(url).netloc
    seen, links = set(), []
    for a in soup.find_all("a", href=True):
        href, _ = urldefrag(urljoin(url, a["href"].strip()))
        if urlparse(href).scheme not in ("http", "https") or href in seen:
            continue
        seen.add(href)
        links.append({"url": href, "text": _clean(a.get_text()),
                      "internal": urlparse(href).netloc == host})
    return links


def _select(soup, selector, attr):
    try:
        nodes = soup.select(selector)
    except Exception as exc:  # soupsieve raises various errors for bad selectors
        raise ValueError(f"Invalid CSS selector '{selector}': {exc}") from exc
    if attr:
        return [n[attr] for n in nodes if n.has_attr(attr)]
    return [_clean(n.get_text()) for n in nodes if _clean(n.get_text())]
