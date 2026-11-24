"""Páginas de empleo de empresas: endpoints públicos de las plataformas (ATS)
más una lectura ligera de HTML para el resto."""
from __future__ import annotations

import json
import re
import threading
import xml.etree.ElementTree as ET
from urllib.parse import urljoin, urlparse

from bs4 import BeautifulSoup

from ..models import RawOffer
from ..text import html_to_text, norm
from . import get, parse_date, relative_date, session


class Budget:
    """Límite compartido de páginas de detalle por revisión."""

    def __init__(self, n: int):
        self.n = n
        self.lock = threading.Lock()

    def take(self) -> bool:
        with self.lock:
            if self.n <= 0:
                return False
            self.n -= 1
            return True


class Ctx:
    def __init__(self, company: dict, prelim, known_urls: set[str], budget: Budget, timeout: int = 20):
        self.c = company
        self.s = session()
        self.prelim = prelim
        self.known = known_urls
        self.budget = budget
        self.timeout = timeout

    def want_detail(self, title: str, url: str) -> bool:
        ok, _ = self.prelim(title)
        return ok and url not in self.known and self.budget.take()

    def raw(self, **kw) -> RawOffer:
        sec = self.c.get("sector")
        sectors = sec if isinstance(sec, list) else ([sec] if sec else [])
        kw.setdefault("company", self.c.get("nombre", ""))
        return RawOffer(source="Web de la empresa", company_sectors=sectors,
                        default_location=self.c.get("ubicacion") or "", **kw)


# ---------------------------------------------------------------------------
def greenhouse(x: Ctx, eu: bool = False) -> list[RawOffer]:
    host = "boards-api.eu.greenhouse.io" if eu else "boards-api.greenhouse.io"
    data = get(x.s, f"https://{host}/v1/boards/{x.c['id']}/jobs", params={"content": "true"}, timeout=x.timeout).json()
    out = []
    for j in data.get("jobs") or []:
        meta = {m.get("name", ""): m.get("value") for m in (j.get("metadata") or []) if isinstance(m, dict)}
        out.append(x.raw(
            title=j.get("title", ""), url=j.get("absolute_url", ""),
            location=(j.get("location") or {}).get("name", ""),
            description=html_to_text(j.get("content") or ""),
            published_at=parse_date(j.get("first_published") or j.get("updated_at")),
            workday=str(meta.get("Employment Type") or meta.get("Time Type") or ""),
        ))
    return out


def lever(x: Ctx, eu: bool = False) -> list[RawOffer]:
    host = "api.eu.lever.co" if eu else "api.lever.co"
    data = get(x.s, f"https://{host}/v0/postings/{x.c['id']}", params={"mode": "json"}, timeout=x.timeout).json()
    out = []
    for j in data or []:
        cats = j.get("categories") or {}
        parts = [j.get("descriptionPlain") or html_to_text(j.get("description") or "")]
        for lst in j.get("lists") or []:
            parts.append(lst.get("text", ""))
            parts.append(html_to_text(lst.get("content", "")))
        parts.append(j.get("additionalPlain") or "")
        commitment = cats.get("commitment", "") or ""
        out.append(x.raw(
            title=j.get("text", ""), url=j.get("hostedUrl", ""),
            location=cats.get("location", "") or ", ".join(cats.get("allLocations") or []),
            description="\n".join(p for p in parts if p),
            published_at=parse_date(j.get("createdAt")),
            contract=commitment,
            workday=commitment if re.search(r"time", commitment, re.I) else "",
            modality=j.get("workplaceType", "") or "",
        ))
    return out


def workable(x: Ctx) -> list[RawOffer]:
    data = get(x.s, f"https://apply.workable.com/api/v1/widget/accounts/{x.c['id']}", timeout=x.timeout).json()
    out = []
    for j in data.get("jobs") or []:
        url = j.get("url") or j.get("shortlink") or ""
        loc = ", ".join(v for v in [j.get("city"), j.get("state"), j.get("country")] if v)
        raw = x.raw(title=j.get("title", ""), url=url, location=loc,
                    published_at=parse_date(j.get("published_on") or j.get("created_at")),
                    workday=j.get("employment_type", "") or "",
                    modality="Remoto" if j.get("telecommuting") else "")
        sc = j.get("shortcode")
        if sc and x.want_detail(raw.title, url):
            try:
                d = get(x.s, f"https://apply.workable.com/api/v2/accounts/{x.c['id']}/jobs/{sc}", timeout=x.timeout).json()
                raw.description = "\n".join(html_to_text(d.get(k) or "") for k in ("description", "requirements", "benefits"))
            except Exception:  # noqa: BLE001
                pass
        out.append(raw)
    return out


def personio(x: Ctx) -> list[RawOffer]:
    xml = None
    for tld in ("de", "com"):
        try:
            xml = get(x.s, f"https://{x.c['id']}.jobs.personio.{tld}/xml", timeout=x.timeout).content
            base = f"https://{x.c['id']}.jobs.personio.{tld}"
            break
        except Exception:  # noqa: BLE001
            continue
    if xml is None:
        raise RuntimeError("No se pudo leer el feed de Personio")
    root = ET.fromstring(xml)
    out = []
    for p in root.iter("position"):
        def t(tag):
            el = p.find(tag)
            return (el.text or "").strip() if el is not None and el.text else ""
        desc = []
        for jd in p.iter("jobDescription"):
            desc.append(t_el(jd.find("name")))
            desc.append(html_to_text(t_el(jd.find("value"))))
        offices = [o.text for o in p.iter("office") if o.text]
        offices += [o.text for o in p.iter("additionalOffice") if o.text]
        out.append(x.raw(
            title=t("name"), url=f"{base}/job/{t('id')}",
            location=", ".join(dict.fromkeys(offices)),
            description="\n".join(d for d in desc if d),
            published_at=parse_date(t("createdAt")),
            contract=t("employmentType"), workday=t("schedule"),
        ))
    return out


def t_el(el) -> str:
    return (el.text or "").strip() if el is not None and el.text else ""


def teamtailor(x: Ctx) -> list[RawOffer]:
    base = x.c["url"].rstrip("/")
    out: list[RawOffer] = []
    try:
        r = get(x.s, f"{base}/jobs.rss", timeout=x.timeout)
        root = ET.fromstring(r.content)
        for item in root.iter("item"):
            cities = [el.text.strip() for el in item.iter() if el.tag.endswith("}city") and el.text]
            remote = t_el(item.find("remoteStatus"))
            out.append(x.raw(
                title=t_el(item.find("title")), url=t_el(item.find("link")),
                location=", ".join(dict.fromkeys(cities)),
                description=html_to_text(t_el(item.find("description"))),
                published_at=parse_date(t_el(item.find("pubDate"))),
                modality={"hybrid": "Híbrido", "fully": "Remoto", "none": "Presencial"}.get(remote.lower(), ""),
            ))
        if out:
            return out
    except Exception:  # noqa: BLE001
        pass
    return html_list(x, link_pattern=r"/jobs/\d+")


def smartrecruiters(x: Ctx) -> list[RawOffer]:
    data = get(x.s, f"https://api.smartrecruiters.com/v1/companies/{x.c['id']}/postings",
               params={"limit": 100}, timeout=x.timeout).json()
    out = []
    for j in data.get("content") or []:
        loc = j.get("location") or {}
        url = f"https://jobs.smartrecruiters.com/{x.c['id']}/{j.get('id')}"
        raw = x.raw(title=j.get("name", ""), url=url,
                    location=", ".join(v for v in [loc.get("city"), loc.get("country")] if v),
                    published_at=parse_date(j.get("releasedDate")),
                    workday=(j.get("typeOfEmployment") or {}).get("label", ""),
                    modality="Remoto" if loc.get("remote") else "")
        if x.want_detail(raw.title, url):
            try:
                d = get(x.s, f"https://api.smartrecruiters.com/v1/companies/{x.c['id']}/postings/{j.get('id')}",
                        timeout=x.timeout).json()
                secs = ((d.get("jobAd") or {}).get("sections") or {})
                raw.description = "\n".join(html_to_text((v or {}).get("text", "")) for v in secs.values())
            except Exception:  # noqa: BLE001
                pass
        out.append(raw)
    return out


def recruitee(x: Ctx) -> list[RawOffer]:
    data = get(x.s, f"https://{x.c['id']}.recruitee.com/api/offers/", timeout=x.timeout).json()
    out = []
    for j in data.get("offers") or []:
        out.append(x.raw(
            title=j.get("title", ""), url=j.get("careers_url", ""),
            location=j.get("location", "") or j.get("city", ""),
            description=html_to_text((j.get("description") or "") + (j.get("requirements") or "")),
            published_at=parse_date(j.get("published_at")),
            workday=j.get("employment_type_code", "") or "",
        ))
    return out


def ashby(x: Ctx) -> list[RawOffer]:
    data = get(x.s, f"https://api.ashbyhq.com/posting-api/job-board/{x.c['id']}", timeout=x.timeout).json()
    out = []
    for j in data.get("jobs") or []:
        out.append(x.raw(
            title=j.get("title", ""), url=j.get("jobUrl", ""), location=j.get("location", ""),
            description=j.get("descriptionPlain") or html_to_text(j.get("descriptionHtml") or ""),
            published_at=parse_date(j.get("publishedAt")), workday=j.get("employmentType", "") or "",
        ))
    return out


def successfactors(x: Ctx) -> list[RawOffer]:
    """Webs de empleo de SAP SuccessFactors (las de /job/Ciudad-Titulo/123/)."""
    base = x.c["url"].rstrip("/")
    out: list[RawOffer] = []
    seen = set()
    for start in (0, 25, 50, 75):
        params = {"q": "", "locationsearch": x.c.get("buscar_ubicacion", "Barcelona"),
                  "sortColumn": "referencedate", "sortDirection": "desc", "startrow": start}
        try:
            r = get(x.s, f"{base}/search/", params=params, timeout=x.timeout)
        except Exception:  # noqa: BLE001 - algunas webs SAP no tienen /search/
            if start == 0:
                return html_list(x, link_pattern="/job/")
            break
        soup = BeautifulSoup(r.text, "html.parser")
        rows = soup.select("tr.data-row") or soup.select("li.job-tile") or []
        if not rows:
            # plantillas modernas: enlaces /job/...
            rows = [a.parent for a in soup.select("a.jobTitle-link")]
        new = 0
        for row in rows:
            a = row.select_one("a.jobTitle-link") or row.find("a", href=re.compile(r"/job/"))
            if not a:
                continue
            url = urljoin(base + "/", a.get("href", ""))
            if url in seen:
                continue
            seen.add(url)
            new += 1
            loc_el = row.select_one(".jobLocation") or row.select_one("[class*=location]")
            date_el = row.select_one(".jobDate") or row.select_one("[class*=date]")
            raw = x.raw(title=a.get_text(" ", strip=True), url=url,
                        location=loc_el.get_text(" ", strip=True) if loc_el else "",
                        published_at=parse_date(date_el.get_text(strip=True)) if date_el else None)
            if x.want_detail(raw.title, url):
                try:
                    d = BeautifulSoup(get(x.s, url, timeout=x.timeout).text, "html.parser")
                    body = d.select_one("[itemprop=description]") or d.select_one(".jobdescription") or d.select_one(".job")
                    raw.description = html_to_text(str(body)) if body else ""
                    if not raw.location:
                        loc2 = d.select_one("[itemprop=jobLocation]") or d.select_one(".jobGeoLocation")
                        raw.location = loc2.get_text(" ", strip=True) if loc2 else ""
                except Exception:  # noqa: BLE001
                    pass
            out.append(raw)
        if new < 20:
            break
    return out


def workday(x: Ctx) -> list[RawOffer]:
    """url: https://TENANT.wdN.myworkdayjobs.com/[idioma/]SITIO"""
    u = urlparse(x.c["url"])
    tenant = u.netloc.split(".")[0]
    parts = [p for p in u.path.split("/") if p]
    site = parts[-1] if parts else ""
    api = f"https://{u.netloc}/wday/cxs/{tenant}/{site}"
    out = []
    for offset in (0, 20, 40):
        payload = {"appliedFacets": {}, "limit": 20, "offset": offset,
                   "searchText": x.c.get("buscar_texto", "Barcelona")}
        r = x.s.post(f"{api}/jobs", json=payload, timeout=x.timeout,
                     headers={"Accept": "application/json", "Content-Type": "application/json"})
        r.raise_for_status()
        posts = r.json().get("jobPostings") or []
        for j in posts:
            path = j.get("externalPath", "")
            url = f"https://{u.netloc}/{site}{path}" if path else x.c["url"]
            raw = x.raw(title=j.get("title", ""), url=url, location=j.get("locationsText", ""),
                        published_at=relative_date(j.get("postedOn", "")))
            if path and x.want_detail(raw.title, url):
                try:
                    d = get(x.s, f"{api}{path}", timeout=x.timeout,
                            headers={"Accept": "application/json"}).json().get("jobPostingInfo", {})
                    raw.description = html_to_text(d.get("jobDescription", ""))
                    raw.workday = d.get("timeType", "") or ""
                    raw.location = d.get("location", "") or raw.location
                except Exception:  # noqa: BLE001
                    pass
            out.append(raw)
        if len(posts) < 20:
            break
    return out


def factorial(x: Ctx) -> list[RawOffer]:
    return html_list(x, link_pattern=r"/job_posting/")


# ---------------------------------------------------------------------------
_JOBISH = re.compile(r"(job|empleo|oferta|vacan|career|position|offre|posting|puesto|trabaj|/o/|/node/|/detail/)", re.I)
_NAV = {"inicio", "home", "contacto", "contact", "login", "acceder", "registrate", "sign in", "about us",
        "sobre nosotros", "privacy", "privacidad", "cookies", "aviso legal", "ver todas", "all jobs",
        "todas las ofertas", "volver", "back", "siguiente", "next", "anterior", "previous", "buscar", "search"}


def _jsonld_jobs(soup) -> list[dict]:
    jobs = []
    for sc in soup.find_all("script", type="application/ld+json"):
        try:
            data = json.loads(sc.string or "")
        except (json.JSONDecodeError, TypeError):
            continue
        items = data if isinstance(data, list) else data.get("@graph", [data]) if isinstance(data, dict) else []
        for it in items:
            if isinstance(it, dict) and it.get("@type") == "JobPosting":
                jobs.append(it)
    return jobs


def _jsonld_location(j: dict) -> str:
    loc = j.get("jobLocation")
    locs = loc if isinstance(loc, list) else [loc]
    out = []
    for l in locs:
        if isinstance(l, dict):
            addr = l.get("address") or {}
            if isinstance(addr, dict):
                out.append(", ".join(v for v in [addr.get("addressLocality"), addr.get("addressRegion")] if v))
    return "; ".join(o for o in out if o)


def html_list(x: Ctx, link_pattern: str | None = None) -> list[RawOffer]:
    """Lectura ligera de una página de empleo: enlaces a ofertas (+ detalle si pasa el filtro)."""
    url = x.c["url"]
    r = get(x.s, url, timeout=x.timeout)
    soup = BeautifulSoup(r.text, "html.parser")
    pattern = link_pattern or x.c.get("enlace_patron")
    rx = re.compile(re.escape(pattern) if pattern and not any(ch in pattern for ch in "\\[](){}+*?|^$") else pattern) \
        if pattern else _JOBISH
    host = urlparse(url).netloc
    found: dict[str, str] = {}
    for a in soup.find_all("a", href=True):
        href = urljoin(url, a["href"])
        if not rx.search(href):
            continue
        if urlparse(href).netloc and urlparse(href).netloc != host and not pattern:
            continue
        text = re.sub(r"\s+", " ", a.get_text(" ")).strip()
        if not text or norm(text) in _NAV or len(text) < 4 or len(text) > 160:
            # algunas webs ponen el título en un atributo
            text = (a.get("title") or a.get("aria-label") or "").strip()
            if not text or len(text) < 4:
                continue
        if href.rstrip("/") == url.rstrip("/"):
            continue
        found.setdefault(href, text.split("  ")[0][:150])
    out = []
    for href, title in found.items():
        raw = x.raw(title=title, url=href)
        if x.want_detail(title, href):
            try:
                d = BeautifulSoup(get(x.s, href, timeout=x.timeout).text, "html.parser")
                jl = _jsonld_jobs(d)
                if jl:
                    j = jl[0]
                    raw.title = html_to_text(j.get("title") or title) or title
                    raw.description = html_to_text(j.get("description") or "")
                    raw.location = _jsonld_location(j)
                    raw.published_at = parse_date(j.get("datePosted"))
                    et = j.get("employmentType")
                    raw.workday = ", ".join(et) if isinstance(et, list) else str(et or "")
                else:
                    main = d.find("main") or d.find("article") or d.body
                    raw.description = html_to_text(str(main))[:20000] if main else ""
            except Exception:  # noqa: BLE001
                pass
        out.append(raw)
    return out


def html_generic(x: Ctx) -> list[RawOffer]:
    return html_list(x)


FETCHERS = {
    "greenhouse": greenhouse,
    "greenhouse_eu": lambda x: greenhouse(x, eu=True),
    "lever": lever,
    "lever_eu": lambda x: lever(x, eu=True),
    "workable": workable,
    "personio": personio,
    "teamtailor": teamtailor,
    "smartrecruiters": smartrecruiters,
    "recruitee": recruitee,
    "ashby": ashby,
    "successfactors": successfactors,
    "workday": workday,
    "factorial": factorial,
    "html": html_generic,
}


def fetch_company(company: dict, prelim, known_urls: set[str], budget: Budget, timeout: int = 20) -> list[RawOffer]:
    platform = (company.get("plataforma") or "pendiente").lower()
    fn = FETCHERS.get(platform)
    if not fn:
        return []
    return fn(Ctx(company, prelim, known_urls, budget, timeout))
