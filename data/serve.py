"""Serve data/site/ and open it.

    python data/serve.py [--port 8787]

The page also works opened straight off disk -- bundle.js is a script, not a
fetch -- so this is a convenience, not a requirement. The default port is
deliberately odd so the process is unambiguous if it ever has to be killed.
"""
import argparse
import functools
import http.server
import os
import sys
import webbrowser

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from paths import SITE_DIR  # noqa: E402


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--port", type=int, default=8787)
    ap.add_argument("--no-open", action="store_true")
    args = ap.parse_args()

    if not os.path.exists(os.path.join(SITE_DIR, "bundle.js")):
        raise SystemExit("no bundle.js -- run: python data/build.py")

    handler = functools.partial(http.server.SimpleHTTPRequestHandler,
                                directory=SITE_DIR)
    url = f"http://127.0.0.1:{args.port}/index.html"
    with http.server.ThreadingHTTPServer(("127.0.0.1", args.port), handler) as httpd:
        print(f"serving {SITE_DIR}\n  {url}\nCtrl-C to stop")
        if not args.no_open:
            webbrowser.open(url)
        httpd.serve_forever()


if __name__ == "__main__":
    main()
