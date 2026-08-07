"""Endpoint protegido, chamado diariamente pelo Vercel Cron."""

from __future__ import annotations

from http.server import BaseHTTPRequestHandler
from pathlib import Path
import hmac
import os
import sys

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from rrquant.generate import gerar_dashboard
from rrquant.storage import salvar_snapshot


class handler(BaseHTTPRequestHandler):
    def do_GET(self):
        secret = os.getenv("CRON_SECRET")
        authorization = self.headers.get("Authorization", "")
        if not secret or not hmac.compare_digest(authorization, f"Bearer {secret}"):
            self._json(401, '{"error":"unauthorized"}')
            return
        try:
            dashboard = gerar_dashboard()
            salvar_snapshot(dashboard.html, dashboard.market_date)
        except Exception as exc:
            self._json(500, '{"error":"refresh_failed"}')
            print(f"refresh failed: {exc}")
            return
        self._json(200, '{"ok":true,"market_date":"%s"}' % (dashboard.market_date or ""))

    def _json(self, status: int, body: str) -> None:
        self.send_response(status)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.end_headers()
        self.wfile.write(body.encode("utf-8"))
