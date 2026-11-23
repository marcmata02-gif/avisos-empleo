"""Lee los emails de alertas de empleo (LinkedIn, Indeed, FashionJobs, FashionUnited,
InfoJobs...) de una cuenta de Gmail dedicada, por IMAP con contraseña de aplicación.

No se accede a LinkedIn ni a Indeed: solo se leen los emails que esos portales envían.
"""
from __future__ import annotations

import email
import imaplib
import re
from datetime import datetime, timedelta, timezone
from email.header import decode_header, make_header
from email.utils import parseaddr, parsedate_to_datetime
from urllib.parse import parse_qs, unquote, urlparse

from bs4 import BeautifulSoup

from ..dedupe import canonical_url
from ..models import RawOffer
from ..text import norm
from . import session

PORTAL_NAMES = {
    "linkedin": "LinkedIn", "indeed": "Indeed", "fashionjobs": "FashionJobs",
    "fashionunited": "FashionUnited", "infojobs": "InfoJobs (alerta)", "otro": "Email",
}

JOB_LINK = {
    "linkedin": re.compile(r"linkedin\.com/(?:comm/)?jobs/view/(?:[^/?\"']*?-)?(\d{6,})", re.I),
    "indeed": re.compile(r"(?:indeed\.[a-z.]+/(?:rc/clk|pagead/clk|viewjob|m/viewjob|applystart|job/)|[?&](?:jk|vjk)=[0-9a-f]{12,})", re.I),
    "infojobs": re.compile(r"infojobs\.net/[^\s\"'<>]+/of-i[0-9a-f]{10,}", re.I),
    "fashionjobs": re.compile(r"fashionjobs\.com/[^\s\"'<>]*(?:empleo|empleos|job|jobs|emploi|oferta|offre|vacature)[^\s\"'<>]*", re.I),
    "fashionunited": re.compile(r"fashionunited\.[a-z.]+/(?:ofertas-trabajo-moda|fashion-jobs|jobs|vacatures|empleo|ofertas)/[^\s\"'<>]+", re.I),
}

_CTA = {"ver empleo", "ver oferta", "view job", "apply", "aplicar", "solicitar", "ver mas", "see more",
        "ver todos los empleos", "see all jobs", "view all jobs", "inscribirme", "inscribete", "postular",
        "candidatura sencilla", "solicitud sencilla", "easy apply", "ver todas", "mas empleos",
        "more jobs", "unsubscribe", "darse de baja", "gestionar alertas", "manage alerts", "ver detalles",
        "view details", "search", "buscar", "jobs", "empleos", "linkedin", "indeed", "help", "ayuda"}
_NOISE_LINE = re.compile(
    r"^(promocionad[oa]|promoted|nuevo|new|actively recruiting|selecci[oó]n activa|be an early applicant|"
    r"s[eé] de los primeros|\d+ (?:connections?|contactos?|antiguos alumnos|alumni|applicants|solicitudes)|"
    r"hace \d+|\d+ (?:d[ií]as?|days?|horas?|hours?) ago|publicado|posted|responde|responds|"
    r"solicitud sencilla|easy apply|candidatura sencilla|urgente|urgent|top applicant|"
    r"tu perfil encaja|your profile matches|ver empleo|view job|apply now|aplicar ahora)\b", re.I)
_LOC_HINT = re.compile(r"(barcelona|catalu|españa|espana|spain|remoto|remote|h[ií]brido|hybrid|presencial|"
                       r"on-site|madrid|valencia|provincia|, es\b|\bbcn\b|hospitalet|badalona|sabadell|terrassa|"
                       r"cornell|prat|cugat|mataro|granollers)", re.I)


def _decode(s: str | None) -> str:
    if not s:
        return ""
    try:
        return str(make_header(decode_header(s)))
    except Exception:  # noqa: BLE001
        return s


def portal_for(sender: str, portales: dict) -> str:
    domain = sender.split("@")[-1].lower()
    for portal, domains in (portales or {}).items():
        if any(domain == d or domain.endswith("." + d) for d in domains):
            return portal
    return "otro"


def _unwrap(href: str) -> str:
    """Desenvuelve enlaces de seguimiento que llevan la URL real en un parámetro."""
    href = href.strip()
    for _ in range(3):
        try:
            q = parse_qs(urlparse(href).query)
        except ValueError:
            break
        inner = None
        for key in ("url", "u", "redirect", "redirect_url", "target", "dest", "destination", "r", "to"):
            v = (q.get(key) or [None])[0]
            if v and v.startswith(("http", "%2F", "http%3A", "https%3A")):
                inner = unquote(v)
                break
        if not inner:
            break
        href = inner
    return href


def _lines(node) -> list[str]:
    txt = node.get_text("\n")
    out = []
    for ln in txt.split("\n"):
        ln = re.sub(r"\s+", " ", ln).strip()
        if ln and ln not in out:
            out.append(ln)
    return out


def _context(a) -> list[str]:
    node = a
    best: list[str] = []
    for _ in range(7):
        node = node.parent
        if node is None:
            break
        lines = _lines(node)
        if len(" ".join(lines)) > 700:
            break
        best = lines
        if len(lines) >= 3:
            break
    return best


def _is_cta(text: str) -> bool:
    t = norm(text).strip(" .:›>»→")
    return not t or t in _CTA or len(t) < 4


def _collect(soup, portal: str, generic: bool) -> tuple[dict, list]:
    pattern = JOB_LINK.get(portal)
    groups: dict[str, dict] = {}
    order: list[str] = []
    for a in soup.find_all("a", href=True):
        href = _unwrap(a["href"])
        if not href.startswith("http"):
            continue
        if generic:
            text = re.sub(r"\s+", " ", a.get_text(" ")).strip()
            if _is_cta(text) or not (10 <= len(text) <= 120) or re.search(
                    r"(unsubscribe|baja|privacy|privacidad|preferencias|preferences|facebook|instagram|"
                    r"twitter|linkedin\.com/company|tiktok|youtube|newsletter|noticias|news)", href + " " + text, re.I):
                continue
        elif pattern:
            if not pattern.search(href):
                continue
        elif not re.search(r"(job|empleo|oferta|vacan|career|position|offre|posting)", href, re.I):
            continue
        url = canonical_url(href)
        if portal == "linkedin":
            m = JOB_LINK["linkedin"].search(href)
            if m:
                url = f"https://www.linkedin.com/jobs/view/{m.group(1)}/"
        if url not in groups:
            groups[url] = {"url": url, "anchors": []}
            order.append(url)
        groups[url]["anchors"].append(a)
    return groups, order


def parse_html(html: str, portal: str) -> list[dict]:
    """Extrae [{title, url, company, location, salary}] de un email de alertas."""
    soup = BeautifulSoup(html, "html.parser")
    groups, order = _collect(soup, portal, generic=False)
    if not order and portal not in ("linkedin", "indeed"):
        # Enlaces envueltos en redirecciones de seguimiento: modo genérico
        groups, order = _collect(soup, portal, generic=True)

    results = []
    for url in order:
        anchors = groups[url]["anchors"]
        title, anchor = "", None
        for a in anchors:
            lines = [ln for ln in _lines(a) if not _is_cta(ln)]
            if lines and 4 <= len(lines[0]) <= 140:
                title, anchor = lines[0], a
                break
        if not title:
            continue
        ctx = _context(anchor)
        rest: list[str] = []
        seen_title = False
        for ln in ctx:
            if not seen_title and (ln == title or ln.startswith(title) or title.startswith(ln)):
                seen_title = True
                continue
            if seen_title and not _is_cta(ln) and not _NOISE_LINE.match(ln):
                rest.append(ln)
        if not seen_title:
            rest = [ln for ln in ctx if ln != title and not _is_cta(ln) and not _NOISE_LINE.match(ln)]
        company = location = salary = ""
        for ln in rest[:5]:
            if "€" in ln or re.search(r"\d+\s?k\b|\bEUR\b", ln):
                salary = salary or ln
                continue
            if " · " in ln and not company:
                parts = [p.strip() for p in ln.split(" · ") if p.strip()]
                company = parts[0]
                if len(parts) > 1 and not location:
                    location = parts[1]
                continue
            if not company and not _LOC_HINT.search(ln):
                company = ln
            elif not location and _LOC_HINT.search(ln):
                location = ln
        results.append({"title": title, "url": url, "company": company[:120],
                        "location": location[:120], "salary": salary[:80]})
    return results


def parse_text(text: str, portal: str) -> list[dict]:
    """Para emails sin HTML: solo enlaces (el título lo da la línea anterior)."""
    out = []
    pattern = JOB_LINK.get(portal)
    lines = [ln.strip() for ln in text.split("\n")]
    for i, ln in enumerate(lines):
        for m in re.finditer(r"https?://\S+", ln):
            href = _unwrap(m.group(0).rstrip(">)."))
            if pattern and not pattern.search(href):
                continue
            title = ""
            for j in range(i - 1, max(-1, i - 4), -1):
                if lines[j] and not lines[j].startswith("http") and not _is_cta(lines[j]):
                    title = lines[j]
                    break
            if title:
                out.append({"title": title, "url": canonical_url(href), "company": "", "location": "", "salary": ""})
    return out


def sector_from_subject(subject: str) -> str:
    s = norm(subject)
    if re.search(r"\b(moda|fashion|textil|retail de moda|lujo|luxury)\b", s):
        return "Moda"
    if re.search(r"\b(cosmetica|cosmetics|belleza|beauty|perfumeria|skincare)\b", s):
        return "Belleza"
    return ""


def parse_message(msg: email.message.Message, cfg: dict) -> tuple[str, list[RawOffer]]:
    sender = parseaddr(msg.get("From", ""))[1]
    portal = portal_for(sender, cfg.get("portales"))
    subject = _decode(msg.get("Subject"))
    html = text = ""
    for part in msg.walk():
        ctype = part.get_content_type()
        if part.get_content_maintype() == "multipart" or part.get("Content-Disposition", "").startswith("attachment"):
            continue
        try:
            payload = part.get_payload(decode=True)
            if payload is None:
                continue
            charset = part.get_content_charset() or "utf-8"
            content = payload.decode(charset, errors="replace")
        except (LookupError, AssertionError):
            continue
        if ctype == "text/html" and not html:
            html = content
        elif ctype == "text/plain" and not text:
            text = content
    items = parse_html(html, portal) if html else parse_text(text, portal)
    try:
        received = parsedate_to_datetime(msg.get("Date"))
        if received and received.tzinfo is None:
            received = received.replace(tzinfo=timezone.utc)
    except (TypeError, ValueError):
        received = None
    implicit = (cfg.get("jornada_implicita") or {}).get(portal) == "completa"
    sector_default = (cfg.get("sector_por_defecto") or {}).get(portal, "") or sector_from_subject(subject)
    offers = [
        RawOffer(
            source=PORTAL_NAMES.get(portal, portal),
            title=it["title"], url=it["url"], company=it["company"], location=it["location"],
            salary=it["salary"], published_at=received, sector_hint=sector_default,
            location_prefiltered=True, implicit_fulltime=implicit,
            extra={"email_subject": subject[:150]},
        )
        for it in items
    ]
    return portal, offers


class GmailSource:
    name = "gmail"

    def __init__(self, cfg: dict, user: str, password: str):
        self.cfg = cfg
        self.user = user
        self.password = password
        self.M: imaplib.IMAP4_SSL | None = None
        self.uids: list[bytes] = []
        self.label = cfg.get("etiqueta_procesado", "ofertas-procesadas")
        self.stats: dict[str, int] = {}

    def fetch(self) -> list[RawOffer]:
        self.M = imaplib.IMAP4_SSL(self.cfg.get("servidor", "imap.gmail.com"))
        self.M.login(self.user, self.password)
        self.M.select(f'"{self.cfg.get("carpeta", "INBOX")}"')
        dias = int(self.cfg.get("dias", 3))
        domains = sorted({d for ds in (self.cfg.get("portales") or {}).values() for d in ds})
        from_q = " OR ".join(domains)
        query = f'newer_than:{dias}d -label:{self.label} from:({from_q})'
        try:
            typ, data = self.M.uid("SEARCH", "X-GM-RAW", f'"{query}"')
        except imaplib.IMAP4.error:
            since = (datetime.now(timezone.utc) - timedelta(days=dias)).strftime("%d-%b-%Y")
            typ, data = self.M.uid("SEARCH", None, "SINCE", since)
        uids = data[0].split() if data and data[0] else []
        offers: list[RawOffer] = []
        for uid in uids[-300:]:
            typ, msg_data = self.M.uid("FETCH", uid, "(RFC822)")
            if typ != "OK" or not msg_data or not isinstance(msg_data[0], tuple):
                continue
            msg = email.message_from_bytes(msg_data[0][1])
            portal, found = parse_message(msg, self.cfg)
            self.stats[portal] = self.stats.get(portal, 0) + len(found)
            offers.extend(found)
            self.uids.append(uid)
        return offers

    def commit(self) -> None:
        """Marca los emails como procesados (solo después de guardar las ofertas)."""
        if not self.M:
            return
        if self.uids:
            try:
                self.M.create(self.label)
            except imaplib.IMAP4.error:
                pass
            for uid in self.uids:
                try:
                    self.M.uid("STORE", uid, "+X-GM-LABELS", f'"{self.label}"')
                except imaplib.IMAP4.error:
                    pass
        self.close()

    def close(self) -> None:
        if self.M:
            try:
                self.M.logout()
            except Exception:  # noqa: BLE001
                pass
            self.M = None


def resolve_redirects(offers: list[RawOffer], limit: int = 40) -> None:
    """Para portales que envuelven los enlaces en redirecciones de seguimiento."""
    s = session()
    n = 0
    for o in offers:
        if n >= limit:
            break
        host = urlparse(o.url).netloc
        if o.source in ("FashionJobs", "FashionUnited") and not any(d in host for d in ("fashionjobs", "fashionunited")):
            try:
                r = s.head(o.url, allow_redirects=True, timeout=15)
                o.url = canonical_url(r.url)
                n += 1
            except Exception:  # noqa: BLE001
                continue
