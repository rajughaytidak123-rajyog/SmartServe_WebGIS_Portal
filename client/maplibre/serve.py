"""
SmartServe GIS - MapLibre Vector Frontend HTTP Server Launcher
Serves the MapLibre GL JS vector portal on http://127.0.0.1:5600
Directly routes /data/ requests to the project root data/ directory.
Full RFC 7233 HTTP Range Request Support for PMTiles v3 archives.
"""

import http.server
import socketserver
import os
import sys
import webbrowser
from urllib.parse import urlparse, unquote, urlunparse

PORT = 5600
CLIENT_DIR = os.path.dirname(os.path.abspath(__file__))
PROJECT_ROOT = os.path.abspath(os.path.join(CLIENT_DIR, "..", ".."))
DATA_DIR = os.path.join(PROJECT_ROOT, "data")

class RangeFileWrapper:
    """Wraps an open file to read only a specified byte range."""
    def __init__(self, f, length):
        self.f = f
        self.remaining = length

    def read(self, size=-1):
        if self.remaining <= 0:
            return b""
        if size < 0 or size > self.remaining:
            size = self.remaining
        data = self.f.read(size)
        self.remaining -= len(data)
        return data

    def close(self):
        self.f.close()

class MapLibreHandler(http.server.SimpleHTTPRequestHandler):
    def translate_path(self, path):
        # Parse URL path
        parsed_path = unquote(urlparse(path).path)
        
        # Route /data/... to project root data/ directory
        if parsed_path.startswith("/data/"):
            rel_path = parsed_path[6:] # strip /data/
            return os.path.join(DATA_DIR, rel_path.replace("/", os.sep))
        
        # Otherwise serve from client/maplibre/
        rel_path = parsed_path.lstrip("/")
        if not rel_path:
            return os.path.join(CLIENT_DIR, "index.html")
        return os.path.join(CLIENT_DIR, rel_path.replace("/", os.sep))

    def guess_type(self, path):
        if path.endswith(".geojson") or path.endswith(".json"):
            return "application/json"
        if path.endswith(".pbf") or path.endswith(".mvt"):
            return "application/x-protobuf"
        if path.endswith(".pmtiles"):
            return "application/octet-stream"
        return super().guess_type(path)

    def send_head(self):
        """Handle GET/HEAD with support for HTTP Range requests (RFC 7233)."""
        path = self.translate_path(self.path)
        if os.path.isdir(path):
            parts = urlparse(self.path)
            if not parts.path.endswith('/'):
                self.send_response(301)
                new_parts = (parts[0], parts[1], parts[2] + '/', parts[3], parts[4], parts[5])
                new_url = urlunparse(new_parts)
                self.send_header("Location", new_url)
                self.end_headers()
                return None
            for index in "index.html", "index.htm":
                index_path = os.path.join(path, index)
                if os.path.exists(index_path):
                    path = index_path
                    break
            else:
                return super().send_head()

        ctype = self.guess_type(path)
        try:
            f = open(path, 'rb')
        except OSError:
            self.send_error(404, "File not found")
            return None

        fs = os.fstat(f.fileno())
        total_len = fs[6]

        range_header = self.headers.get("Range")
        if range_header and range_header.startswith("bytes="):
            try:
                ranges = range_header[6:].split("-")
                start = int(ranges[0]) if ranges[0] else 0
                end = int(ranges[1]) if len(ranges) > 1 and ranges[1] else total_len - 1
                if start >= total_len or end >= total_len or start > end:
                    self.send_error(416, "Requested Range Not Satisfiable")
                    f.close()
                    return None
                
                length = end - start + 1
                self.send_response(206)
                self.send_header("Content-Type", ctype)
                self.send_header("Content-Range", f"bytes {start}-{end}/{total_len}")
                self.send_header("Content-Length", str(length))
                self.send_header("Accept-Ranges", "bytes")
                self.send_header("Last-Modified", self.date_time_string(fs.st_mtime))
                self.end_headers()
                f.seek(start)
                return RangeFileWrapper(f, length)
            except Exception:
                pass

        self.send_response(200)
        self.send_header("Content-Type", ctype)
        self.send_header("Content-Length", str(total_len))
        self.send_header("Accept-Ranges", "bytes")
        self.send_header("Last-Modified", self.date_time_string(fs.st_mtime))
        self.end_headers()
        return f

    def end_headers(self):
        # Enable CORS and disable cache during development
        self.send_header('Access-Control-Allow-Origin', '*')
        self.send_header('Access-Control-Allow-Methods', 'GET, OPTIONS')
        self.send_header('Access-Control-Allow-Headers', '*')
        self.send_header('Cache-Control', 'no-store, no-cache, must-revalidate')
        super().end_headers()

def main():
    print("=" * 70)
    print("  SMARTSERVE GIS - MAPLIBRE GL JS VECTOR CLIENT")
    print("  Pune Municipal Corporation (PMC) - Vector Engine (Port 5600)")
    print("  Featuring Native HTTP Range Support for PMTiles v3 Archives")
    print("=" * 70)
    print(f"\n[INFO] Client Directory : {CLIENT_DIR}")
    print(f"[INFO] Data Directory   : {DATA_DIR}")
    print(f"[SUCCESS] Vector Portal URL: http://127.0.0.1:{PORT}")
    print(f"[INFO] Ensure Vector Tile Server is running: http://127.0.0.1:7800")
    print(f"[INFO] Ensure FastAPI Backend is running  : http://127.0.0.1:8000")
    print("\n👉 Press Ctrl + C to stop the MapLibre frontend server.\n")

    socketserver.TCPServer.allow_reuse_address = True
    with socketserver.TCPServer(("", PORT), MapLibreHandler) as httpd:
        try:
            httpd.serve_forever()
        except KeyboardInterrupt:
            print("\n[INFO] Shutting down MapLibre server.")
            sys.exit(0)

if __name__ == "__main__":
    main()
