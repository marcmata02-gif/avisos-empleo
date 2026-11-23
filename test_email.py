from email.message import EmailMessage

from jobwatch.config import load_config
from jobwatch.sources.gmail_alerts import parse_html, parse_message

LINKEDIN_HTML = """
<html><body>
<table><tr><td>Tu alerta de empleo para marketing moda en Barcelona</td></tr></table>
<table class="job"><tr><td>
  <a href="https://www.linkedin.com/comm/jobs/view/3912345678/?trackingId=abc&refId=x">
    <img alt="logo" src="x.png"></a></td></tr>
  <tr><td><a href="https://www.linkedin.com/comm/jobs/view/3912345678/?trackingId=abc">Marketing Assistant</a></td></tr>
  <tr><td><p>Scalpers · Barcelona, Cataluña, España</p></td></tr>
  <tr><td><p>Solicitud sencilla</p></td></tr>
</table>
<table class="job"><tr><td>
  <a href="https://www.linkedin.com/comm/jobs/view/3999999999/?trackingId=def">Junior Trade Marketing</a></td></tr>
  <tr><td>Puig</td></tr>
  <tr><td>L'Hospitalet de Llobregat, Cataluña, España (Híbrido)</td></tr>
</table>
<a href="https://www.linkedin.com/comm/jobs/search?keywords=marketing">Ver todos los empleos</a>
<a href="https://www.linkedin.com/comm/psettings/email-unsubscribe">Darse de baja</a>
</body></html>
"""

INDEED_HTML = """
<html><body>
<table><tr><td>
 <a href="https://es.indeed.com/rc/clk/dl?jk=abcdef0123456789&from=ja&qd=x">Trade Marketing Junior</a><br>
 <span>L'Oréal</span><br><span>Barcelona, Barcelona provincia</span><br><span>25.000 € - 30.000 € al año</span>
</td></tr></table>
<table><tr><td>
 <a href="https://es.indeed.com/pagead/clk?mo=r&ad=xyz&jk=1234567890abcdef">Social Media Coordinator</a><br>
 <span>Desigual</span><br><span>Barcelona</span>
</td></tr></table>
</body></html>
"""


def test_linkedin_email():
    items = parse_html(LINKEDIN_HTML, "linkedin")
    assert len(items) == 2
    a, b = items
    assert a["title"] == "Marketing Assistant"
    assert a["company"] == "Scalpers"
    assert "Barcelona" in a["location"]
    assert a["url"] == "https://www.linkedin.com/jobs/view/3912345678/"
    assert b["title"] == "Junior Trade Marketing" and b["company"] == "Puig"
    assert "Hospitalet" in b["location"]


def test_indeed_email():
    items = parse_html(INDEED_HTML, "indeed")
    assert [i["title"] for i in items] == ["Trade Marketing Junior", "Social Media Coordinator"]
    assert items[0]["company"] == "L'Oréal"
    assert items[0]["url"] == "https://es.indeed.com/viewjob?jk=abcdef0123456789"
    assert "25.000" in items[0]["salary"]
    assert items[1]["company"] == "Desigual"


def test_parse_message_sets_flags():
    cfg = load_config().fuentes["gmail"]
    msg = EmailMessage()
    msg["From"] = "LinkedIn Job Alerts <jobalerts-noreply@linkedin.com>"
    msg["Subject"] = "“marketing moda”: 2 empleos nuevos en Barcelona"
    msg["Date"] = "Mon, 23 Nov 2026 08:00:00 +0100"
    msg.set_content("texto")
    msg.add_alternative(LINKEDIN_HTML, subtype="html")
    portal, offers = parse_message(msg, cfg)
    assert portal == "linkedin"
    assert len(offers) == 2
    assert all(o.implicit_fulltime and o.location_prefiltered for o in offers)
    assert offers[0].sector_hint == "Moda"
    assert offers[0].source == "LinkedIn"
