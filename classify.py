"""Aplica los criterios de criterios.yaml a cada oferta."""
from __future__ import annotations

import re

from .config import Config
from .models import Evaluated, RawOffer
from .text import detect_lang, find_kw, has_kw, norm, remove_kw, truncate

FLAG_TEXTS = {
    "experiencia": "Puede pedir más experiencia",
    "jornada": "Jornada no indicada",
}

_ROLE_SENTENCE = ["buscamos", "estamos buscando", "busquem", "we are looking", "we're looking",
                  "we are seeking", "is looking for", "are looking for", "seeking", "incorporar",
                  "your mission", "tu mision", "your main mission", "you will", "seras responsable",
                  "will be responsible", "the role", "el puesto", "la persona", "your role",
                  "en dependencia", "reporting to", "reportando"]

_REQ_HEADERS = re.compile(
    r"^(?:[\W\d]*)(requisitos|requirements|requerimientos|what we(?:'re| are) looking for|"
    r"que buscamos|lo que buscamos|que necesitamos|perfil|your profile|tu perfil|profile|"
    r"qualifications|we'?d love to meet you|what you need|what you'?ll need|what you bring|"
    r"must have|skills|competencias|who you are|about you|sobre ti|que pedimos|"
    r"is this you|this is you|requirements and skills|el candidato ideal|candidato ideal|"
    r"what do we need|que valoramos|formacion y experiencia|experience|requisits)\b"
)
_HEADER_LIKE = re.compile(r"^[^.!?]{2,60}:?$")

_SALARY_RE = re.compile(
    r"((?:\d{1,3}[.,]?\d{3}|\d{2}\s?k)\s*(?:€|eur|euros|k)?(?:\s*(?:-|–|a|to|y)\s*"
    r"(?:\d{1,3}[.,]?\d{3}|\d{2}\s?k)\s*(?:€|eur|euros|k)?)?\s*(?:€|eur|euros)?\s*"
    r"(?:brutos?|bruto/ano|gross|/\s*ano|/\s*year|al ano|per year|anual(?:es)?|b/a)?)",
)

_EXP_PATTERNS = [
    re.compile(r"(\d{1,2})\s*(?:\+|o mas|-\s*\d{1,2}|a\s+\d{1,2})?\s*anos?\s+(?:de\s+)?(?:experiencia|trayectoria)"),
    re.compile(r"experiencia\s+(?:minima\s+|previa\s+|demostrable\s+|profesional\s+)?(?:de\s+)?(?:al menos\s+|minimo\s+|mas de\s+)?(\d{1,2})\s*(?:\+|-\s*\d{1,2})?\s*anos"),
    re.compile(r"(?:al menos|minimo|minima)\s+(?:de\s+)?(\d{1,2})\s*anos"),
    re.compile(r"(\d{1,2})\s*\+?\s*(?:-|to)?\s*(?:\d{1,2})?\s*\+?\s*years?'?\s*(?:of\s+)?(?:[a-z/&,-]+\s+){0,5}?experience"),
    re.compile(r"(?:minimum|at least|min\.?)\s*(?:of\s+)?(\d{1,2})\s*\+?\s*years"),
    re.compile(r"experience\s*[:\-]\s*(?:at least\s+|minimum\s+)?(\d{1,2})\s*\+?\s*(?:-\s*\d{1,2})?\s*years"),
    re.compile(r"experiencia\s*[:\-]\s*(?:al menos\s+|minimo\s+)?(\d{1,2})\s*\+?\s*(?:-\s*\d{1,2})?\s*anos"),
]
_EXP_NEGATIVE = re.compile(r"(max|maximo|maxima|maximum|hasta|menos de|less than|no more than|up to|no mas de)\W*(?:\w+\W+){0,2}$")


class Classifier:
    def __init__(self, config: Config):
        self.cfg = config
        c = config.criterios
        self.c = c
        self.areas = c.get("areas") or []
        self.grad_kw = (c.get("graduate") or {}).get("palabras") or []
        self.nivel = c.get("nivel") or {}
        self.desc = c.get("descartar") or {}
        self.sector = c.get("sector") or {}
        self.ubic = c.get("ubicacion") or {}
        self.full_kw = c.get("jornada_completa") or []
        self.lang_cfg = c.get("idiomas_aviso") or {}
        self.cv = c.get("cv") or {}
        # índice de empresas: lista de (alias_normalizado, empresa)
        self.company_index: list[tuple[str, dict]] = []
        for e in config.empresas:
            names = [e.get("nombre", "")] + list(e.get("alias") or [])
            for n in names:
                n2 = norm(re.sub(r"\(.*?\)", "", n or ""))
                if len(n2) >= 3:
                    self.company_index.append((n2, e))
        self.company_index.sort(key=lambda x: -len(x[0]))

    # ------------------------------------------------------------------
    def find_company(self, name: str) -> dict | None:
        n = norm(name)
        if not n:
            return None
        for alias, e in self.company_index:
            if n == alias or has_kw(n, [alias]):
                return e
        return None

    # ------------------------------------------------------------------
    def _title_checks(self, title: str, graduate: bool) -> tuple[str, str]:
        """Descartes por título. Devuelve (motivo, '') o ('', título_limpio)."""
        t = norm(title)
        t_clean = remove_kw(t, self.desc.get("excepciones_titulo"))
        groups = [
            ("titulo_tienda", "Puesto de tienda / cara al público"),
            ("titulo_comercial_calle", "Puesto comercial de calle"),
            ("titulo_laboratorio_produccion", "Puesto de laboratorio, producción o calidad"),
            ("titulo_practicas", "Prácticas / beca"),
        ]
        for key, reason in groups:
            hit = find_kw(t_clean, self.desc.get(key))
            if hit:
                return f"{reason} ({hit[0]})", ""
        hit = find_kw(t_clean, self.desc.get("titulo_jornada"))
        if hit:
            temporal_only = all(norm(h) in {"temporal", "temporary", "fixed term", "fixed-term"} for h in hit)
            if not (graduate and temporal_only):
                return f"Jornada parcial o temporal ({hit[0]})", ""
        if not graduate:
            t_lvl = remove_kw(t_clean, self.nivel.get("excepciones_titulo"))
            hit = find_kw(t_lvl, self.nivel.get("descartar_titulo"))
            if hit:
                return f"Nivel senior / dirección ({hit[0]})", ""
        return "", t_clean

    def is_graduate(self, title: str, description: str = "") -> bool:
        if has_kw(norm(title), self.grad_kw):
            return True
        d = norm(description)[:6000]
        return has_kw(d, ["graduate program", "graduate programme", "programa graduate",
                          "graduate contract", "trainee program", "trainee programme",
                          "management trainee program", "programa de graduados"])

    def match_areas(self, text_norm: str) -> list[str]:
        return [a["nombre"] for a in self.areas if has_kw(text_norm, a.get("palabras"))]

    # ------------------------------------------------------------------
    def prelim(self, title: str) -> tuple[bool, str]:
        """Filtro rápido solo por título, antes de pedir el detalle de una oferta."""
        grad = has_kw(norm(title), self.grad_kw)
        reason, t_clean = self._title_checks(title, grad)
        if reason:
            return False, reason
        if not self.match_areas(norm(title)) and not grad:
            return False, "Fuera de tus áreas (título)"
        return True, ""

    # ------------------------------------------------------------------
    def detect_sector(self, raw: RawOffer, text_norm: str) -> str:
        company = self.find_company(raw.company)
        candidates: list[str] = []
        if company:
            s = company.get("sector")
            candidates = s if isinstance(s, list) else [s] if s else []
        elif raw.company_sectors:
            candidates = list(raw.company_sectors)
        if len(candidates) == 1:
            return candidates[0]
        cn = norm(raw.company)
        if not candidates:
            if has_kw(cn, self.sector.get("marcas_moda")):
                return "Moda"
            if has_kw(cn, self.sector.get("marcas_belleza")):
                return "Belleza"
            if raw.sector_hint:
                return raw.sector_hint
        moda = len(find_kw(text_norm, self.sector.get("palabras_moda")))
        belleza = len(find_kw(text_norm, self.sector.get("palabras_belleza")))
        if candidates:
            if "Moda" in candidates and "Belleza" in candidates:
                if moda > belleza:
                    return "Moda"
                if belleza > moda:
                    return "Belleza"
            return candidates[0]
        if moda == 0 and belleza == 0:
            return ""
        return "Moda" if moda >= belleza else "Belleza"

    # ------------------------------------------------------------------
    def location_ok(self, raw: RawOffer) -> tuple[bool, str]:
        loc = raw.location or ""
        accept = self.ubic.get("aceptar") or []
        ln = norm(loc)
        if ln and has_kw(ln, accept):
            return True, loc
        if ln:
            remote = has_kw(ln, ["remote", "remoto", "remota", "teletrabajo", "anywhere"])
            only_country = bool(re.fullmatch(r"(spain|espana|es|catalonia|cataluna|catalunya)([ ,\-]+(spain|espana|es))*", ln))
            if remote and self.ubic.get("descartar_solo_remoto", True):
                return False, loc
            if only_country or remote:
                if raw.default_location:
                    return True, raw.default_location
                if raw.location_prefiltered:
                    return True, loc
            return False, loc
        if raw.default_location:
            return True, raw.default_location
        return True, ""  # fuentes ya filtradas por Barcelona o alertas por email

    # ------------------------------------------------------------------
    def years_required(self, raw: RawOffer) -> int | None:
        best = None
        texts = []
        if raw.experience:
            texts.append(norm(raw.experience))
        if raw.description:
            texts.append(norm(raw.description)[:15000])
        for t in texts:
            for rx in _EXP_PATTERNS:
                for m in rx.finditer(t):
                    try:
                        n = int(m.group(1))
                    except (TypeError, ValueError):
                        continue
                    if n == 0 or n > 20:
                        continue
                    before = t[max(0, m.start() - 30): m.start()]
                    if _EXP_NEGATIVE.search(before):
                        continue
                    best = n if best is None else max(best, n)
        return best

    def required_languages(self, title: str, description: str) -> list[str]:
        langs = self.lang_cfg.get("idiomas") or {}
        must = self.lang_cfg.get("obligatorio") or []
        opt = self.lang_cfg.get("opcional") or []
        found: list[str] = []
        tn = norm(title)
        for name, words in langs.items():
            if has_kw(tn, words):
                found.append(name)
        sentences = re.split(r"[\n.;•]+", norm(description)[:15000])
        for s in sentences:
            if not s.strip():
                continue
            for name, words in langs.items():
                if name in found:
                    continue
                if has_kw(s, words) and has_kw(s, must) and not has_kw(s, opt):
                    found.append(name)
        return found

    # ------------------------------------------------------------------
    def summary(self, raw: RawOffer, area: str) -> str:
        text = raw.description or ""
        sentences = []
        for ln in text.split("\n"):
            ln = ln.strip("•-* ").strip()
            if len(ln) < 25 or _HEADER_LIKE.match(ln) and len(ln) < 45:
                continue
            sentences.extend(s.strip() for s in re.split(r"(?<=[.!?])\s+", ln) if len(s.strip()) > 25)
        for s in sentences:
            if has_kw(norm(s), _ROLE_SENTENCE):
                return truncate(s, 180)
        for s in sentences:
            ns = norm(s)
            if not has_kw(ns, ["sobre nosotros", "about us", "quienes somos", "who we are", "fundada", "founded"]):
                return truncate(s, 180)
        company = raw.company or "la empresa"
        return f"Puesto de {area or 'tu área'} en {company}."

    def requirements(self, raw: RawOffer) -> list[str]:
        lines = [ln.strip() for ln in (raw.description or "").split("\n") if ln.strip()]
        out: list[str] = []
        i = 0
        while i < len(lines) and len(out) < 5:
            ln = lines[i]
            ln_n = norm(ln.strip("•-* "))
            if len(ln_n) <= 70 and _REQ_HEADERS.match(ln_n):
                j = i + 1
                while j < len(lines) and len(out) < 5:
                    nxt = lines[j].strip()
                    nn = norm(nxt.strip("•-* "))
                    if len(nn) <= 60 and _HEADER_LIKE.match(nn) and not nxt.startswith("•") and j > i + 1:
                        break
                    item = nxt.strip("•-*· ").strip()
                    if 8 <= len(item) <= 400:
                        out.append(truncate(item, 150))
                    j += 1
                break
            i += 1
        if not out:
            extra = raw.extra.get("requirements_text") or ""
            for part in re.split(r"[\n•]+", extra):
                part = part.strip(" -*·")
                if len(part) >= 8:
                    out.append(truncate(part, 150))
                if len(out) >= 4:
                    break
        if not out:
            for ln in lines:
                ln2 = ln.strip("•-*· ").strip()
                if 15 <= len(ln2) <= 220 and has_kw(norm(ln2), ["experiencia", "experience", "ingles", "english",
                                                                  "grado", "degree", "titulacion", "licenciatura",
                                                                  "conocimientos", "knowledge"]):
                    out.append(truncate(ln2, 150))
                if len(out) >= 3:
                    break
        return out

    def salary(self, raw: RawOffer) -> str:
        if raw.salary:
            return raw.salary.strip()
        d = raw.description or ""
        for ln in d.split("\n"):
            lnn = norm(ln)
            if has_kw(lnn, ["salario", "salary", "sueldo", "retribucion", "remuneracion", "compensation",
                            "bruto", "brutos", "gross", "eur", "€"]) or "€" in ln:
                m = _SALARY_RE.search(lnn)
                if m and re.search(r"\d{2}", m.group(1)) and ("€" in ln or "eur" in lnn or "k" in m.group(1)):
                    val = m.group(1).strip()
                    if len(val) >= 4:
                        return truncate(val.replace("eur", "€"), 60)
        return ""

    def modality(self, raw: RawOffer, d: str) -> str:
        m = norm(raw.modality)
        src = m or d
        if has_kw(src, ["hibrido", "hibrida", "hybrid", "hibrid", "teletrabajo parcial", "days from home",
                        "dias de teletrabajo", "wfh", "dias en remoto", "days remote"]):
            return "Híbrido"
        if has_kw(src, ["solo teletrabajo", "100% remoto", "full remote", "fully remote", "remoto", "remote"]):
            return "Remoto" if m else ("Híbrido" if has_kw(d, ["oficina", "office"]) else "Remoto")
        if has_kw(src, ["presencial", "on-site", "onsite", "on site", "in-office", "in office", "en oficina"]):
            return "Presencial"
        return raw.modality or ""

    # ------------------------------------------------------------------
    def choose_cv(self, area: str, sector: str, lang: str, graduate: bool, title: str) -> tuple[int, str]:
        tn = norm(title)
        for rule in self.cv.get("reglas") or []:
            cond = rule.get("si") or {}
            if "area" in cond and area not in (cond["area"] or []):
                continue
            if "sector" in cond and sector != cond["sector"]:
                continue
            if "idioma" in cond and lang != cond["idioma"]:
                continue
            if "graduate" in cond and bool(cond["graduate"]) != graduate:
                continue
            if "titulo" in cond and not has_kw(tn, cond["titulo"]):
                continue
            return int(rule.get("cv")), rule.get("nota", "") or ""
        return int(self.cv.get("por_defecto", 6)), ""

    # ------------------------------------------------------------------
    def evaluate(self, raw: RawOffer) -> Evaluated:
        ev = Evaluated(passes=False)
        title = raw.title or ""
        desc = raw.description or ""
        tn = norm(title)
        dn = norm(desc)
        ev.is_graduate = self.is_graduate(title, desc)

        reason, t_clean = self._title_checks(title, ev.is_graduate)
        if reason:
            ev.discard_reason = reason
            return ev

        # Áreas
        areas = self.match_areas(tn)
        if not areas and ev.is_graduate:
            areas = self.match_areas(dn[:4000])
        if not areas:
            ev.discard_reason = "Fuera de tus áreas"
            return ev

        # Ubicación
        ok, loc = self.location_ok(raw)
        ev.location = loc
        if not ok:
            ev.discard_reason = f"Fuera de Barcelona ({raw.location})"
            return ev

        # Sector
        sector = self.detect_sector(raw, f"{tn} {norm(raw.company)} {dn[:8000]}")
        if not sector:
            ev.discard_reason = "Sector no reconocido (ni moda ni belleza)"
            return ev
        ev.sector = sector
        allowed = []
        area_cfg = {a["nombre"]: a for a in self.areas}
        for a in areas:
            secs = area_cfg.get(a, {}).get("sectores") or ["Moda", "Belleza"]
            if sector in secs:
                allowed.append(a)
        if not allowed:
            ev.discard_reason = f"{areas[0]} solo interesa en moda"
            return ev
        ev.areas = allowed
        ev.area = allowed[0]

        # Prácticas / becas en descripción o tipo de contrato
        cn = norm(raw.contract)
        if has_kw(cn, ["practicas", "internship", "intern", "beca", "becario", "stage", "alternance",
                       "apprenticeship", "convenio"]) or has_kw(dn, self.desc.get("descripcion_practicas")):
            ev.discard_reason = "Prácticas / beca (según contrato o descripción)"
            return ev

        # Contrato temporal
        if self.desc.get("descartar_contrato_temporal", True) and not ev.is_graduate:
            if (cn and has_kw(cn, self.desc.get("contrato_temporal"))) or (
                    not cn and has_kw(dn, self.desc.get("descripcion_temporal"))):
                ev.discard_reason = "Contrato temporal"
                return ev
        ev.contract = raw.contract

        # Jornada
        wn = norm(raw.workday)
        partial_kw = self.desc.get("descripcion_jornada_parcial") or []
        if wn and has_kw(wn, ["parcial", "part-time", "part time", "media jornada", "por horas", "partial"]) \
                and not has_kw(wn, ["completa", "full"]):
            ev.discard_reason = f"Jornada parcial ({raw.workday})"
            return ev
        if wn and has_kw(wn, ["completa", "full", "intensiva", "full-time", "full time"]):
            ev.jornada = "Jornada completa"
        elif has_kw(dn, self.full_kw) or has_kw(tn, self.full_kw):
            ev.jornada = "Jornada completa"
        elif has_kw(dn, partial_kw):
            ev.discard_reason = "Jornada parcial (según descripción)"
            return ev
        elif raw.implicit_fulltime:
            ev.jornada = "Jornada completa (filtro de la alerta)"
        else:
            ev.jornada = "Jornada no indicada"
            ev.flags.append("jornada")
            ev.flag_texts.append(FLAG_TEXTS["jornada"])

        # Experiencia
        years = self.years_required(raw)
        maxy = int(self.nivel.get("max_anos_experiencia", 3))
        if years is not None and years > maxy:
            ev.discard_reason = f"Pide {years} años de experiencia"
            return ev
        if has_kw(t_clean, self.nivel.get("marcar_titulo")) and not has_kw(tn, self.nivel.get("palabras_junior")) \
                and not ev.is_graduate:
            ev.flags.append("experiencia")
            ev.flag_texts.append(FLAG_TEXTS["experiencia"])

        # Idiomas
        langs = self.required_languages(title, desc)
        if langs:
            ev.flags.append("idioma")
            ev.flag_texts.append("Exige " + ", ".join(langs))

        # Resto de campos
        ev.lang = detect_lang(f"{title}\n{desc}" if desc else title)
        ev.modality = self.modality(raw, dn)
        ev.summary = self.summary(raw, ev.area)
        ev.requirements = self.requirements(raw)
        ev.salary = self.salary(raw)
        ev.cv_id, ev.cv_note = self.choose_cv(ev.area, ev.sector, ev.lang, ev.is_graduate, title)
        ev.priority = (20 if ev.sector == "Moda" else 5) + (15 if ev.is_graduate else 0) - 5 * len(ev.flags)
        ev.passes = True
        return ev
