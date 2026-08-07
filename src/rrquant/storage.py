"""Persistencia do dashboard no Supabase via REST, sem dependencia extra."""

from __future__ import annotations

import json
import os
import urllib.error
import urllib.request


class StorageError(RuntimeError):
    pass


def _config() -> tuple[str, str]:
    url = os.getenv("SUPABASE_URL", "").rstrip("/")
    key = os.getenv("SUPABASE_SECRET_KEY", "")
    if not url or not key:
        raise StorageError("SUPABASE_URL e SUPABASE_SECRET_KEY precisam estar configuradas.")
    return url, key


def _request(method: str, path: str, body: bytes | None = None) -> bytes:
    url, key = _config()
    request = urllib.request.Request(
        f"{url}/rest/v1/{path}", data=body, method=method,
        headers={"apikey": key, "Content-Type": "application/json"},
    )
    try:
        with urllib.request.urlopen(request, timeout=20) as response:
            return response.read()
    except urllib.error.HTTPError as exc:
        detail = exc.read().decode("utf-8", errors="replace")
        raise StorageError(f"Supabase respondeu {exc.code}: {detail}") from exc
    except urllib.error.URLError as exc:
        raise StorageError(f"Nao foi possivel acessar o Supabase: {exc.reason}") from exc


def salvar_snapshot(dashboard_html: str, market_date: str | None) -> None:
    payload = json.dumps([{
        "dashboard_html": dashboard_html,
        "market_date": market_date,
    }]).encode("utf-8")
    _request("POST", "snapshots", payload)


def obter_dashboard_mais_recente() -> str | None:
    raw = _request(
        "GET", "snapshots?select=dashboard_html&order=generated_at.desc&limit=1",
    )
    rows = json.loads(raw)
    return rows[0]["dashboard_html"] if rows else None
