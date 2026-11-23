"""Utilidades de texto: normalización, búsqueda de palabras clave, HTML→texto."""
from __future__ import annotations

import html as _html
import re
import unicodedata
from functools import lru_cache

from bs4 import BeautifulSoup


def strip_accents(s: str) -> str:
    return "".join(c for c in unicodedata.normalize("NFKD", s) if not unicodedata.combining(c))


def norm(s: str | None) -> str:
    """minúsculas, sin acentos, espacios simples. Conserva / & + - ' para frases."""
    if not s:
        return ""
    s = strip_accents(str(s)).lower()
    s = s.replace("’", "'").replace("´", "'").replace("–", "-").replace("—", "-")
    s = re.sub(r"[​\xa0]", " ", s)
    s = re.sub(r"\s+", " ", s)
    return s.strip()


@lru_cache(maxsize=4096)
def _kw_regex(kw: str) -> re.Pattern:
    k = norm(kw)
    prefix = k.endswith("*")
    if prefix:
        k = k[:-1]
    parts = [re.escape(p) for p in k.split(" ") if p]
    body = r"[\s\-/]+".join(parts)
    tail = r"[a-z0-9]*" if prefix else ""
    return re.compile(r"(?<![a-z0-9])" + body + tail + r"(?![a-z0-9])")


def find_kw(text_norm: str, keywords) -> list[str]:
    """Devuelve las palabras clave (tal como están en la config) que aparecen."""
    if not text_norm or not keywords:
        return []
    return [kw for kw in keywords if _kw_regex(str(kw)).search(text_norm)]


def has_kw(text_norm: str, keywords) -> bool:
    if not text_norm or not keywords:
        return False
    return any(_kw_regex(str(kw)).search(text_norm) for kw in keywords)


def remove_kw(text_norm: str, keywords) -> str:
    for kw in keywords or []:
        text_norm = _kw_regex(str(kw)).sub(" ", text_norm)
    return re.sub(r"\s+", " ", text_norm).strip()


_BLOCK_TAGS = {"p", "div", "br", "li", "ul", "ol", "h1", "h2", "h3", "h4", "h5", "h6",
               "tr", "table", "section", "article", "header", "footer"}


def html_to_text(html: str | None) -> str:
    """Convierte HTML a texto conservando saltos de línea y viñetas."""
    if not html:
        return ""
    if "<" not in html and "&" in html:
        html = _html.unescape(html)
    if "<" not in html:
        return _clean_lines(html)
    soup = BeautifulSoup(html, "html.parser")
    for t in soup(["script", "style", "noscript", "svg"]):
        t.decompose()
    for li in soup.find_all("li"):
        li.insert_before("\n• ")
    for br in soup.find_all("br"):
        br.replace_with("\n")
    for tag in soup.find_all(_BLOCK_TAGS):
        tag.insert_after("\n")
    return _clean_lines(soup.get_text())


def _clean_lines(text: str) -> str:
    lines = []
    for ln in text.replace("\r", "\n").split("\n"):
        ln = re.sub(r"[ \t\xa0]+", " ", ln).strip()
        if ln:
            lines.append(ln)
    out = "\n".join(lines)
    out = re.sub(r"(•\s*)+•", "•", out)
    return out


_ES_WORDS = {"de", "la", "el", "en", "y", "para", "con", "los", "las", "del", "una", "un", "que",
             "por", "tu", "nuestro", "nuestra", "buscamos", "experiencia", "equipo", "empresa",
             "funciones", "requisitos", "se", "es", "al", "como", "sus", "o"}
_CA_WORDS = {"i", "amb", "els", "les", "per", "una", "del", "que", "som", "busquem", "equip",
             "experiencia", "nostre", "nostra", "dels"}
_EN_WORDS = {"the", "and", "of", "to", "in", "for", "with", "you", "our", "we", "are", "is", "a",
             "will", "your", "experience", "team", "skills", "role", "about", "looking", "be", "as"}


def detect_lang(text: str) -> str:
    """'es' (castellano/catalán) o 'en'."""
    words = re.findall(r"[a-z]+", norm(text)[:4000])
    if not words:
        return "es"
    es = sum(w in _ES_WORDS for w in words)
    ca = sum(w in _CA_WORDS for w in words)
    en = sum(w in _EN_WORDS for w in words)
    return "en" if en > max(es, ca) else "es"


def truncate(s: str, n: int) -> str:
    s = (s or "").strip()
    return s if len(s) <= n else s[: n - 1].rstrip() + "…"
