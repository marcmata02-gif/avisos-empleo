"""API oficial gratuita de InfoJobs (developer.infojobs.net)."""
from __future__ import annotations

from ..models import RawOffer
from ..text import html_to_text
from . import get, parse_date, session

BASE = "https://api.infojobs.net/api"


def _v(obj, key="value") -> str:
    if isinstance(obj, dict):
        return str(obj.get(key) or "")
    return str(obj or "")


def fetch(cfg: dict, client_id: str, client_secret: str, first_run: bool, prelim, known_urls: set[str]) -> list[RawOffer]:
    s = session()
    s.auth = (client_id, client_secret)
    since = "_7_DAYS" if first_run else "_24_HOURS"
    seen: dict[str, dict] = {}
    for q in cfg.get("busquedas") or []:
        params = {"q": q, "province": cfg.get("provincia", "barcelona"), "maxResults": cfg.get("max_resultados", 50),
                  "order": "updated-desc", "sinceDate": since}
        r = get(s, f"{BASE}/9/offer", params=params, timeout=30)
        for o in r.json().get("offers") or []:
            seen.setdefault(o.get("id"), o)

    offers: list[RawOffer] = []
    details_left = int(cfg.get("max_detalles", 25))
    for oid, o in seen.items():
        title = o.get("title") or ""
        url = (o.get("link") or "").split("?")[0]
        city = o.get("city") or ""
        prov = _v(o.get("province"))
        raw = RawOffer(
            source="InfoJobs",
            title=title,
            url=url,
            company=_v(o.get("author"), "name"),
            location=", ".join(x for x in [city, prov] if x),
            published_at=parse_date(o.get("published") or o.get("updated")),
            salary=o.get("salaryDescription") or "",
            contract=_v(o.get("contractType")),
            workday=_v(o.get("workDay")),
            modality=_v(o.get("teleworking")),
            experience=_v(o.get("experienceMin")),
            location_prefiltered=True,
            extra={"requirements_text": o.get("requirementMin") or "", "category": _v(o.get("category"))},
        )
        raw.description = o.get("requirementMin") or ""
        ok, _ = prelim(title)
        if ok and details_left > 0 and url not in known_urls:
            try:
                d = get(s, f"{BASE}/7/offer/{oid}", timeout=30).json()
                raw.description = html_to_text(d.get("description") or "")
                if d.get("minRequirements"):
                    raw.description += "\n\nRequisitos mínimos:\n" + html_to_text(d.get("minRequirements"))
                    raw.extra["requirements_text"] = d.get("minRequirements")
                raw.contract = _v(d.get("contractType")) or raw.contract
                raw.workday = _v(d.get("journey")) or raw.workday
                details_left -= 1
            except Exception:  # noqa: BLE001 - el detalle es opcional
                pass
        offers.append(raw)
    return offers
