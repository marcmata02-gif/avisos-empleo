"""Avisos por Telegram."""
from __future__ import annotations

import html
import os
import time
from datetime import datetime, timezone

import requests

API = "https://api.telegram.org/bot{token}/{method}"


class Telegram:
    def __init__(self, token: str | None = None, chat_id: str | None = None, web_url: str | None = None):
        self.token = token or os.environ.get("TELEGRAM_BOT_TOKEN", "")
        self.chat_id = chat_id or os.environ.get("TELEGRAM_CHAT_ID", "")
        self.web_url = (web_url or os.environ.get("WEB_URL", "")).strip()
        if not self.token or not self.chat_id:
            raise RuntimeError("Faltan TELEGRAM_BOT_TOKEN o TELEGRAM_CHAT_ID (secretos de GitHub).")

    def _call(self, method: str, payload: dict) -> dict:
        for attempt in range(4):
            r = requests.post(API.format(token=self.token, method=method), json=payload, timeout=30)
            if r.status_code == 429:  # demasiados mensajes seguidos
                wait = int(r.json().get("parameters", {}).get("retry_after", 5))
                time.sleep(min(wait, 60))
                continue
            data = r.json()
            if not data.get("ok"):
                raise RuntimeError(f"Telegram: {data.get('description')}")
            return data
        raise RuntimeError("Telegram: demasiados reintentos")

    def send_text(self, text: str) -> None:
        self._call("sendMessage", {"chat_id": self.chat_id, "text": text, "parse_mode": "HTML",
                                   "disable_web_page_preview": True})

    def send_offer(self, o: dict) -> None:
        self._call("sendMessage", {
            "chat_id": self.chat_id,
            "text": format_offer(o),
            "parse_mode": "HTML",
            "disable_web_page_preview": True,
            "reply_markup": {"inline_keyboard": buttons(o, self.web_url)},
        })
        time.sleep(1.1)  # Telegram permite ~1 mensaje/segundo por chat


def _e(s) -> str:
    return html.escape(str(s or ""), quote=False)


def ago(dt_iso: str | None) -> str:
    if not dt_iso:
        return ""
    try:
        dt = datetime.fromisoformat(str(dt_iso).replace("Z", "+00:00"))
    except ValueError:
        return ""
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=timezone.utc)
    mins = int((datetime.now(timezone.utc) - dt).total_seconds() // 60)
    if mins < 60:
        return f"hace {max(mins, 1)} min"
    if mins < 60 * 24:
        return f"hace {mins // 60} h"
    days = mins // (60 * 24)
    return "hace 1 día" if days == 1 else f"hace {days} días"


def format_offer(o: dict) -> str:
    tags = []
    if o.get("is_graduate"):
        tags.append("🎓 <b>GRADUATE PROGRAM</b>")
    if o.get("sector") == "Moda":
        tags.append("👗 <b>MODA</b>")
    else:
        tags.append("💄 Belleza")
    lines = [" · ".join(tags), "", f"<b>{_e(o.get('title'))}</b>"]
    where = " · ".join(x for x in [o.get("company"), o.get("ubicacion")] if x)
    lines.append(f"🏢 {_e(where)}")
    meta = " · ".join(x for x in [o.get("area"), o.get("modalidad"), o.get("jornada")] if x)
    if meta:
        lines.append(f"🏷 {_e(meta)}")
    if o.get("salario"):
        lines.append(f"💶 {_e(o['salario'])}")
    if o.get("summary"):
        lines.append(f"📝 {_e(o['summary'])}")
    cv = f"CV {o.get('cv_id')}: {o.get('cv_name') or ''}".strip()
    lines.append(f"📄 <b>{_e(cv)}</b>")
    if o.get("cv_note"):
        lines.append(f"   <i>{_e(o['cv_note'])}</i>")
    srcs = o.get("sources") or []
    when = ago(o.get("published_at"))
    tail = " · ".join(x for x in [", ".join(srcs), when] if x)
    if tail:
        lines.append(f"🔎 {_e(tail)}")
    return "\n".join(lines)


def buttons(o: dict, web_url: str = "") -> list[list[dict]]:
    links = o.get("links") or []
    row = []
    if links:
        row.append({"text": "✅ Aplicar", "url": links[0]["url"]})
    if web_url:
        row.append({"text": "📋 Ver en la web", "url": f"{web_url.rstrip('/')}/#o={o['id']}"})
    rows = [row] if row else []
    extra = [{"text": f"🔗 {link['source']}", "url": link["url"]} for link in links[1:4]]
    if extra:
        rows.append(extra)
    return rows
