"""Guardado en Supabase (plan gratuito) mediante su API REST."""
from __future__ import annotations

import json
import os
from datetime import datetime, timedelta, timezone

import requests

PAGE = 1000

# Columnas con los datos "en bruto" de cada oferta (permiten re-evaluarla si
# cambian los criterios) más las de control.
RAW_COLUMNS = ("id,title,company,description,published_at,links,sources,raw_location,raw_salary,"
               "raw_contract,raw_workday,raw_modality,raw_experience,sector_hint,company_sectors,"
               "default_location,location_prefiltered,implicit_fulltime,requirements_text,"
               "first_seen,last_seen,aviso,passes,config_hash")


class Storage:
    def __init__(self, url: str | None = None, key: str | None = None):
        self.url = (url or os.environ.get("SUPABASE_URL", "")).rstrip("/")
        self.key = key or os.environ.get("SUPABASE_SECRET_KEY", "")
        if not self.url or not self.key:
            raise RuntimeError("Faltan SUPABASE_URL o SUPABASE_SECRET_KEY (secretos de GitHub).")
        self.s = requests.Session()
        headers = {"apikey": self.key, "Content-Type": "application/json"}
        # Las claves nuevas (sb_secret_...) no son JWT: solo van en 'apikey'.
        if not self.key.startswith("sb_"):
            headers["Authorization"] = f"Bearer {self.key}"
        self.s.headers.update(headers)

    def _r(self, table: str) -> str:
        return f"{self.url}/rest/v1/{table}"

    def _check(self, r: requests.Response):
        if r.status_code >= 300:
            raise RuntimeError(f"Supabase {r.status_code}: {r.text[:300]}")
        return r

    # ------------------------------------------------------------------
    def select_all(self, table: str, params: dict) -> list[dict]:
        out: list[dict] = []
        start = 0
        while True:
            r = self._check(self.s.get(self._r(table), params={**params, "offset": start, "limit": PAGE},
                                       timeout=60))
            rows = r.json()
            out.extend(rows)
            if len(rows) < PAGE:
                return out
            start += PAGE

    def upsert(self, table: str, rows: list[dict], on_conflict: str = "id") -> None:
        for i in range(0, len(rows), 200):
            chunk = rows[i:i + 200]
            self._check(self.s.post(self._r(table), params={"on_conflict": on_conflict},
                                    data=json.dumps(chunk, default=str),
                                    headers={"Prefer": "resolution=merge-duplicates,return=minimal"},
                                    timeout=60))

    def patch(self, table: str, match: dict, values: dict) -> None:
        params = {k: f"eq.{v}" for k, v in match.items()}
        self._check(self.s.patch(self._r(table), params=params, data=json.dumps(values, default=str),
                                 headers={"Prefer": "return=minimal"}, timeout=60))

    def delete(self, table: str, params: dict) -> None:
        self._check(self.s.delete(self._r(table), params=params, timeout=60))

    # ------------------------------------------------------------------
    def load_index(self, days: int = 150) -> dict[str, dict]:
        since = (datetime.now(timezone.utc) - timedelta(days=days)).isoformat()
        rows = self.select_all("offers", {
            "select": RAW_COLUMNS,
            "last_seen": f"gte.{since}",
        })
        return {r["id"]: r for r in rows}

    def source_states(self) -> dict[str, dict]:
        rows = self.select_all("source_state", {"select": "*"})
        return {r["source"]: r for r in rows}

    def save_source_state(self, rows: list[dict]) -> None:
        if rows:
            self.upsert("source_state", rows, on_conflict="source")

    def pending_notifications(self) -> list[dict]:
        return self.select_all("offers", {
            "select": "*", "passes": "eq.true", "aviso": "is.null", "order": "priority.desc,first_seen.asc",
        })

    def cleanup(self) -> None:
        now = datetime.now(timezone.utc)
        # Descartadas por el filtro: se borran a los 30 días.
        self.delete("offers", {"passes": "eq.false", "last_seen": f"lt.{(now - timedelta(days=30)).isoformat()}"})
        # Ofertas que ya no aparecen en ninguna fuente desde hace 120 días y sin estado.
        old = self.select_all("offers", {"select": "id", "last_seen": f"lt.{(now - timedelta(days=120)).isoformat()}"})
        if old:
            with_status = {r["offer_id"] for r in self.select_all("offer_status", {"select": "offer_id"})}
            ids = [r["id"] for r in old if r["id"] not in with_status]
            for i in range(0, len(ids), 100):
                self.delete("offers", {"id": "in.(" + ",".join(ids[i:i + 100]) + ")"})
