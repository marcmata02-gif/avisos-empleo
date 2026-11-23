"""Revisión completa: recoge ofertas, las filtra, las guarda y avisa por Telegram.

Uso:
  python -m jobwatch.main                 # revisión normal (la lanza GitHub Actions)
  python -m jobwatch.main --prueba        # no guarda ni avisa: muestra lo que encontraría
  python -m jobwatch.main --fuente adzuna # solo una fuente (gmail, infojobs, adzuna, rss, empresas
                                          #   o el nombre de una empresa)
  python -m jobwatch.main --probar-telegram
"""
from __future__ import annotations

import argparse
import os
import sys
import traceback
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import datetime, timedelta, timezone

from .classify import Classifier
from .config import Config, load_config
from .dedupe import canonical_url, fingerprint
from .models import Evaluated, RawOffer
from .sources import ats, adzuna, infojobs, rss
from .sources.gmail_alerts import GmailSource, resolve_redirects
from .text import norm

LINK_ORDER = ["Web de la empresa", "InfoJobs", "LinkedIn", "Indeed", "FashionJobs", "FashionUnited",
              "InfoJobs (alerta)", "Email", "Adzuna"]

EVAL_COLUMNS = ["passes", "discard_reason", "area", "areas", "sector", "is_graduate", "flags", "flag_texts",
                "lang", "cv_id", "cv_name", "cv_note", "jornada", "modalidad", "contrato", "summary",
                "requirements", "salario", "ubicacion", "priority", "config_hash"]
RAW_COLUMNS = ["id", "title", "company", "description", "published_at", "links", "sources", "raw_location",
               "raw_salary", "raw_contract", "raw_workday", "raw_modality", "raw_experience", "sector_hint",
               "company_sectors", "default_location", "location_prefiltered", "implicit_fulltime",
               "requirements_text", "first_seen", "last_seen", "aviso"]


def now_utc() -> datetime:
    return datetime.now(timezone.utc)


def iso(dt: datetime | None) -> str | None:
    return dt.astimezone(timezone.utc).isoformat() if dt else None


def parse_iso(s) -> datetime | None:
    if not s:
        return None
    if isinstance(s, datetime):
        return s
    try:
        dt = datetime.fromisoformat(str(s).replace("Z", "+00:00"))
        return dt if dt.tzinfo else dt.replace(tzinfo=timezone.utc)
    except ValueError:
        return None


def log(*a):
    print(*a, flush=True)


# ---------------------------------------------------------------------------
def build_alias_map(cfg: Config) -> dict[str, str]:
    pairs = []
    for e in cfg.empresas:
        canon = norm(e.get("nombre", ""))
        for n in [e.get("nombre", "")] + list(e.get("alias") or []):
            n2 = norm(n.split("(")[0])
            if len(n2) >= 3:
                pairs.append((n2, canon))
    pairs.sort(key=lambda p: -len(p[0]))
    return dict(pairs)


def raw_from_row(row: dict) -> RawOffer:
    return RawOffer(
        source=(row.get("sources") or ["?"])[0], title=row.get("title") or "",
        url=((row.get("links") or [{}])[0]).get("url", ""), company=row.get("company") or "",
        location=row.get("raw_location") or "", description=row.get("description") or "",
        published_at=parse_iso(row.get("published_at")), salary=row.get("raw_salary") or "",
        contract=row.get("raw_contract") or "", workday=row.get("raw_workday") or "",
        modality=row.get("raw_modality") or "", experience=row.get("raw_experience") or "",
        sector_hint=row.get("sector_hint") or "", company_sectors=row.get("company_sectors") or [],
        default_location=row.get("default_location") or "",
        location_prefiltered=bool(row.get("location_prefiltered")),
        implicit_fulltime=bool(row.get("implicit_fulltime")),
        extra={"requirements_text": row.get("requirements_text") or ""},
    )


def merge_row(existing: dict | None, raw: RawOffer, fid: str, now: datetime) -> dict:
    row = {k: None for k in RAW_COLUMNS}
    if existing:
        row.update({k: existing.get(k) for k in RAW_COLUMNS if k in existing})
    row["id"] = fid
    from_company = raw.source == "Web de la empresa"

    links = list(row.get("links") or [])
    if raw.url and raw.url not in {l["url"] for l in links}:
        links.append({"source": raw.source, "url": raw.url})
    links.sort(key=lambda l: LINK_ORDER.index(l["source"]) if l["source"] in LINK_ORDER else 50)
    row["links"] = links
    row["sources"] = list(dict.fromkeys(l["source"] for l in links))

    def pick(col, val, prefer_new=False):
        if val in (None, "", []):
            return
        if prefer_new or not row.get(col):
            row[col] = val

    pick("title", raw.title, prefer_new=from_company)
    pick("company", raw.company, prefer_new=from_company)
    if len(raw.description or "") > len(row.get("description") or ""):
        row["description"] = raw.description
    pick("raw_location", raw.location, prefer_new=from_company)
    pick("raw_salary", raw.salary)
    pick("raw_contract", raw.contract, prefer_new=from_company)
    pick("raw_workday", raw.workday, prefer_new=from_company)
    pick("raw_modality", raw.modality)
    pick("raw_experience", raw.experience)
    pick("sector_hint", raw.sector_hint)
    pick("default_location", raw.default_location)
    pick("requirements_text", raw.extra.get("requirements_text"))
    secs = list(dict.fromkeys((row.get("company_sectors") or []) + list(raw.company_sectors or [])))
    row["company_sectors"] = secs
    row["location_prefiltered"] = bool(row.get("location_prefiltered")) or raw.location_prefiltered
    row["implicit_fulltime"] = bool(row.get("implicit_fulltime")) or raw.implicit_fulltime
    old_pub = parse_iso(row.get("published_at"))
    if raw.published_at and (not old_pub or raw.published_at < old_pub):
        row["published_at"] = iso(raw.published_at)
    row["first_seen"] = row.get("first_seen") or iso(now)
    row["last_seen"] = now.date().isoformat()   # solo la fecha: menos cambios en los archivos
    return row


def eval_columns(ev: Evaluated, cfg: Config) -> dict:
    names = cfg.cv_names()
    return {
        "passes": ev.passes, "discard_reason": ev.discard_reason, "area": ev.area, "areas": ev.areas,
        "sector": ev.sector, "is_graduate": ev.is_graduate, "flags": ev.flags, "flag_texts": ev.flag_texts,
        "lang": ev.lang, "cv_id": ev.cv_id, "cv_name": names.get(ev.cv_id or 0, ""), "cv_note": ev.cv_note,
        "jornada": ev.jornada, "modalidad": ev.modality, "contrato": ev.contract, "summary": ev.summary,
        "requirements": ev.requirements, "salario": ev.salary, "ubicacion": ev.location,
        "priority": ev.priority, "config_hash": cfg.hash,
    }


# ---------------------------------------------------------------------------
def is_due(state: dict | None, minutes: int, now: datetime) -> bool:
    if not state or not state.get("last_run"):
        return True
    last = parse_iso(state["last_run"])
    # margen de 5 min porque GitHub Actions no es puntual
    return not last or now - last >= timedelta(minutes=max(minutes - 5, 1))


def run(args) -> int:
    cfg = load_config()
    clf = Classifier(cfg)
    alias_map = build_alias_map(cfg)
    now = now_utc()
    dry = args.prueba

    store = None
    if not dry or args.probar_telegram:
        from .storage import Storage
        store = Storage()

    if args.probar_telegram:
        tg = telegram_for(store)
        tg.send_text("✅ <b>Bot de ofertas conectado.</b>\nA partir de ahora recibirás aquí las ofertas nuevas.")
        store.flush()
        log("Mensaje de prueba enviado.")
        return 0
    states = store.source_states() if store else {}
    index = store.load_index() if store else {}
    url_to_id = {}
    known_urls = set()
    for r in index.values():
        for l in r.get("links") or []:
            url_to_id[l["url"]] = r["id"]
            if len(r.get("description") or "") > 300:
                known_urls.add(l["url"])

    only = norm(args.fuente) if args.fuente else ""
    F = cfg.fuentes
    collected: list[RawOffer] = []
    new_states: list[dict] = []
    first_run_sources: set[str] = set()
    gmail: GmailSource | None = None

    def want(key: str) -> bool:
        conf = F.get(key) or {}
        if not conf.get("activa", True):
            return False
        if only:
            return only == key or (key == "empresas" and only not in {"gmail", "infojobs", "adzuna", "rss"})
        return is_due(states.get(key), int(conf.get("cada_minutos", 30)), now)

    def record(key: str, ok: bool, n: int, err: str = "", meta: dict | None = None):
        st = states.get(key) or {}
        new_states.append({
            "source": key, "last_run": iso(now),
            "last_ok": iso(now) if ok else st.get("last_ok"),
            "last_error": "" if ok else err[:500], "runs": int(st.get("runs") or 0) + 1,
            "meta": {**(st.get("meta") or {}), **(meta or {}), "ultimas_ofertas": n},
        })
        if not st.get("last_ok") and ok:
            first_run_sources.add(key)
        log(f"[{key}] {'OK' if ok else 'ERROR'} – {n} ofertas" + (f" – {err[:200]}" if err else ""))

    # ---------------- Gmail
    if want("gmail"):
        user, pw = os.environ.get("GMAIL_USER"), os.environ.get("GMAIL_APP_PASSWORD")
        if not user or not pw:
            log("[gmail] sin configurar (faltan GMAIL_USER / GMAIL_APP_PASSWORD)")
        else:
            try:
                gmail = GmailSource(F["gmail"], user, pw)
                found = gmail.fetch()
                resolve_redirects(found)
                collected += found
                record("gmail", True, len(found), meta={"por_portal": gmail.stats})
            except Exception as e:  # noqa: BLE001
                record("gmail", False, 0, f"{type(e).__name__}: {e}")
                if gmail:
                    gmail.close()
                gmail = None

    # ---------------- InfoJobs
    if want("infojobs"):
        cid, sec = os.environ.get("INFOJOBS_CLIENT_ID"), os.environ.get("INFOJOBS_CLIENT_SECRET")
        if not cid or not sec:
            log("[infojobs] sin configurar (faltan INFOJOBS_CLIENT_ID / INFOJOBS_CLIENT_SECRET)")
        else:
            try:
                first = not (states.get("infojobs") or {}).get("last_ok")
                found = infojobs.fetch(F["infojobs"], cid, sec, first, clf.prelim, known_urls)
                collected += found
                record("infojobs", True, len(found))
            except Exception as e:  # noqa: BLE001
                record("infojobs", False, 0, f"{type(e).__name__}: {e}")

    # ---------------- Adzuna
    if want("adzuna"):
        aid, akey = os.environ.get("ADZUNA_APP_ID"), os.environ.get("ADZUNA_APP_KEY")
        if not aid or not akey:
            log("[adzuna] sin configurar (faltan ADZUNA_APP_ID / ADZUNA_APP_KEY)")
        else:
            try:
                found = adzuna.fetch(F["adzuna"], aid, akey)
                collected += found
                record("adzuna", True, len(found))
            except Exception as e:  # noqa: BLE001
                record("adzuna", False, 0, f"{type(e).__name__}: {e}")

    # ---------------- RSS
    if want("rss") and (F.get("rss") or {}).get("feeds"):
        try:
            found = rss.fetch(F["rss"])
            collected += found
            record("rss", True, len(found))
        except Exception as e:  # noqa: BLE001
            record("rss", False, 0, f"{type(e).__name__}: {e}")

    # ---------------- Empresas
    if want("empresas"):
        conf = F.get("empresas") or {}
        companies = [c for c in cfg.empresas if (c.get("plataforma") or "pendiente") not in ("pendiente", "ninguna")]
        if only and only not in {"empresas"}:
            companies = [c for c in companies if only in norm(c.get("nombre", ""))]
        budget = ats.Budget(int(conf.get("max_detalles", 60)))
        timeout = int(conf.get("timeout_segundos", 20))
        with ThreadPoolExecutor(max_workers=int(conf.get("paralelo", 6))) as pool:
            futs = {pool.submit(ats.fetch_company, c, clf.prelim, known_urls, budget, timeout): c for c in companies}
            for fut in as_completed(futs):
                c = futs[fut]
                key = f"empresa:{c.get('nombre')}"
                try:
                    found = fut.result()
                    collected += found
                    record(key, True, len(found))
                except Exception as e:  # noqa: BLE001
                    record(key, False, 0, f"{type(e).__name__}: {e}")
        record("empresas", True, sum(1 for o in collected if o.source == "Web de la empresa"))

    # ---------------- Evaluar y unir duplicados
    changed: dict[str, dict] = {}
    passed_new = 0
    for raw in collected:
        if not raw.title or not raw.url:
            continue
        raw.title = raw.title.strip()
        raw.url = canonical_url(raw.url)
        fid = url_to_id.get(raw.url) or fingerprint(raw.title, raw.company or raw.url, alias_map)
        existing = changed.get(fid) or index.get(fid)
        is_new = existing is None
        row = merge_row(existing, raw, fid, now)
        ev = clf.evaluate(raw_from_row(row))
        row.update(eval_columns(ev, cfg))
        if is_new and raw.published_at is None and (
                raw.source == "Web de la empresa" and "empresas" in first_run_sources):
            row["aviso"] = "omitido_arranque"
        changed[fid] = row
        url_to_id[raw.url] = fid
        if is_new and ev.passes:
            passed_new += 1

    # ---------------- Si cambiaron los criterios, re-evaluar lo reciente
    cfg_state = states.get("config") or {}
    if not dry and (cfg_state.get("meta") or {}).get("hash") != cfg.hash and index:
        limit = now - timedelta(days=30)
        n = 0
        for fid, r in index.items():
            if fid in changed or (parse_iso(r.get("first_seen")) or now) < limit:
                continue
            row = {k: r.get(k) for k in RAW_COLUMNS}
            row.update(eval_columns(clf.evaluate(raw_from_row(row)), cfg))
            changed[fid] = row
            n += 1
        log(f"[config] criterios cambiados: re-evaluadas {n} ofertas recientes")

    passing = [r for r in changed.values() if r["passes"]]
    log(f"Total recogidas: {len(collected)} · nuevas que pasan el filtro: {passed_new} · "
        f"actualizadas: {len(changed)}")

    if dry:
        for r in sorted(passing, key=lambda r: -(r.get("priority") or 0))[:80]:
            flags = (" ⚠ " + ", ".join(r["flag_texts"])) if r["flag_texts"] else ""
            log(f"  ✔ [{r['sector']}/{r['area']}{'/GRADUATE' if r['is_graduate'] else ''}] "
                f"{r['title']} – {r['company']} ({r.get('ubicacion') or '?'}) CV{r['cv_id']}{flags}")
        reasons: dict[str, int] = {}
        for r in changed.values():
            if not r["passes"]:
                key = r["discard_reason"].split(" (")[0]
                reasons[key] = reasons.get(key, 0) + 1
        log("  Descartes: " + ", ".join(f"{k}: {v}" for k, v in sorted(reasons.items(), key=lambda x: -x[1])))
        if gmail:
            gmail.close()
        return 0

    # ---------------- Guardar
    assert store is not None
    store.upsert("offers", list(changed.values()))

    # ---------------- Avisar por Telegram
    sent = notify_pending(store, cfg, now)

    # ---------------- Estado para la web
    pendientes = [c.get("nombre") for c in cfg.empresas if (c.get("plataforma") or "pendiente") == "pendiente"]
    new_states.append({"source": "config", "last_run": iso(now), "last_ok": iso(now), "last_error": "",
                       "runs": int(cfg_state.get("runs") or 0) + 1,
                       "meta": {"hash": cfg.hash, "cv": {str(k): v for k, v in cfg.cv_names().items()},
                                "empresas_pendientes": pendientes, "enviadas_ultima": sent,
                                "areas": [a["nombre"] for a in cfg.criterios.get("areas") or []]}})
    store.save_source_state(new_states)

    # ---------------- Limpieza (una vez al día)
    cl = states.get("limpieza") or {}
    if is_due(cl, 24 * 60, now):
        try:
            store.cleanup()
            store.save_source_state([{"source": "limpieza", "last_run": iso(now), "last_ok": iso(now),
                                      "last_error": "", "runs": int(cl.get("runs") or 0) + 1, "meta": {}}])
        except Exception as e:  # noqa: BLE001
            log(f"[limpieza] {e}")
    store.flush()
    if gmail:
        gmail.commit()   # los emails se marcan como leídos solo después de guardar
    return 0


def telegram_for(store):
    """Crea el bot. Si no hay TELEGRAM_CHAT_ID, usa el chat que escribió al bot (y lo recuerda)."""
    from .notify import Telegram, discover_chat_id
    token = os.environ.get("TELEGRAM_BOT_TOKEN", "")
    if not token:
        raise RuntimeError("Falta el secreto TELEGRAM_BOT_TOKEN")
    st = store.source_states().get("telegram") or {}
    chat = os.environ.get("TELEGRAM_CHAT_ID") or (st.get("meta") or {}).get("telegram_chat_id")
    if not chat:
        chat = discover_chat_id(token)
        if not chat:
            raise RuntimeError("Escribe cualquier mensaje a tu bot en Telegram y vuelve a ejecutar.")
        store.save_source_state([{"source": "telegram", "last_run": iso(now_utc()), "last_ok": iso(now_utc()),
                                  "last_error": "", "runs": 1, "meta": {"telegram_chat_id": str(chat)}}])
    return Telegram(token=token, chat_id=str(chat))


def notify_pending(store, cfg: Config, now: datetime) -> int:
    tcfg = cfg.criterios.get("telegram") or {}
    max_days = int(tcfg.get("max_dias_antiguedad", 7))
    no_send = set(tcfg.get("no_enviar_si_aviso") or [])
    max_n = int(tcfg.get("max_por_revision", 25))
    pending = store.pending_notifications()
    if not pending:
        return 0
    tg = None
    if os.environ.get("TELEGRAM_BOT_TOKEN"):
        try:
            tg = telegram_for(store)
        except Exception as e:  # noqa: BLE001
            log(f"[telegram] {e}")
    sent = 0
    for o in pending:
        date = parse_iso(o.get("published_at")) or parse_iso(o.get("first_seen")) or now
        if now - date > timedelta(days=max_days):
            store.patch("offers", {"id": o["id"]}, {"aviso": "omitido_antiguo", "aviso_at": iso(now)})
            continue
        if no_send & set(o.get("flags") or []):
            store.patch("offers", {"id": o["id"]}, {"aviso": "solo_web", "aviso_at": iso(now)})
            continue
        if not tg or sent >= max_n:
            continue
        try:
            tg.send_offer(o)
            store.patch("offers", {"id": o["id"]}, {"aviso": "enviado", "aviso_at": iso(now)})
            sent += 1
        except Exception as e:  # noqa: BLE001
            log(f"[telegram] error con '{o.get('title')}': {e}")
    log(f"[telegram] enviados: {sent}")
    return sent


def main(argv=None) -> int:
    p = argparse.ArgumentParser(description="Avisos de ofertas de empleo")
    p.add_argument("--prueba", action="store_true", help="no guarda ni envía nada; muestra resultados")
    p.add_argument("--fuente", default="", help="solo esta fuente o empresa")
    p.add_argument("--probar-telegram", action="store_true", help="envía un mensaje de prueba")
    args = p.parse_args(argv)
    try:
        return run(args)
    except Exception:  # noqa: BLE001
        traceback.print_exc()
        return 1


if __name__ == "__main__":
    sys.exit(main())
