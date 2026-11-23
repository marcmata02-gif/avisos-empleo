"""Estructuras de datos."""
from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime


@dataclass
class RawOffer:
    """Oferta tal como llega de una fuente, antes de filtrar."""
    source: str                 # p. ej. "LinkedIn", "InfoJobs", "Puig (empresa)"
    title: str
    url: str
    company: str = ""
    location: str = ""
    description: str = ""       # texto plano (con saltos de línea)
    published_at: datetime | None = None
    salary: str = ""
    contract: str = ""          # indefinido, temporal, prácticas...
    workday: str = ""           # jornada completa / parcial (si la fuente lo da)
    modality: str = ""          # presencial / híbrido / remoto
    experience: str = ""        # "Al menos 2 años" (InfoJobs)
    sector_hint: str = ""       # sector por defecto de la fuente o empresa
    company_sectors: list[str] = field(default_factory=list)
    default_location: str = ""  # ubicación por defecto (empresa)
    location_prefiltered: bool = False  # la fuente ya filtra por Barcelona
    implicit_fulltime: bool = False     # p. ej. alertas creadas con filtro de jornada completa
    extra: dict = field(default_factory=dict)


@dataclass
class Evaluated:
    """Resultado de aplicar los criterios a una oferta."""
    passes: bool
    discard_reason: str = ""
    area: str = ""
    areas: list[str] = field(default_factory=list)
    sector: str = ""
    is_graduate: bool = False
    flags: list[str] = field(default_factory=list)       # códigos: experiencia, jornada, idioma
    flag_texts: list[str] = field(default_factory=list)  # textos para mostrar
    lang: str = "es"
    cv_id: int | None = None
    cv_note: str = ""
    jornada: str = ""
    modality: str = ""
    contract: str = ""
    summary: str = ""
    requirements: list[str] = field(default_factory=list)
    salary: str = ""
    location: str = ""
    priority: int = 0
