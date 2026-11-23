"""API oficial gratuita de Adzuna (developer.adzuna.com)."""
from __future__ import annotations

from ..models import RawOffer
from ..text import html_to_text
from . import get, parse_date, session


def fetch(cfg: dict, app_id: str, app_key: str) -> list[RawOffer]:
    s = session()
    country = cfg.get("pais", "es")
    seen: dict[str, dict] = {}
    for b in cfg.get("busquedas") or []:
        params = {
            "app_id": app_id, "app_key": app_key, "results_per_page": 50,
            "where": cfg.get("donde", "Barcelona"), "max_days_old": cfg.get("max_dias", 3),
            "sort_by": "date",
        }
        if b.get("todas"):
            params["what"] = b["todas"]
        if b.get("alguna"):
            params["what_or"] = b["alguna"]
        r = get(s, f"https://api.adzuna.com/v1/api/jobs/{country}/search/1", params=params, timeout=30)
        for j in r.json().get("results") or []:
            seen.setdefault(str(j.get("id")), j)

    out = []
    for j in seen.values():
        smin, smax = j.get("salary_min"), j.get("salary_max")
        salary = ""
        if smin and not j.get("salary_is_predicted") in ("1", 1, True):
            salary = f"{int(smin):,} – {int(smax or smin):,} €".replace(",", ".")
        ct = (j.get("contract_time") or "").replace("_", " ")
        ctype = (j.get("contract_type") or "").replace("_", " ")
        out.append(RawOffer(
            source="Adzuna",
            title=html_to_text(j.get("title") or ""),
            url=j.get("redirect_url") or "",
            company=(j.get("company") or {}).get("display_name", ""),
            location=(j.get("location") or {}).get("display_name", ""),
            description=html_to_text(j.get("description") or ""),
            published_at=parse_date(j.get("created")),
            salary=salary,
            workday="jornada completa" if ct == "full time" else ("jornada parcial" if ct == "part time" else ""),
            contract="temporal" if ctype == "contract" else ("indefinido" if ctype == "permanent" else ""),
            location_prefiltered=True,
        ))
    return out
