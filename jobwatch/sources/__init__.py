"""Fuentes de ofertas. Cada fuente devuelve una lista de RawOffer."""
from __future__ import annotations

import time
from datetime import datetime, timezone

import requests

UA = ("Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) "
      "Chrome/124.0 Safari/537.36 avisos-empleo-personal")


def session() -> requests.Session:
    s = requests.Session()
    s.headers.update({"User-Agent": UA, "Accept-Language": "es-ES,es;q=0.9,en;q=0.8"})
    return s


def get(s: requests.Session, url: str, timeout: int = 20, retries: int = 1, **kw) -> requests.Response:
    last = None
    for i in range(retries + 1):
        try:
            r = s.get(url, timeout=timeout, **kw)
            if r.status_code in (429, 502, 503, 504) and i < retries:
                time.sleep(3)
                continue
            r.raise_for_status()
            return r
        except requests.RequestException as e:  # noqa: PERF203
            last = e
            if i < retries:
                time.sleep(2)
    raise last  # type: ignore[misc]


def parse_date(value) -> datetime | None:
    """Acepta ISO 8601, milisegundos epoch o fechas RFC 822 (RSS)."""
    if value in (None, ""):
        return None
    if isinstance(value, (int, float)):
        v = value / 1000 if value > 1e11 else value
        return datetime.fromtimestamp(v, tz=timezone.utc)
    s = str(value).strip()
    try:
        dt = datetime.fromisoformat(s.replace("Z", "+00:00"))
        return dt if dt.tzinfo else dt.replace(tzinfo=timezone.utc)
    except ValueError:
        pass
    from email.utils import parsedate_to_datetime
    try:
        dt = parsedate_to_datetime(s)
        return dt if dt.tzinfo else dt.replace(tzinfo=timezone.utc)
    except (TypeError, ValueError):
        pass
    for fmt in ("%d/%m/%Y", "%d-%m-%Y", "%Y-%m-%d", "%d %b %Y", "%b %d, %Y", "%d.%m.%Y"):
        try:
            return datetime.strptime(s[:20], fmt).replace(tzinfo=timezone.utc)
        except ValueError:
            continue
    return None


def relative_date(text: str) -> datetime | None:
    """'Posted 3 Days Ago', 'hace 2 días', 'Posted Today', 'hace 5 h'..."""
    import re
    from datetime import timedelta
    t = (text or "").lower()
    now = datetime.now(timezone.utc)
    if any(w in t for w in ("today", "hoy", "just posted", "avui")):
        return now
    if any(w in t for w in ("yesterday", "ayer", "ahir")):
        return now - timedelta(days=1)
    m = re.search(r"(\d+)\+?\s*(min|minute|minuto|h|hour|hora|day|día|dia|week|semana|month|mes)", t)
    if not m:
        return None
    n = int(m.group(1))
    unit = m.group(2)
    if unit.startswith(("min",)):
        return now - timedelta(minutes=n)
    if unit.startswith(("h",)):
        return now - timedelta(hours=n)
    if unit.startswith(("d", "dí")):
        return now - timedelta(days=n)
    if unit.startswith(("w", "s")):
        return now - timedelta(weeks=n)
    return now - timedelta(days=30 * n)
