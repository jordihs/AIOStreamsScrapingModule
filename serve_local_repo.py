#!/usr/bin/env python3
"""
Serve local-repo/ over HTTP so Kodi's repository engine can fetch its
addons.xml/checksum/zips - see build.py's build_local_repo(). Kodi's fetch
mechanism didn't work against local-repo/ as a bare path or a file:// URI on
this setup (repository install succeeded, but "Install from repository"
failed with "Could not connect to repository"); serving over HTTP reuses the
exact mechanism already proven to work against GitHub Pages.

Usage: run this, leave it running, then in Kodi use Install from repository
against the local repository addon. Ctrl+C to stop.
"""
import http.server
import socketserver

import build

DIRECTORY = build.LOCAL_REPO_DIR
PORT = build.LOCAL_REPO_HTTP_PORT


class Handler(http.server.SimpleHTTPRequestHandler):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, directory=str(DIRECTORY), **kwargs)

    def log_message(self, format, *args):
        pass  # keep the console output to just the startup line below


if __name__ == "__main__":
    if not DIRECTORY.is_dir():
        raise SystemExit(f"{DIRECTORY} does not exist yet - run build.py first.")

    with socketserver.TCPServer(("127.0.0.1", PORT), Handler) as httpd:
        print(f"Serving {DIRECTORY} at http://127.0.0.1:{PORT}/ - Ctrl+C to stop")
        try:
            httpd.serve_forever()
        except KeyboardInterrupt:
            pass
