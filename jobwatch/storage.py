"""Guardado en archivos JSON dentro del propio repositorio de GitHub.

- datos/ofertas.json : todas las ofertas vistas (con su descripción), una por línea
- datos/estado.json  : estado de cada fuente
- docs/ofertas.json  : lo que lee la web (solo campos para mostrar)
- docs/estado.json   : resumen de fuentes para la web
"""
from __future__ import annotations

import json
from datetime import datetime, timedelta, timezone
from pathlib import Path

from .config import ROOT

DATA_DIR = ROOT / "datos"
WEB_DIR = ROOT / "docs"

WEB_FIELDS = ["id", "title", "company", "published_at", "first_seen", "links", "sources", "area", "areas",
              "sector", "is_graduate", "flag_texts", "cv_id", "cv_name", "cv_note", "jornada", "modalidad",
              "contrato", "summary", "requirements", "salario", "ubicacion", "priority", "passes",
              "discard_reason"]
MAX_DESC = 4000


def _parse(s) -> datetime | None:
    if not s:
        return None
    try:
        dt = datetime.fromisoformat(str(s).replace("Z", "+00:00"))
    except ValueError:
        return None
    return dt if dt.tzinfo else dt.replace(tzinfo=timezone.utc)


def _dump_lines(path: Path, rows: list[dict]) -> None:
    """Un registro por línea: los cambios entre revisiones son pequeños en GitHub."""
    path.parent.mkdir(parents=True, exist_ok=True)
    body = ",\n".join(json.dumps(r, ensure_ascii=False, sort_keys=True, default=str) for r in rows)
    path.write_text("[\n" + body + "\n]\n", encoding="utf-8")


class Storage:
    def __init__(self, data_dir: Path = DATA_DIR, web_dir: Path = WEB_DIR):
        self.data_dir = Path(data_dir)
        self.web_dir = Path(web_dir)
        self.offers: dict[str, dict] = {}
        self.states: dict[str, dict] = {}
        f = self.data_dir / "ofertas.json"
        if f.exists():
            self.offers = {r["id"]: r for r in json.loads(f.read_text(encoding="utf-8") or "[]")}
        s = self.data_dir / "estado.json"
        if s.exists():
            self.states = json.loads(s.read_text(encoding="utf-8") or "{}")

    # --- misma interfaz que usa main.py -------------------------------
    def source_states(self) -> dict[str, dict]:
        return {k: dict(v) for k, v in self.states.items()}

    def load_index(self, days: int = 150) -> dict[str, dict]:
        return {k: dict(v) for k, v in self.offers.items()}

    def upsert(self, table: str, rows: list[dict], on_conflict: str = "id") -> None:
        for r in rows:
            r = dict(r)
            if r.get("description") and len(r["description"]) > MAX_DESC:
                r["description"] = r["description"][:MAX_DESC]
            self.offers.setdefault(r["id"], {}).update(r)

    def patch(self, table: str, match: dict, values: dict) -> None:
        if match["id"] in self.offers:
            self.offers[match["id"]].update(values)

    def pending_notifications(self) -> list[dict]:
        rows = [o for o in self.offers.values() if o.get("passes") and o.get("aviso") is None]
        return sorted(rows, key=lambda r: (-(r.get("priority") or 0), r.get("first_seen") or ""))

    def save_source_state(self, rows: list[dict]) -> None:
        for r in rows:
            self.states[r["source"]] = r

    def cleanup(self) -> None:
        now = datetime.now(timezone.utc)
        for oid, o in list(self.offers.items()):
            seen = _parse(o.get("last_seen")) or now
            if not o.get("passes") and now - seen > timedelta(days=30):
                del self.offers[oid]
            elif now - seen > timedelta(days=120):
                del self.offers[oid]

    # --- escribir archivos --------------------------------------------
    def flush(self) -> None:
        rows = sorted(self.offers.values(), key=lambda r: r["id"])
        _dump_lines(self.data_dir / "ofertas.json", rows)
        (self.data_dir / "estado.json").write_text(
            json.dumps(self.states, ensure_ascii=False, indent=1, sort_keys=True, default=str), encoding="utf-8")
        self.export_web()

    def export_web(self) -> None:
        now = datetime.now(timezone.utc)
        web = []
        for o in self.offers.values():
            seen = _parse(o.get("first_seen")) or now
            if o.get("passes") and now - seen <= timedelta(days=90):
                web.append({k: o.get(k) for k in WEB_FIELDS})
            elif not o.get("passes") and now - seen <= timedelta(days=14) and o.get("discard_reason") not in (
                    "Fuera de tus áreas", "Sector no reconocido (ni moda ni belleza)"):
                web.append({k: o.get(k) for k in ("id", "title", "company", "first_seen", "published_at", "links",
                                                   "sources", "passes", "discard_reason")})
        web.sort(key=lambda r: r.get("first_seen") or "", reverse=True)
        _dump_lines(self.web_dir / "ofertas.json", web)
        public_states = {
            k: {"last_run": v.get("last_run"), "last_error": v.get("last_error"),
                "meta": {kk: vv for kk, vv in (v.get("meta") or {}).items() if kk != "telegram_chat_id"}}
            for k, v in self.states.items() if k != "limpieza"
        }
        (self.web_dir / "estado.json").write_text(
            json.dumps(public_states, ensure_ascii=False, indent=1, sort_keys=True, default=str), encoding="utf-8")
