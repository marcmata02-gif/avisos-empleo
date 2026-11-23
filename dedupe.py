"""Identificación de duplicados entre portales."""
from __future__ import annotations

import hashlib
import re
from urllib.parse import parse_qs, urlencode, urlparse, urlunparse

from .text import norm

_COMPANY_NOISE = [
    "s.a.u", "s.a.", "s.l.u", "s.l.", "sau", "slu", "s a", "s l", "sa", "sl", "s.l", "s.a",
    "group", "grupo", "groupe", "holding", "spain", "espana", "iberia", "iberica", "europe",
    "international", "internacional", "services", "retail", "brands", "inc", "ltd", "gmbh",
    "b.v.", "bv", "co", "company", "corporate", "jewelry", "fashion", "barcelona",
]
_TITLE_NOISE = re.compile(
    r"\((?:[^)]*)\)|\[(?:[^\]]*)\]|\b(?:h|m|f|w|x|d|a)\s*/\s*(?:h|m|f|w|x|d|a)(?:\s*/\s*(?:h|m|f|w|x|d|a))?\b"
    r"|\bm/f/d\b|\bf/m/x\b|\bw/m/x\b|\bx/m/w\b|\bh/m/x\b|\bm/w/x\b"
)
_TITLE_DROP_WORDS = {"barcelona", "bcn", "spain", "espana", "hq", "headquarters", "sede", "central",
                     "oficinas", "office", "-", "–", "|", "en", "in", "de", "the", "y", "and", "&"}


def company_key(company: str, alias_map: dict[str, str] | None = None) -> str:
    c = norm(company)
    if alias_map:
        for alias, canon in alias_map.items():
            if alias and (c == alias or re.search(r"(?<![a-z0-9])" + re.escape(alias) + r"(?![a-z0-9])", c)):
                return canon
    c = re.sub(r"[^a-z0-9&' ]+", " ", c)
    words = [w for w in c.split() if w not in _COMPANY_NOISE]
    return " ".join(words) or c.strip()


def title_key(title: str) -> str:
    t = norm(title)
    t = _TITLE_NOISE.sub(" ", t)
    t = re.sub(r"(\w)/a\b", r"\1", t)          # dependiente/a → dependiente
    t = re.sub(r"(\w)\(a\)", r"\1", t)
    t = re.sub(r"[^a-z0-9&+ ]+", " ", t)
    words = [w for w in t.split() if w not in _TITLE_DROP_WORDS]
    return " ".join(words)


def fingerprint(title: str, company: str, alias_map: dict[str, str] | None = None) -> str:
    key = f"{company_key(company, alias_map)}|{title_key(title)}"
    return hashlib.sha1(key.encode()).hexdigest()[:16]


_TRACKING = {"utm_source", "utm_medium", "utm_campaign", "utm_content", "utm_term", "trk", "trackingid",
             "refid", "midtoken", "midsig", "eid", "lipi", "from", "src", "source", "gh_src", "ref",
             "tk", "alid", "fccid", "vjs", "sjdu", "acatk", "pub", "xpse", "xfps", "xkcb"}


def canonical_url(url: str) -> str:
    """Quita parámetros de seguimiento para comparar enlaces."""
    try:
        p = urlparse(url.strip())
    except ValueError:
        return url
    host = p.netloc.lower()
    path = p.path
    q = parse_qs(p.query)
    if "linkedin.com" in host:
        m = re.search(r"/jobs/view/(?:[^/]*?-)?(\d{6,})", path)
        if m:
            return f"https://www.linkedin.com/jobs/view/{m.group(1)}/"
    if "indeed." in host:
        jk = (q.get("jk") or q.get("vjk") or [None])[0]
        if jk:
            return f"https://es.indeed.com/viewjob?jk={jk}"
    keep = {k: v for k, v in q.items() if k.lower() not in _TRACKING}
    return urlunparse((p.scheme or "https", host, path.rstrip("/") or "/", "", urlencode(keep, doseq=True), ""))
