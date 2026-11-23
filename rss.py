"""Feeds RSS genéricos de portales de empleo."""
from __future__ import annotations

import feedparser

from ..models import RawOffer
from ..text import html_to_text
from . import get, parse_date, session


def fetch(cfg: dict) -> list[RawOffer]:
    s = session()
    out: list[RawOffer] = []
    for feed in cfg.get("feeds") or []:
        r = get(s, feed["url"], timeout=30)
        parsed = feedparser.parse(r.content)
        for e in parsed.entries:
            out.append(RawOffer(
                source=feed.get("nombre", "RSS"),
                title=html_to_text(e.get("title", "")),
                url=e.get("link", ""),
                company=e.get("author", "") or feed.get("empresa", ""),
                location=e.get("location", "") or e.get("tt_location", "") or "",
                description=html_to_text(e.get("summary", "") or e.get("description", "")),
                published_at=parse_date(e.get("published") or e.get("updated")),
                sector_hint=feed.get("sector", ""),
                location_prefiltered=bool(feed.get("solo_barcelona")),
            ))
    return out
