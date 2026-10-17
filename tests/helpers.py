"""Local HTTP test site so tests never touch the real internet."""

import threading
from http.server import BaseHTTPRequestHandler, HTTPServer

PAGES = {
    "/": """<html><head><title> Home  Page </title>
        <meta name="description" content="A test site"></head><body>
        <h1>Welcome</h1><h2>Sub</h2><p>Hello <b>world</b></p>
        <script>var x=1;</script>
        <a href="/a">Page A</a> <a href="/a#frag">dup</a>
        <a href="/private/x">Private</a>
        <a href="http://other.invalid/z">External</a><a href="mailto:a@b.c">mail</a>
        <img src="/i.png" alt="pic">
        <table><tr><th>N</th><th>V</th></tr><tr><td>a</td><td>1</td></tr></table>
        </body></html>""",
    "/a": '<html><head><title>A</title></head><body><h1>A</h1><a href="/b">B</a></body></html>',
    "/b": "<html><head><title>B</title></head><body><h1>B</h1></body></html>",
    "/private/x": "<html><head><title>Secret</title></head></html>",
}
ROBOTS = "User-agent: *\nDisallow: /private/\n"


class Handler(BaseHTTPRequestHandler):
    hits = {}

    def do_GET(self):
        Handler.hits[self.path] = Handler.hits.get(self.path, 0) + 1
        if self.path == "/robots.txt":
            return self._send(200, ROBOTS, "text/plain")
        if self.path == "/flaky" and Handler.hits[self.path] < 2:
            return self._send(503, "busy", "text/plain")
        if self.path == "/flaky":
            return self._send(200, "<title>Recovered</title>", "text/html")
        if self.path == "/image":
            return self._send(200, "xx", "image/png")
        if self.path in PAGES:
            return self._send(200, PAGES[self.path], "text/html; charset=utf-8")
        self._send(404, "nope", "text/plain")

    def _send(self, code, body, ctype):
        data = body.encode()
        self.send_response(code)
        self.send_header("Content-Type", ctype)
        self.send_header("Content-Length", str(len(data)))
        self.end_headers()
        self.wfile.write(data)

    def log_message(self, *args):
        pass


class TestSite:
    """Context manager: `with TestSite() as base_url:`"""

    def __enter__(self):
        Handler.hits = {}
        self.server = HTTPServer(("127.0.0.1", 0), Handler)
        threading.Thread(target=self.server.serve_forever, daemon=True).start()
        return f"http://127.0.0.1:{self.server.server_port}"

    def __exit__(self, *exc):
        self.server.shutdown()
        self.server.server_close()
