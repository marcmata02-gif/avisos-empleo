"""Carga de la configuración (archivos YAML de la carpeta config/)."""
from __future__ import annotations

import hashlib
import json
import os
from dataclasses import dataclass
from pathlib import Path

import yaml

ROOT = Path(__file__).resolve().parent.parent
CONFIG_DIR = Path(os.environ.get("JOBWATCH_CONFIG_DIR", ROOT / "config"))


@dataclass
class Config:
    criterios: dict
    fuentes: dict
    empresas: list[dict]

    @property
    def hash(self) -> str:
        """Huella de los criterios: si cambian, se re-evalúan las ofertas recientes."""
        blob = json.dumps({"c": self.criterios, "e": [
            {k: e.get(k) for k in ("nombre", "alias", "sector", "ubicacion")} for e in self.empresas
        ]}, sort_keys=True, ensure_ascii=False, default=str)
        return hashlib.sha1(blob.encode()).hexdigest()[:12]

    def cv_names(self) -> dict[int, str]:
        return {int(k): v for k, v in (self.criterios.get("cv", {}).get("versiones") or {}).items()}


def _load(name: str):
    with open(CONFIG_DIR / name, encoding="utf-8") as f:
        return yaml.safe_load(f) or {}


def load_config() -> Config:
    criterios = _load("criterios.yaml")
    fuentes = _load("fuentes.yaml")
    empresas = (_load("empresas.yaml").get("empresas") or [])
    _validate(criterios, empresas)
    return Config(criterios=criterios, fuentes=fuentes, empresas=empresas)


VALID_PLATFORMS = {
    "greenhouse", "greenhouse_eu", "lever", "lever_eu", "workable", "personio", "teamtailor",
    "smartrecruiters", "recruitee", "ashby", "successfactors", "workday", "factorial", "html",
    "pendiente", "ninguna",
}


def _validate(criterios: dict, empresas: list[dict]) -> None:
    errors = []
    for key in ("areas", "descartar", "sector", "cv", "nivel"):
        if key not in criterios:
            errors.append(f"criterios.yaml: falta la sección '{key}'")
    for i, e in enumerate(empresas):
        name = e.get("nombre") or f"#{i + 1}"
        p = (e.get("plataforma") or "pendiente").strip().lower()
        if p not in VALID_PLATFORMS:
            errors.append(f"empresas.yaml: '{name}' tiene una plataforma desconocida: {p}")
        if p in {"greenhouse", "greenhouse_eu", "lever", "lever_eu", "workable", "personio",
                 "smartrecruiters", "recruitee", "ashby"} and not e.get("id"):
            errors.append(f"empresas.yaml: '{name}' necesita 'id' para la plataforma {p}")
        if p in {"successfactors", "workday", "factorial", "html", "teamtailor"} and not e.get("url"):
            errors.append(f"empresas.yaml: '{name}' necesita 'url' para la plataforma {p}")
    if errors:
        raise ValueError("Errores en la configuración:\n - " + "\n - ".join(errors))
