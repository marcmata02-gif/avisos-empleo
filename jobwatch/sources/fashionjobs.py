"""FashionJobs (es.fashionjobs.com): lectura ligera de sus páginas públicas de
ofertas de la provincia de Barcelona. Su robots.txt permite estas páginas.
Solo se abre el detalle (que trae los datos estructurados JobPosting) de las
ofertas nuevas que pasan el primer filtro por título."""
from __future__ import annotations

import json
import re

from bs4 import BeautifulSoup

from ..models import RawOffer
from ..text import html_to_text
from . import get, parse_date, session

BASE = "https://es.fashionjobs.com"
JOB_RE = re.compile(r"/empleo/([^/]+)/[^/]+,(\d+)\.html")


def _company_from_slug(slug: str) -> str:
    words = [w for w in slug.split("-") if w not in {"sl", "slu", "sa", "sau", "s", "l", "u"}]
    return " ".join(w.capitalize() for w in words)


def _jobposting(soup) -> dict:
    for sc in soup.find_all("script", type="application/ld+json"):
        try:
            data = json.loads(sc.string or "", strict=False)
        except (json.JSONDecodeError, TypeError):
            continue
        for it in data if isinstance(data, list) else [data]:
            if isinstance(it, dict) and it.get("@type") == "JobPosting":
                return it
    return {}


def _location(jp: dict) -> str:
    locs = jp.get("jobLocation")
    out = []
    for l in locs if isinstance(locs, list) else [locs]:
        addr = (l or {}).get("address") if isinstance(l, dict) else None
        if isinstance(addr, dict):
            out.append(", ".join(v for v in [addr.get("addressLocality"), addr.get("addressRegion")] if v))
    return "; ".join(o for o in out if o)


def fetch(cfg: dict, prelim, known_urls: set[str]) -> list[RawOffer]:
    s = session()
    pages = int(cfg.get("paginas", 4))
    details_left = int(cfg.get("max_detalles", 30))
    listing = cfg.get("listado", "/provincia/Barcelona,4334")
    found: dict[str, dict] = {}
    for p in range(1, pages + 1):
        url = f"{BASE}{listing}.html" if p == 1 else f"{BASE}{listing},{p}.html"
        soup = BeautifulSoup(get(s, url, timeout=30).text, "html.parser")
        new = 0
        for a in soup.find_all("a", href=True):
            m = JOB_RE.search(a["href"])
            if not m:
                continue
            href = BASE + m.group(0)
            if href in found:
                continue
            title = (a.get("title") or a.get_text(" ", strip=True)).strip()
            if not title:
                continue
            found[href] = {"title": title, "company": _company_from_slug(m.group(1))}
            new += 1
        if new == 0:
            break

    out = []
    for href, it in found.items():
        raw = RawOffer(source="FashionJobs", title=it["title"], url=href, company=it["company"],
                       sector_hint="Moda", location_prefiltered=True)
        ok, _ = prelim(raw.title)
        if ok and href not in known_urls and details_left > 0:
            details_left -= 1
            try:
                jp = _jobposting(BeautifulSoup(get(s, href, timeout=30).text, "html.parser"))
                if jp:
                    raw.title = html_to_text(jp.get("title") or raw.title) or raw.title
                    org = jp.get("hiringOrganization")
                    if isinstance(org, dict) and org.get("name"):
                        raw.company = org["name"]
                    raw.description = html_to_text(jp.get("description") or "")
                    raw.location = _location(jp)
                    raw.published_at = parse_date(jp.get("datePosted"))
                    et = jp.get("employmentType")
                    raw.workday = ", ".join(et) if isinstance(et, list) else str(et or "")
            except Exception:  # noqa: BLE001 - el detalle es opcional
                pass
        out.append(raw)
    return out
