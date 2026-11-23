

from jobwatch.classify import Classifier
from jobwatch.config import load_config
from jobwatch.dedupe import canonical_url, fingerprint
from jobwatch.main import build_alias_map
from jobwatch.models import RawOffer

CFG = load_config()
C = Classifier(CFG)


def ev(title, company="", desc="", **kw):
    kw.setdefault("location", "Barcelona")
    return C.evaluate(RawOffer(source="test", title=title, url="https://x/1", company=company,
                               description=desc, **kw))


EN_FT = "We are looking for a person to join our team in Barcelona. Full-time, permanent contract. " \
        "Requirements:\n• Degree in Marketing\n• Fluent English\n• 1-2 years of experience"
ES_FT = "Buscamos una persona para unirse a nuestro equipo en Barcelona. Jornada completa.\n" \
        "Requisitos:\n• Grado en ADE o Marketing\n• Experiencia de 2 años en el sector\n• Inglés avanzado"


def test_puig_graduate_temporal_passes():
    e = ev("EMEA Marketing Graduate", "Puig",
           "This one-year graduate program... Contract: 1-year temporary contract. Full-time. "
           "We are looking for a graduate to support regional marketing strategies.")
    assert e.passes, e.discard_reason
    assert e.is_graduate and e.sector == "Belleza" and e.area == "Marketing"
    assert e.cv_id == 2


def test_graduate_with_head_in_title():
    e = ev("CH Head of Digital Marketing Graduate", "Puig", "1-year temporary contract – dedicated for young talent. Full time.")
    assert e.passes, e.discard_reason
    assert e.is_graduate


def test_store_roles_discarded():
    assert not ev("Sales Assistant Barcelona 20h (fijo discontinuo) F/M", "Lacoste", EN_FT).passes
    assert not ev("Store Manager Full Time - Barcelona", "Fashion brand", EN_FT).passes
    assert not ev("Dependienta moda", "Mango", ES_FT).passes
    assert not ev("Beauty Advisor Barcelona", "Puig", EN_FT).passes


def test_store_word_in_description_is_ok():
    e = ev("Trade Marketing Specialist", "ISDIN",
           "Buscamos un/a especialista en trade marketing para coordinar activaciones en tienda y punto de venta. "
           "Jornada completa. Experiencia de 2 años.")
    assert e.passes, e.discard_reason
    assert e.area == "Trade Marketing" and e.sector == "Belleza" and e.cv_id == 4


def test_online_store_exception():
    e = ev("Online Store Specialist", "Mango", EN_FT)
    assert e.passes, e.discard_reason
    assert e.area == "E-commerce"


def test_senior_discarded_and_manager_flagged():
    assert not ev("Senior Brand Manager", "Desigual", EN_FT).passes
    e = ev("Brand Manager", "Desigual", EN_FT)
    assert e.passes and "experiencia" in e.flags
    assert "experiencia" not in ev("Assistant Brand Manager", "Desigual", EN_FT).flags
    assert "experiencia" in ev("Responsable de Comunicación", "Custo Barcelona", ES_FT).flags


def test_years_of_experience():
    assert not ev("Marketing Specialist", "Desigual", "Full time. At least 5 years of experience in fashion marketing.").passes
    assert ev("Marketing Specialist", "Desigual", "Full time. 3-5 years of experience in marketing.").passes
    assert ev("Marketing Specialist", "Desigual", "Full time. Experiencia mínima de 2-4 años en moda.").passes
    assert not ev("Marketing Specialist", "Desigual", "Jornada completa. Experiencia mínima de 4 años en moda.").passes
    e = ev("Marketing Graduate", "Puig", "Full time. Graduate contract: maximum 3 years of experience after graduation.")
    assert e.passes, e.discard_reason
    assert not ev("Social Media Specialist", "Mango", "Jornada completa", experience="Al menos 4 años").passes


def test_internships_discarded_even_if_graduate_word():
    assert not ev("PR & Press Assistant (Internship)", "Pronovias", EN_FT).passes
    assert not ev("Becario/a Marketing", "Tous", ES_FT).passes
    assert not ev("Marketing Intern", "Veepee", EN_FT).passes
    assert not ev("Marketing Assistant", "Veepee", EN_FT + " Internship agreement with your university required.").passes
    assert not ev("Content Manager", "Veepee", EN_FT, contract="Internship").passes


def test_international_is_not_intern():
    e = ev("International Marketing Coordinator", "Desigual", EN_FT)
    assert e.passes, e.discard_reason


def test_part_time_and_temporary():
    assert not ev("Event & Internal Communications Specialist - Fixed Term (W/M/X)", "Veepee", EN_FT).passes
    assert not ev("Digital Content Executive", "Pronovias", EN_FT, contract="Temporary").passes
    assert not ev("Comunicación y Marketing", "Mango", "Ofrecemos media jornada de lunes a viernes por la mañana.").passes
    assert not ev("Social Media Junior", "Tous", ES_FT, workday="Jornada parcial - mañana").passes
    assert not ev("Brand Marketing Specialist", "Pronovias", "Maternity cover. Full time.").passes


def test_no_jornada_flag_and_implicit():
    e = ev("Marketing Assistant", "Scalpers", "")
    assert e.passes and "jornada" in e.flags
    e2 = ev("Marketing Assistant", "Scalpers", "", implicit_fulltime=True)
    assert e2.passes and not e2.flags
    assert e2.jornada.startswith("Jornada completa")


def test_language_flag():
    e = ev("Social Media Specialist", "Desigual", EN_FT + "\nFluent German is a must.")
    assert e.passes and "idioma" in e.flags and "alemán" in e.flag_texts[0]
    e2 = ev("Social Media Specialist", "Desigual", EN_FT + "\nFrench or Italian would be a plus.")
    assert "idioma" not in e2.flags
    e3 = ev("Product Data Integration with Dutch - Permanent", "Veepee", EN_FT)
    assert not e3.passes or "idioma" in e3.flags


def test_compras_only_fashion():
    e = ev("Junior Buyer", "Desigual", EN_FT)
    assert e.passes and e.area == "Compras" and e.sector == "Moda"
    assert not ev("Junior Buyer", "ISDIN", EN_FT).passes


def test_sector_detection():
    assert not ev("Ecommerce Specialist", "Tech Solutions SL", EN_FT).passes
    e = ev("Ecommerce Specialist", "Unknown SL", EN_FT + " We are a sustainable fashion brand.")
    assert e.passes and e.sector == "Moda"
    e = ev("Marketing Assistant", "Unknown SL", ES_FT + " Somos una marca de cosmética natural.")
    assert e.passes and e.sector == "Belleza"
    e = ev("Marketing Assistant", "Unknown SL", "", sector_hint="Moda", implicit_fulltime=True)
    assert e.passes and e.sector == "Moda"


def test_puig_fashion_role_is_moda():
    e = ev("Fashion Merchandising - Graduate Program", "Puig",
           "E-Commerce Merchandising Graduate for Carolina Herrera fashion. Full time. Fashion collections and fashion house.")
    assert e.passes, e.discard_reason
    assert e.sector == "Moda"


def test_location():
    assert not ev("Marketing Assistant", "Desigual", EN_FT, location="Madrid").passes
    assert ev("Marketing Assistant", "Desigual", EN_FT, location="Palau-solità i Plegamans, Barcelona").passes
    assert not ev("Marketing Assistant", "Desigual", EN_FT, location="Remote").passes
    e = ev("Marketing Assistant", "Desigual", EN_FT, location="Spain", default_location="Barcelona")
    assert e.passes and e.location == "Barcelona"


def test_cv_rules():
    assert ev("Social Media & Content Specialist", "Desigual", EN_FT).cv_id == 1
    assert ev("Especialista de Contenido y Redes Sociales", "Desigual", ES_FT).cv_id == 3
    assert ev("Marketing Assistant", "Desigual", EN_FT).cv_id == 2
    assert ev("PR & Influencer Assistant", "Desigual", EN_FT).cv_id == 6
    assert ev("Graduate Program Marketing", "ISDIN", ES_FT).cv_id == 5
    assert ev("Trade Marketing Junior", "Puig", EN_FT).cv_id == 4


def test_summary_requirements_salary():
    e = ev("Marketing Assistant", "Desigual",
           "About us\nDesigual is a fashion brand.\nWe are looking for a Marketing Assistant to support campaigns.\n"
           "Requirements:\n• Degree in Marketing\n• Fluent English\nWhat we offer:\n• Salary: 26.000 - 30.000 € gross/year\nFull time")
    assert "looking for" in e.summary
    assert e.requirements[:2] == ["Degree in Marketing", "Fluent English"]
    assert "26.000" in e.salary


def test_fingerprint_dedupe():
    am = build_alias_map(CFG)
    a = fingerprint("Marketing Assistant (H/M)", "Mango Fashion Group", am)
    b = fingerprint("Marketing Assistant - Barcelona", "MANGO", am)
    assert a == b
    assert fingerprint("Content Manager", "Privalia", am) == fingerprint("Content Manager (W/M/X)", "Veepee", am)
    assert fingerprint("Content Manager", "Veepee", am) != fingerprint("Content Manager", "Desigual", am)
    assert fingerprint("Dependiente/a", "Natura Bissé", am) != fingerprint("Dependiente/a", "Natura Selection", am)


def test_canonical_url():
    assert canonical_url("https://www.linkedin.com/comm/jobs/view/3912345678/?trackingId=x&refId=y") == \
        "https://www.linkedin.com/jobs/view/3912345678/"
    assert canonical_url("https://es.indeed.com/rc/clk/dl?jk=abcdef0123456789&from=ja") == \
        "https://es.indeed.com/viewjob?jk=abcdef0123456789"
    assert canonical_url("https://jobs.puig.com/job/Barcelona-X/123/?utm_source=linkedin") == \
        "https://jobs.puig.com/job/Barcelona-X/123"


def test_prelim():
    assert C.prelim("Marketing Graduate")[0]
    assert C.prelim("Trade Marketing Specialist")[0]
    assert not C.prelim("Sales Associate")[0]
    assert not C.prelim("Software Engineer")[0]
    assert not C.prelim("Senior PR Manager")[0]
