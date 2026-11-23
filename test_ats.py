"""Parsers de páginas de empleo con respuestas simuladas (sin red)."""
import json

import jobwatch.sources.ats as A
from jobwatch.classify import Classifier
from jobwatch.config import load_config

C = Classifier(load_config())


class R:
    def __init__(self, text="", js=None, content=None):
        self.text = text
        self._js = js
        self.content = content if content is not None else text.encode()
        self.status_code = 200

    def json(self):
        return self._js

    def raise_for_status(self):
        pass


def ctx(company, budget=10):
    return A.Ctx(company, C.prelim, set(), A.Budget(budget))


def test_personio(monkeypatch):
    xml = b"""<?xml version="1.0"?><workzag-jobs><position><id>123</id><office>Barcelona</office>
    <name>Junior Influencer Marketing Manager</name><employmentType>permanent</employmentType>
    <schedule>full-time</schedule><createdAt>2026-11-20T10:00:00+00:00</createdAt>
    <jobDescriptions><jobDescription><name>Your tasks</name><value>&lt;ul&gt;&lt;li&gt;Influencers&lt;/li&gt;&lt;/ul&gt;</value></jobDescription></jobDescriptions>
    </position></workzag-jobs>"""
    monkeypatch.setattr(A, "get", lambda s, url, **k: R(content=xml))
    out = A.personio(ctx({"nombre": "Newflag", "id": "newflag", "sector": "Belleza", "ubicacion": "Barcelona"}))
    assert len(out) == 1
    o = out[0]
    assert o.url == "https://newflag.jobs.personio.de/job/123"
    assert o.location == "Barcelona" and o.workday == "full-time"
    e = C.evaluate(o)
    assert e.passes, e.discard_reason
    assert e.sector == "Belleza" and e.area == "PR"


def test_lever(monkeypatch):
    data = [{"text": "Content Manager - Permanent (F/M/X)", "hostedUrl": "https://jobs.lever.co/veepee/1",
             "categories": {"location": "Barcelona", "commitment": "Permanent"}, "createdAt": 1763900000000,
             "descriptionPlain": "Full time role in fashion e-commerce.", "lists": [{"text": "Must have", "content": "<li>Degree</li>"}]},
            {"text": "E-Merchandiser - Internship", "hostedUrl": "https://jobs.lever.co/veepee/2",
             "categories": {"location": "Barcelona", "commitment": "Internship"}, "createdAt": 1763900000000,
             "descriptionPlain": "x"}]
    monkeypatch.setattr(A, "get", lambda s, url, **k: R(js=data))
    out = A.lever(ctx({"nombre": "Veepee", "id": "veepee", "sector": ["Moda", "Belleza"], "ubicacion": "Barcelona"}))
    res = [C.evaluate(o) for o in out]
    assert res[0].passes, res[0].discard_reason
    assert not res[1].passes


def test_successfactors(monkeypatch):
    listing = """<table><tr class="data-row"><td><a class="jobTitle-link" href="/job/Barcelona-Trade-Marketing-Graduate/1287710701/">Trade Marketing Graduate</a></td>
      <td><span class="jobLocation">Barcelona, B, ES</span></td><td><span class="jobDate">20/11/2026</span></td></tr>
      <tr class="data-row"><td><a class="jobTitle-link" href="/job/Barcelona-Beauty-Advisor/1/">Beauty Advisor Barcelona</a></td>
      <td><span class="jobLocation">Barcelona, B, ES</span></td></tr></table>"""
    detail = """<html><span itemprop="description"><p>Provide support to the EMEA Trade Marketing Manager.</p>
      <p>Graduate contract: 1-year temporary contract. Full time.</p></span></html>"""

    def fake_get(s, url, **k):
        return R(text=detail if "/job/" in url else listing)

    monkeypatch.setattr(A, "get", fake_get)
    out = A.successfactors(ctx({"nombre": "Puig", "url": "https://jobs.puig.com", "sector": ["Belleza", "Moda"],
                                "ubicacion": "Barcelona"}))
    assert [o.title for o in out] == ["Trade Marketing Graduate", "Beauty Advisor Barcelona"]
    assert out[0].url == "https://jobs.puig.com/job/Barcelona-Trade-Marketing-Graduate/1287710701/"
    assert "EMEA Trade Marketing" in out[0].description
    assert out[1].description == ""      # no pasa el filtro por título: no se abre el detalle
    e = C.evaluate(out[0])
    assert e.passes and e.is_graduate and e.area == "Trade Marketing"


def test_html_with_jsonld(monkeypatch):
    listing = """<html><a href="/job_posting/creative-campaigns-content-specialist-321014">CREATIVE CAMPAIGNS &amp; CONTENT SPECIALIST</a>
      <a href="/job_posting/warehouse-operator-1">Warehouse Operator</a><a href="/">Inicio</a></html>"""
    jl = {"@context": "https://schema.org", "@type": "JobPosting", "title": "Creative Campaigns & Content Specialist",
          "description": "<p>Are you passionate about fashion?</p><p>Full time, permanent.</p>",
          "datePosted": "2026-11-18", "employmentType": "FULL_TIME",
          "jobLocation": {"@type": "Place", "address": {"addressLocality": "Barcelona", "addressRegion": "Barcelona"}}}
    detail = f'<html><script type="application/ld+json">{json.dumps(jl)}</script></html>'
    monkeypatch.setattr(A, "get", lambda s, url, **k: R(text=detail if "321014" in url else listing))
    out = A.factorial(ctx({"nombre": "Meller", "url": "https://mellerbrand.factorial.es", "sector": "Moda",
                           "ubicacion": "Barcelona"}))
    titles = {o.title for o in out}
    assert "Creative Campaigns & Content Specialist" in titles
    good = [o for o in out if "321014" in o.url][0]
    assert good.location.startswith("Barcelona") and good.workday == "FULL_TIME"
    e = C.evaluate(good)
    assert e.passes and e.area == "Comunicación/Contenido" and e.sector == "Moda"


def test_teamtailor_rss(monkeypatch):
    rss = b"""<?xml version="1.0"?><rss xmlns:tt="https://teamtailor.com/locations" version="2.0"><channel>
    <item><title>Social Media &amp; Web Content Specialist</title><description>&lt;p&gt;Fashion bridal brand. Full time.&lt;/p&gt;</description>
    <link>https://careers.pronovias.com/jobs/1-social</link><pubDate>Fri, 20 Nov 2026 10:00:00 +0100</pubDate>
    <remoteStatus>hybrid</remoteStatus><tt:locations><tt:location><tt:city>El Prat de Llobregat</tt:city></tt:location></tt:locations></item>
    </channel></rss>"""
    monkeypatch.setattr(A, "get", lambda s, url, **k: R(content=rss))
    out = A.teamtailor(ctx({"nombre": "Pronovias", "url": "https://careers.pronovias.com", "sector": "Moda",
                            "ubicacion": "El Prat"}))
    assert out[0].location == "El Prat de Llobregat" and out[0].modality == "Híbrido"
    e = C.evaluate(out[0])
    assert e.passes, e.discard_reason
