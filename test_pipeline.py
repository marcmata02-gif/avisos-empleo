"""Prueba de extremo a extremo con fuentes y base de datos simuladas."""
from datetime import datetime, timedelta, timezone
from types import SimpleNamespace

import jobwatch.main as M
import jobwatch.notify as N
import jobwatch.storage as S
from jobwatch.models import RawOffer

NOW = datetime.now(timezone.utc)


class FakeStore:
    def __init__(self):
        self.offers = {}
        self.states = {}

    def source_states(self):
        return dict(self.states)

    def load_index(self, days=150):
        return {k: dict(v) for k, v in self.offers.items()}

    def upsert(self, table, rows, on_conflict="id"):
        assert table == "offers"
        keys = {tuple(sorted(r.keys())) for r in rows}
        assert len(keys) <= 1, "todas las filas deben tener las mismas columnas"
        for r in rows:
            self.offers.setdefault(r["id"], {}).update(r)

    def patch(self, table, match, values):
        self.offers[match["id"]].update(values)

    def pending_notifications(self):
        rows = [o for o in self.offers.values() if o.get("passes") and o.get("aviso") is None]
        return sorted(rows, key=lambda r: -(r.get("priority") or 0))

    def save_source_state(self, rows):
        for r in rows:
            self.states[r["source"]] = r

    def cleanup(self):
        pass


SENT = []


class FakeTelegram:
    def __init__(self, *a, **k):
        pass

    def send_offer(self, o):
        N.format_offer(o)
        N.buttons(o, "https://example.github.io/app")
        SENT.append(o["title"])

    def send_text(self, t):
        SENT.append(t)


def fake_adzuna(cfg, a, b):
    return [
        RawOffer(source="Adzuna", title="Marketing Assistant (H/M)", url="https://adzuna/1", company="Desigual",
                 location="Barcelona", description="We are looking for... Full time. Fashion.",
                 published_at=NOW - timedelta(hours=2), location_prefiltered=True),
        RawOffer(source="Adzuna", title="Dependiente/a", url="https://adzuna/2", company="Desigual",
                 location="Barcelona", description="Jornada completa", published_at=NOW),
        RawOffer(source="Adzuna", title="Brand Manager", url="https://adzuna/3", company="Desigual",
                 location="Barcelona", description="Full time. Fashion brand.", published_at=NOW),
        RawOffer(source="Adzuna", title="Social Media Junior", url="https://adzuna/4", company="Desigual",
                 location="Barcelona", description="Full time fashion.", published_at=NOW - timedelta(days=20)),
    ]


def fake_infojobs(cfg, cid, sec, first, prelim, known):
    return [RawOffer(source="InfoJobs", title="Marketing Assistant", url="https://infojobs/of-i1",
                     company="DESIGUAL S.L.", location="Barcelona", description="Jornada completa. Moda.",
                     published_at=NOW - timedelta(hours=1), location_prefiltered=True)]


def test_pipeline(monkeypatch):
    store = FakeStore()
    monkeypatch.setattr(S, "Storage", lambda: store)
    monkeypatch.setattr(N, "Telegram", FakeTelegram)
    monkeypatch.setattr(M.adzuna, "fetch", fake_adzuna)
    monkeypatch.setattr(M.infojobs, "fetch", fake_infojobs)
    monkeypatch.setattr(M.ats, "fetch_company", lambda *a, **k: [])
    for k in ("ADZUNA_APP_ID", "ADZUNA_APP_KEY", "INFOJOBS_CLIENT_ID", "INFOJOBS_CLIENT_SECRET",
              "TELEGRAM_BOT_TOKEN", "TELEGRAM_CHAT_ID"):
        monkeypatch.setenv(k, "x")
    monkeypatch.delenv("GMAIL_USER", raising=False)
    args = SimpleNamespace(prueba=False, fuente="", probar_telegram=False)

    assert M.run(args) == 0
    passing = [o for o in store.offers.values() if o["passes"]]
    titles = sorted(o["title"] for o in passing)
    # La misma oferta de Adzuna e InfoJobs aparece una sola vez, con los dos enlaces
    merged = [o for o in passing if "Marketing Assistant" in o["title"]]
    assert len(merged) == 1
    assert {l["source"] for l in merged[0]["links"]} == {"Adzuna", "InfoJobs"}
    assert merged[0]["links"][0]["source"] == "InfoJobs"   # InfoJobs antes que Adzuna
    assert "Dependiente/a" not in titles
    # Brand Manager lleva aviso → solo en la web; Social Media de hace 20 días → no se avisa
    by_title = {o["title"]: o for o in store.offers.values()}
    assert by_title["Brand Manager"]["aviso"] == "solo_web"
    assert by_title["Social Media Junior"]["aviso"] == "omitido_antiguo"
    assert SENT == [merged[0]["title"]]

    # Segunda revisión: no se repite ningún aviso
    SENT.clear()
    store.states["adzuna"]["last_run"] = (NOW - timedelta(days=1)).isoformat()
    store.states["infojobs"]["last_run"] = (NOW - timedelta(days=1)).isoformat()
    assert M.run(args) == 0
    assert SENT == []
    assert len([o for o in store.offers.values() if "Marketing Assistant" in o["title"]]) == 1
