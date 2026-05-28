# -*- coding: utf-8 -*-
"""
Built-in HTTP server for rendering military symbols on demand.

The server runs in a **daemon thread** inside the KADAS process and
listens on ``127.0.0.1:<port>`` (port chosen automatically from a free
OS port).

Design inspired by the dufour-app milsymbol-server, adapted for a
pure-Python / Qt environment without a Node.js dependency.

Key features
------------
* Support for **both** APP-6D (20-char) and MIL-STD-2525C (15-char) SIDCs
* SVG and PNG output with **Cache-Control** headers (24 h)
* **Dimension-aware** frame shapes (air, sea, subsurface)
* Mobility, towed-array, and operational-condition modifiers
* All milsymbol-compatible query parameters
* **Batch rendering** via POST ``/batch``
* **Stats tracking** + enhanced ``/health`` endpoint
* LRU caching in the renderer for frequently requested symbols

Endpoints
---------
``GET /symbol/<SIDC>.svg``
    Returns the SVG rendering of the given SIDC (20 or 15 chars).

``GET /symbol/<SIDC>.svg?designation=TEXT&higher_formation=TEXT``
    Same as above with text amplifiers.

``GET /symbol/<SIDC>.svg?size=100&condition=damaged``
    With optional size and operational-condition overlay.

``GET /symbol/<SIDC>.png``
``GET /symbol/<SIDC>.png?size=64``
    Returns a PNG bitmap rendered via Qt's ``QSvgRenderer``.

``POST /batch``
    Accepts a JSON body ``[{sidc, fmt, size, designation, ...}, ...]``
    and returns a JSON array of rendered results (base64-encoded).

``GET /health``
    Returns JSON status with server stats and configuration.

``GET /catalog``
    Returns the full symbol catalog as JSON.

All responses include permissive CORS headers and 24-hour cache hints.
"""

from __future__ import annotations

import base64
import json
import re
import socket
import threading
import time
from http.server import HTTPServer, BaseHTTPRequestHandler
from typing import Optional
from urllib.parse import urlparse, parse_qs

from ..logger import get_logger

LOG = get_logger("kadas_milsymb.server")


# ======================================================================
# Stats tracker (inspired by dufour-app)
# ======================================================================

class _Stats:
    """Thread-safe request statistics."""

    def __init__(self):
        self.start_time = time.time()
        self.requests = 0
        self.svg_rendered = 0
        self.png_rendered = 0
        self.batch_rendered = 0
        self.cache_hits = 0
        self.errors = 0
        self._lock = threading.Lock()

    def inc(self, attr: str, n: int = 1):
        with self._lock:
            setattr(self, attr, getattr(self, attr) + n)

    def snapshot(self) -> dict:
        with self._lock:
            return {
                "uptime_seconds": int(time.time() - self.start_time),
                "total_requests": self.requests,
                "svg_rendered": self.svg_rendered,
                "png_rendered": self.png_rendered,
                "batch_rendered": self.batch_rendered,
                "cache_hits": self.cache_hits,
                "errors": self.errors,
            }


_stats = _Stats()


# ======================================================================
# SIDC pattern for URL matching (both APP-6D and 2525C)
# ======================================================================

# APP-6D: 20 alphanumeric  |  2525C: 10-15 chars with dashes/asterisks
_SIDC_URL_RE = re.compile(
    r"^/symbol/([A-Za-z0-9\-\*]{10,20})\.(svg|png)$"
)


# ======================================================================
# Request handler
# ======================================================================

class _SymbolHandler(BaseHTTPRequestHandler):
    """Handle incoming symbol requests."""

    # Silence default stderr logging – we use our own logger
    def log_message(self, fmt, *args):  # noqa: D401
        LOG.debug(fmt, *args)

    # ------------------------------------------------------------------

    def do_OPTIONS(self):  # noqa: N802
        """Handle CORS preflight."""
        self.send_response(204)
        self._cors_headers()
        self.end_headers()

    def do_GET(self):  # noqa: N802
        _stats.inc("requests")
        parsed = urlparse(self.path)
        path = parsed.path.rstrip("/")
        qs = parse_qs(parsed.query)

        if path == "/health":
            self._serve_health()
            return

        if path == "/catalog":
            self._serve_catalog()
            return

        # /symbol/<SIDC>.svg  or  /symbol/<SIDC>.png
        m = _SIDC_URL_RE.match(path)
        if m:
            sidc = m.group(1)
            fmt = m.group(2)

            # Parse query parameters (milsymbol-compatible names)
            designation = (
                qs.get("designation", qs.get("uniqueDesignation", [""]))[0]
            )
            higher = (
                qs.get("higher_formation", qs.get("higherFormation", [""]))[0]
            )
            condition = qs.get("condition", [""])[0]

            if fmt == "svg":
                size = int(qs.get("size", ["0"])[0]) or None
                self._serve_svg(sidc, designation, higher, condition, size)
            else:
                size = int(qs.get("size", ["64"])[0])
                self._serve_png(sidc, size, designation, higher, condition)
            return

        self._error(404, "Not found")

    def do_POST(self):  # noqa: N802
        _stats.inc("requests")
        parsed = urlparse(self.path)
        path = parsed.path.rstrip("/")

        if path == "/batch":
            self._serve_batch()
            return

        self._error(404, "Not found")

    # ------------------------------------------------------------------
    # Renderers
    # ------------------------------------------------------------------

    def _serve_svg(
        self,
        sidc: str,
        designation: str,
        higher: str,
        condition: str,
        size: Optional[int] = None,
    ):
        from ..core.sidc import validate_sidc
        from ..symbology.renderer import render_symbol

        # Validate SIDC
        validation = validate_sidc(sidc)
        if not validation.valid:
            _stats.inc("errors")
            self._error(400, validation.error)
            return

        try:
            svg = render_symbol(
                sidc, designation, higher,
                size=size,
                operational_condition=condition,
            )
            _stats.inc("svg_rendered")
            self._response(
                200, "image/svg+xml", svg.encode("utf-8"),
                cache=True,
                extra_headers={
                    "X-SIDC-Format": validation.format,
                },
            )
        except ValueError as exc:
            _stats.inc("errors")
            self._error(400, str(exc))

    def _serve_png(
        self,
        sidc: str,
        size: int,
        designation: str,
        higher: str,
        condition: str,
    ):
        from ..core.sidc import validate_sidc
        from ..symbology.renderer import render_symbol_png

        validation = validate_sidc(sidc)
        if not validation.valid:
            _stats.inc("errors")
            self._error(400, validation.error)
            return

        try:
            data = render_symbol_png(
                sidc, size, designation, higher,
                operational_condition=condition,
            )
            if data is None:
                _stats.inc("errors")
                self._error(
                    501,
                    "PNG rendering unavailable (Qt SVG module not found)",
                )
                return
            _stats.inc("png_rendered")
            self._response(
                200, "image/png", data,
                cache=True,
                extra_headers={
                    "X-SIDC-Format": validation.format,
                },
            )
        except ValueError as exc:
            _stats.inc("errors")
            self._error(400, str(exc))

    def _serve_batch(self):
        """Handle POST /batch – render multiple symbols at once."""
        from ..core.sidc import validate_sidc
        from ..symbology.renderer import render_symbol, render_symbol_png

        content_length = int(self.headers.get("Content-Length", 0))
        if content_length == 0:
            _stats.inc("errors")
            self._error(400, "Empty request body")
            return

        try:
            body = self.rfile.read(content_length)
            symbols = json.loads(body)
        except (json.JSONDecodeError, UnicodeDecodeError) as exc:
            _stats.inc("errors")
            self._error(400, f"Invalid JSON: {exc}")
            return

        if not isinstance(symbols, list):
            _stats.inc("errors")
            self._error(400, "Request body must be a JSON array")
            return

        results = []
        for sym in symbols:
            sidc = sym.get("sidc", sym.get("SIDC", ""))
            fmt = sym.get("fmt", sym.get("format", "svg")).lower()
            size = int(sym.get("size", 64))
            designation = sym.get("designation", sym.get("uniqueDesignation", ""))
            higher = sym.get("higher_formation", sym.get("higherFormation", ""))
            condition = sym.get("condition", "")

            validation = validate_sidc(sidc)
            if not validation.valid:
                results.append({"sidc": sidc, "error": validation.error})
                continue

            try:
                if fmt == "png":
                    data = render_symbol_png(
                        sidc, size, designation, higher,
                        operational_condition=condition,
                    )
                    if data is None:
                        results.append({
                            "sidc": sidc,
                            "error": "PNG rendering unavailable",
                        })
                        continue
                    results.append({
                        "sidc": sidc,
                        "content": base64.b64encode(data).decode("utf-8"),
                        "content_type": "image/png",
                        "format": validation.format,
                    })
                else:
                    svg = render_symbol(
                        sidc, designation, higher,
                        size=size if size != 64 else None,
                        operational_condition=condition,
                    )
                    results.append({
                        "sidc": sidc,
                        "content": base64.b64encode(
                            svg.encode("utf-8")
                        ).decode("utf-8"),
                        "content_type": "image/svg+xml",
                        "format": validation.format,
                    })
            except Exception as exc:
                results.append({"sidc": sidc, "error": str(exc)})

        _stats.inc("batch_rendered", len(results))
        self._json_response(results)

    def _serve_health(self):
        from ..symbology.renderer import cached_svg, cached_png

        stats = _stats.snapshot()
        svg_cache = cached_svg.cache_info()
        png_cache = cached_png.cache_info()

        payload = {
            "status": "ok",
            "service": "kadas-app6-server",
            "version": "0.2.0",
            "supported_formats": ["SVG", "PNG"],
            "supported_sidc": [
                "APP-6D (20 alphanumeric chars)",
                "MIL-STD-2525C (10-15 chars with dashes)",
            ],
            "dimension_frames": True,
            "stats": stats,
            "cache": {
                "svg": {
                    "size": svg_cache.currsize,
                    "max_size": svg_cache.maxsize,
                    "hits": svg_cache.hits,
                    "misses": svg_cache.misses,
                },
                "png": {
                    "size": png_cache.currsize,
                    "max_size": png_cache.maxsize,
                    "hits": png_cache.hits,
                    "misses": png_cache.misses,
                },
            },
            "usage": {
                "svg_app6d": "GET /symbol/10031000001211000000.svg",
                "svg_2525c": "GET /symbol/SFG-UCI---.svg",
                "png_with_modifiers": (
                    "GET /symbol/SFG-UCI---.png?"
                    "designation=BA01&size=80"
                ),
                "batch": (
                    'POST /batch  body: [{"sidc":"10031000001211000000",'
                    '"fmt":"svg"}]'
                ),
            },
        }
        self._json_response(payload)

    def _serve_catalog(self):
        from ..symbology.catalog_data import ALL_ENTRIES, SYMBOL_SET_NAMES
        payload = {
            "symbol_sets": SYMBOL_SET_NAMES,
            "entries": [
                {
                    "symbol_set": e.symbol_set,
                    "entity_code": e.entity_code,
                    "name": e.name,
                    "name_de": e.name_de,
                    "category": e.category,
                    "sidc": e.sidc_template(),
                }
                for e in ALL_ENTRIES
            ],
        }
        self._json_response(payload)

    # ------------------------------------------------------------------
    # Response helpers
    # ------------------------------------------------------------------

    def _response(
        self,
        code: int,
        content_type: str,
        body: bytes,
        cache: bool = False,
        extra_headers: Optional[dict] = None,
    ):
        self.send_response(code)
        self.send_header("Content-Type", content_type)
        self.send_header("Content-Length", str(len(body)))
        if cache:
            # 24-hour browser/CDN cache (matches dufour-app pattern)
            self.send_header("Cache-Control", "public, max-age=86400")
        self._cors_headers()
        if extra_headers:
            for k, v in extra_headers.items():
                self.send_header(k, v)
        self.end_headers()
        self.wfile.write(body)

    def _json_response(self, obj, code: int = 200):
        body = json.dumps(obj, ensure_ascii=False).encode("utf-8")
        self._response(code, "application/json", body)

    def _error(self, code: int, message: str):
        self._json_response({"error": message}, code)

    def _cors_headers(self):
        self.send_header("Access-Control-Allow-Origin", "*")
        self.send_header("Access-Control-Allow-Methods", "GET, POST, OPTIONS")
        self.send_header("Access-Control-Allow-Headers", "Content-Type, *")


# ======================================================================
# Server wrapper
# ======================================================================

_PREFERRED_PORT = 2525


def _find_free_port() -> int:
    """Try port 2525 first; fall back to a free OS port."""
    for port in (_PREFERRED_PORT, 0):
        try:
            with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
                s.bind(("127.0.0.1", port))
                chosen = s.getsockname()[1]
                return chosen
        except OSError:
            continue
    # Should never get here, but just in case
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        s.bind(("127.0.0.1", 0))
        return s.getsockname()[1]


class SymbolServer:
    """Lightweight HTTP server running in a daemon thread.

    Usage::

        srv = SymbolServer()
        srv.start()              # non-blocking
        print(srv.base_url)      # e.g. "http://127.0.0.1:2525"
        ...
        srv.stop()
    """

    def __init__(self, port: int = 0):
        self._port = port or _find_free_port()
        self._httpd: Optional[HTTPServer] = None
        self._thread: Optional[threading.Thread] = None

    @property
    def port(self) -> int:
        return self._port

    @property
    def base_url(self) -> str:
        return f"http://127.0.0.1:{self._port}"

    def symbol_url(self, sidc: str, fmt: str = "svg") -> str:
        """Return the full URL for a symbol (APP-6D or 2525C)."""
        return f"{self.base_url}/symbol/{sidc}.{fmt}"

    @property
    def stats(self) -> dict:
        """Return current server statistics."""
        return _stats.snapshot()

    def start(self) -> None:
        """Start serving in a background daemon thread."""
        if self._httpd is not None:
            return

        self._httpd = HTTPServer(("127.0.0.1", self._port), _SymbolHandler)
        self._thread = threading.Thread(
            target=self._httpd.serve_forever,
            name="KadasApp6-SymbolServer",
            daemon=True,
        )
        self._thread.start()
        LOG.info("Symbol server listening on %s", self.base_url)

    def stop(self) -> None:
        """Shut down the server."""
        if self._httpd is not None:
            self._httpd.shutdown()
            self._httpd.server_close()
            self._httpd = None
            self._thread = None
            LOG.info("Symbol server stopped")
