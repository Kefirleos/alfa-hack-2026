"""Static server for the Alfa-Business frontend.

Why a custom server instead of `python -m http.server`:
the stdlib server sends `Content-Type: text/html` with NO charset,
so the browser has to guess the encoding. In practice that guess
fails and Russian text turns into mojibake. Here every text response
is served with an explicit `charset=utf-8`, and files are always
decoded as UTF-8 (never cp1251), so the page renders correctly.
"""

import argparse
import os
import sys
from functools import partial
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path

TEXT_TYPES = {
    ".html": "text/html; charset=utf-8",
    ".htm": "text/html; charset=utf-8",
    ".js": "text/javascript; charset=utf-8",
    ".mjs": "text/javascript; charset=utf-8",
    ".css": "text/css; charset=utf-8",
    ".json": "application/json; charset=utf-8",
    ".svg": "image/svg+xml; charset=utf-8",
    ".txt": "text/plain; charset=utf-8",
    ".xml": "application/xml; charset=utf-8",
    ".webmanifest": "application/manifest+json; charset=utf-8",
}

BINARY_TYPES = {
    ".png": "image/png",
    ".jpg": "image/jpeg",
    ".jpeg": "image/jpeg",
    ".gif": "image/gif",
    ".webp": "image/webp",
    ".ico": "image/x-icon",
    ".woff": "font/woff",
    ".woff2": "font/woff2",
    ".ttf": "font/ttf",
    ".pdf": "application/pdf",
}


class Utf8Handler(SimpleHTTPRequestHandler):
    server_version = "AlfaFrontend/1.0"

    def guess_type(self, path):
        ext = Path(str(path)).suffix.lower()
        if ext in TEXT_TYPES:
            return TEXT_TYPES[ext]
        if ext in BINARY_TYPES:
            return BINARY_TYPES[ext]
        return super().guess_type(path)

    def end_headers(self):
        # no-cache: the user edits html/js and reloads the page
        self.send_header("Cache-Control", "no-store, must-revalidate")
        super().end_headers()

    def log_message(self, fmt, *args):
        sys.stdout.write("[frontend] %s\n" % (fmt % args))
        sys.stdout.flush()


def main() -> int:
    parser = argparse.ArgumentParser(description="Serve the frontend over HTTP with UTF-8.")
    parser.add_argument("--dir", default=str(Path(__file__).resolve().parent))
    parser.add_argument("--port", type=int, default=5173)
    parser.add_argument("--host", default="127.0.0.1")
    args = parser.parse_args()

    root = Path(args.dir).resolve()
    if not root.is_dir():
        print("[ERROR] Folder not found: %s" % root)
        return 1

    handler = partial(Utf8Handler, directory=str(root))
    httpd = ThreadingHTTPServer((args.host, args.port), handler)

    print("=" * 60)
    print(" Alfa-Business frontend")
    print(" Root   : %s" % root)
    print(" URL    : http://%s:%d/index.html" % (args.host, args.port))
    print(" Charset: UTF-8 (explicit, no guessing)")
    print("=" * 60)
    sys.stdout.flush()

    try:
        httpd.serve_forever()
    except KeyboardInterrupt:
        print("\n[frontend] stopped")
    finally:
        httpd.server_close()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
