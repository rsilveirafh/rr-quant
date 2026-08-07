"""Pagina publica: entrega o ultimo snapshot valido salvo no Supabase."""

from __future__ import annotations

from http.server import BaseHTTPRequestHandler
from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from rrquant.storage import StorageError, obter_dashboard_mais_recente


class handler(BaseHTTPRequestHandler):
    def do_GET(self):
        try:
            dashboard = obter_dashboard_mais_recente()
        except StorageError as exc:
            self._html(503, f"<h1>Dashboard indisponivel</h1><p>{exc}</p>")
            return
        if dashboard is None:
            self._html(503, "<h1>Primeiro snapshot ainda nao foi gerado.</h1>")
            return
        self._html(200, dashboard)

    def _html(self, status: int, body: str) -> None:
        self.send_response(status)
        self.send_header("Content-Type", "text/html; charset=utf-8")
        self.send_header("Cache-Control", "no-store")
        self.end_headers()
        self.wfile.write(body.encode("utf-8"))
