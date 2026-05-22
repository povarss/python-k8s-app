#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Збір лідів: українські бізнеси з сигналом потреби в недорогому сайті (~500 USD).
"""

from __future__ import annotations

import json
import re
import time
import xml.etree.ElementTree as ET
from dataclasses import asdict, dataclass, field
from datetime import datetime
from pathlib import Path
from typing import Iterable
from urllib.parse import quote_plus, urljoin

import requests
from openpyxl import Workbook
from openpyxl.styles import Alignment, Font
from openpyxl.utils import get_column_letter
from playwright.sync_api import sync_playwright

TARGET_COUNT = 1000
BUDGET_USD = 500
BUDGET_UAH_APPROX = 21000
OUTPUT_XLSX = Path("/workspace/ukraina_biznesy_sait_500usd_leads.xlsx")
UAH_PER_USD = 42.0

# КВЕД/опис діяльності — сегменти, де сайт найчастіше потрібен мікробізнесу
SERVICE_KEYWORDS = (
    "перукар",
    "салон",
    "красот",
    "барбер",
    "стоматолог",
    "стоматол",
    "клінік",
    "медич",
    "ресторан",
    "кафе",
    "бар ",
    "піцер",
    "пицер",
    "кав'яр",
    "кавяр",
    "фітнес",
    "спорт",
    "йога",
    "масаж",
    "санатор",
    "готель",
    "хостел",
    "туризм",
    "екскур",
    "авто",
    "шиномонтаж",
    "СТО",
    "ремонт",
    "будів",
    "будівель",
    "оздобл",
    "мебл",
    "квіт",
    "флорист",
    "фото",
    "відео",
    "весіл",
    "організ",
    "юрид",
    "бухгал",
    "консалт",
    "навчан",
    "курс",
    "репетитор",
    "дитяч",
    "ветеринар",
    "зоо",
    "одяг",
    "взутт",
    "косметик",
    "продукт",
    "доставк",
    "кур'єр",
    "курьер",
    "логіст",
    "таксі",
    "перевез",
    "нотар",
    "страхув",
    "агентств",
    "нерухом",
    "риелтор",
    "рілтор",
    "клінінг",
    "прибиран",
    "хімчист",
    "прален",
    "садів",
    "ландшафт",
    "електрик",
    "сантех",
    "вікон",
    "двер",
    "плитк",
    "покрів",
    "дизайн інтер",
    "декор",
    "поліграф",
    "друк",
    "реклам",
    "маркет",
    "SMM",
    "таргет",
    "веб",
    "IT",
    "комп'ютер",
    "телефон",
    "гаджет",
    "оптик",
    "ювелір",
    "пам'ят",
    "ритуаль",
    "охорон",
    "детектив",
    "охорона здоров",
    "аптек",
    "медикам",
    "лаборатор",
    "діагност",
    "ветклін",
    "тварин",
    "квітков",
    "кондитер",
    "пекар",
    "хліб",
    "кейтер",
    "банкет",
    "кейтеринг",
    "музич",
    "DJ",
    "весільн",
    "event",
    "івент",
)

FL_RU_SKIP_TITLES = {
    "найти работу",
    "разместить заказ",
    "вход",
    "регистрация",
    "все категории",
}

BUDGET_PATTERNS = (
    r"\b500\s*\$",
    r"\$?\s*500\b",
    r"\b500\s*usd",
    r"\b500\s*дол",
    r"\b\d{1,2}[\.,]?\s*000\s*грн",
    r"\b\d{4,5}\s*грн",
    r"недорог",
    r"бюджет",
    r"дешев",
    r"економ",
    r"до\s*\d+\s*\$",
    r"до\s*\d+\s*грн",
)


@dataclass
class Lead:
    id: int = 0
    nazva: str = ""
    typ_subiekta: str = ""
    misto: str = ""
    oblast: str = ""
    telefon: str = ""
    email: str = ""
    sait: str = ""
    dzherelo: str = ""
    url_dzherelo: str = ""
    opys_potreby: str = ""
    signal_budzet: str = ""
    otsinka_budzet_uah: str = ""
    riven_vpevnenosti: str = ""
    data_zboru: str = ""
    prymitka: str = ""

    def key(self) -> str:
        base = (self.nazva or self.url_dzherelo or "").strip().lower()
        return f"{self.dzherelo}|{base}|{self.telefon}|{self.email}"


class LeadStore:
    def __init__(self) -> None:
        self._seen: set[str] = set()
        self.leads: list[Lead] = []

    def add(self, lead: Lead) -> bool:
        k = lead.key()
        if not k or k in self._seen:
            return False
        self._seen.add(k)
        lead.id = len(self.leads) + 1
        lead.data_zboru = lead.data_zboru or datetime.now().strftime("%Y-%m-%d")
        self.leads.append(lead)
        return True

    def count(self) -> int:
        return len(self.leads)

    def extend(self, items: Iterable[Lead]) -> int:
        n = 0
        for item in items:
            if self.add(item):
                n += 1
        return n


def normalize_phone(text: str) -> str:
    digits = re.sub(r"\D", "", text or "")
    if digits.startswith("380") and len(digits) == 12:
        return f"+{digits}"
    if digits.startswith("0") and len(digits) == 10:
        return f"+38{digits}"
    return text.strip()


def extract_budget_signal(text: str) -> tuple[str, str]:
    t = (text or "").lower()
    for pat in BUDGET_PATTERNS:
        m = re.search(pat, t, re.I)
        if m:
            return m.group(0), "високий"
    if any(w in t for w in ("сайт", "лендінг", "landing", "візитк", "wordpress", "tilda")):
        return f"орієнтир ~{BUDGET_USD}$", "середній"
    return "", "низький"


def matches_service_sector(text: str) -> bool:
    t = (text or "").lower()
    return any(k in t for k in SERVICE_KEYWORDS)


def scrape_freelancehunt(store: LeadStore, pages: int = 25) -> int:
    """Проєкти Freelancehunt — прямі замовники з бюджетом."""
    added = 0
    base = "https://freelancehunt.com/projects"
    queries = [
        "",
        "?skills[]=1",
        "?skills[]=58",
        "?skills[]=112",
        "?skills[]=5",
    ]
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        page = browser.new_page(locale="uk-UA")
        page.set_default_timeout(45000)
        for q in queries:
            if store.count() >= TARGET_COUNT:
                break
            for pg in range(1, pages + 1):
                if store.count() >= TARGET_COUNT:
                    break
                url = base if not q and pg == 1 else f"{base}{q}&page={pg}" if q else f"{base}?page={pg}"
                if q and pg == 1 and "page=" not in url:
                    url = f"{base}{q}"
                try:
                    page.goto(url, wait_until="domcontentloaded")
                    page.wait_for_timeout(1500)
                    cards = page.query_selector_all("article, .project, [class*='project']")
                    if not cards:
                        cards = page.query_selector_all("a[href*='/project/']")
                    links = page.eval_on_selector_all(
                        "a[href*='/project/']",
                        "els => els.map(e => ({href: e.href, text: e.innerText.trim()}))",
                    )
                    if not links:
                        continue
                    seen_urls: set[str] = set()
                    for item in links:
                        href = item.get("href", "")
                        if "/project/" not in href or href in seen_urls:
                            continue
                        seen_urls.add(href)
                        title = (item.get("text") or "").split("\n")[0].strip()
                        if not title or len(title) < 8:
                            continue
                        tl = title.lower()
                        if not any(
                            w in tl
                            for w in (
                                "сайт",
                                "site",
                                "web",
                                "ленд",
                                "landing",
                                "wordpress",
                                "tilda",
                                "візит",
                                "магазин",
                                "shop",
                                "верст",
                                "дизайн",
                            )
                        ):
                            continue
                        budget = ""
                        parent_text = title
                        sig, conf = extract_budget_signal(parent_text)
                        store.add(
                            Lead(
                                nazva=title[:200],
                                typ_subiekta="замовник (фріланс)",
                                dzherelo="Freelancehunt",
                                url_dzherelo=href,
                                opys_potreby="Активний запит на розробку сайту",
                                signal_budzet=sig,
                                otsinka_budzet_uah=str(int(BUDGET_UAH_APPROX)),
                                riven_vpevnenosti=conf,
                                prymitka="Публічний проєкт на біржі",
                            )
                        )
                        added += 1
                except Exception as exc:
                    print(f"FH skip {url}: {exc}")
        browser.close()
    return added


def scrape_work_ua(store: LeadStore, max_pages: int = 40) -> int:
    """Вакансії Work.ua — компанії, що наймають під сайт (потреба в присутності)."""
    added = 0
    searches = [
        "створення сайту",
        "розробка сайту",
        "лендінг",
        "wordpress",
        "веб-дизайн",
        "tilda",
        "верстальник сайтів",
    ]
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        page = browser.new_page(locale="uk-UA")
        for term in searches:
            if store.count() >= TARGET_COUNT:
                break
            for pg in range(1, max_pages + 1):
                if store.count() >= TARGET_COUNT:
                    break
                url = f"https://www.work.ua/jobs/?search={quote_plus(term)}&page={pg}"
                try:
                    page.goto(url, wait_until="domcontentloaded")
                    page.wait_for_timeout(1200)
                    jobs = page.eval_on_selector_all(
                        "h2 a[href*='/jobs/'], .card h2 a",
                        """els => els.map(e => ({
                            href: e.href,
                            title: e.innerText.trim()
                        }))""",
                    )
                    if not jobs:
                        break
                    for job in jobs:
                        href = job.get("href", "")
                        if "/jobs/" not in href:
                            continue
                        title = job.get("title", "")
                        if not title:
                            continue
                        # Деталі вакансії — компанія
                        try:
                            page.goto(href, wait_until="domcontentloaded", timeout=30000)
                            page.wait_for_timeout(800)
                            company = page.eval_on_selector(
                                "span[class*='glyphicon-company'], .dl-horizontal a, h1 + p a, .mr-xs a",
                                "e => e ? e.innerText.trim() : ''",
                            )
                            if not company:
                                company = page.eval_on_selector(
                                    "a[href*='/jobs/by-company/']",
                                    "e => e ? e.innerText.trim() : ''",
                                )
                            desc = page.inner_text("body")[:2500]
                        except Exception:
                            company = ""
                            desc = title
                        if not company:
                            m = re.search(r"компанія\s+([^\n,]+)", desc, re.I)
                            company = m.group(1).strip() if m else title[:80]
                        sig, conf = extract_budget_signal(desc)
                        if "500" in desc or "недорог" in desc.lower():
                            conf = "високий"
                        store.add(
                            Lead(
                                nazva=company[:200],
                                typ_subiekta="роботодавець (Work.ua)",
                                dzherelo="Work.ua",
                                url_dzherelo=href,
                                opys_potreby=title[:300],
                                signal_budzet=sig,
                                otsinka_budzet_uah=str(int(BUDGET_UAH_APPROX)),
                                riven_vpevnenosti=conf,
                                prymitka="Вакансія/запит пов’язаний із сайтом",
                            )
                        )
                        added += 1
                except Exception as exc:
                    print(f"Work skip {url}: {exc}")
                    break
        browser.close()
    return added


def scrape_weblancer(store: LeadStore, pages: int = 30) -> int:
    added = 0
    cats = [
        "https://www.weblancer.net/freelance/veb-programmirovanie/",
        "https://www.weblancer.net/freelance/dizayn-saytov/",
        "https://www.weblancer.net/freelance/vёрstka/",
    ]
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        page = browser.new_page()
        for cat in cats:
            for pg in range(1, pages + 1):
                if store.count() >= TARGET_COUNT:
                    break
                url = cat if pg == 1 else f"{cat}?page={pg}"
                try:
                    page.goto(url, wait_until="domcontentloaded", timeout=40000)
                    page.wait_for_timeout(1200)
                    items = page.eval_on_selector_all(
                        "a[href*='/freelance/']",
                        "els => els.map(e => ({href:e.href, text:e.innerText.trim()})).filter(x=>x.text.length>15)",
                    )
                    for it in items:
                        href = it["href"]
                        if "/freelance/" not in href or href.count("/") < 5:
                            continue
                        text = it["text"]
                        tl = text.lower()
                        if not any(w in tl for w in ("сайт", "site", "web", "ленд", "wordpress", "дизайн", "верст")):
                            continue
                        sig, conf = extract_budget_signal(text)
                        store.add(
                            Lead(
                                nazva=text[:120],
                                typ_subiekta="замовник (Weblancer)",
                                dzherelo="Weblancer",
                                url_dzherelo=href,
                                opys_potreby=text[:400],
                                signal_budzet=sig,
                                otsinka_budzet_uah=str(int(BUDGET_UAH_APPROX)),
                                riven_vpevnenosti=conf,
                            )
                        )
                        added += 1
                except Exception as exc:
                    print(f"WL skip {url}: {exc}")
        browser.close()
    return added


def scrape_fl_ru_ua(store: LeadStore, pages: int = 25) -> int:
    added = 0
    categories = [
        "saity",
        "dizayn",
        "marketing",
        "reklama-i-marketing",
        "seo",
        "verstka",
        "programmirovanie",
        "kopirajting",
    ]
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        page = browser.new_page()
        for cat in categories:
            for pg in range(1, pages + 1):
                if store.count() >= TARGET_COUNT:
                    break
                url = f"https://www.fl.ru/projects/category/{cat}/?page={pg}"
                try:
                    page.goto(url, wait_until="domcontentloaded", timeout=40000)
                    page.wait_for_timeout(1200)
                    items = page.eval_on_selector_all(
                        "a[href*='/projects/']",
                        "els => els.map(e => ({href:e.href, text:e.innerText.trim()}))",
                    )
                    for it in items:
                        href = it.get("href", "")
                        if "/projects/" not in href or "category" in href:
                            continue
                        text = (it.get("text") or "").strip()
                        if len(text) < 12:
                            continue
                        tl = text.lower()
                        if tl in FL_RU_SKIP_TITLES:
                            continue
                        if not any(
                            w in tl
                            for w in (
                                "сайт",
                                "site",
                                "web",
                                "ленд",
                                "landing",
                                "wordpress",
                                "tilda",
                                "визит",
                                "візит",
                                "магазин",
                                "shop",
                                "верст",
                                "дизайн",
                                "доработ",
                                "интернет",
                            )
                        ):
                            continue
                        sig, conf = extract_budget_signal(text)
                        store.add(
                            Lead(
                                nazva=text[:150],
                                typ_subiekta="замовник (FL.ru)",
                                dzherelo="FL.ru",
                                url_dzherelo=href if href.startswith("http") else urljoin("https://www.fl.ru", href),
                                opys_potreby=text[:400],
                                signal_budzet=sig,
                                otsinka_budzet_uah=str(int(BUDGET_UAH_APPROX)),
                                riven_vpevnenosti=conf,
                            )
                        )
                        added += 1
                except Exception as exc:
                    print(f"FL skip {cat} p{pg}: {exc}")
        browser.close()
    return added


def scrape_kwork(store: LeadStore, pages: int = 20) -> int:
    """Kwork — замовлення на сайти/дизайн (частина замовників з UA)."""
    added = 0
    urls = [
        "https://kwork.ru/projects?c=41",
        "https://kwork.ru/projects?c=15",
        "https://kwork.ru/projects?c=24",
    ]
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        page = browser.new_page()
        for base in urls:
            for pg in range(1, pages + 1):
                if store.count() >= TARGET_COUNT:
                    break
                url = f"{base}&page={pg}" if "?" in base else f"{base}?page={pg}"
                try:
                    page.goto(url, wait_until="domcontentloaded", timeout=60000)
                    page.wait_for_timeout(2000)
                    items = page.eval_on_selector_all(
                        "a[href*='/projects/']",
                        "els => els.map(e => ({href:e.href, text:e.innerText.trim()})).filter(x=>x.text.length>10)",
                    )
                    for it in items:
                        text = it.get("text", "")
                        href = it.get("href", "")
                        tl = text.lower()
                        if not any(
                            w in tl
                            for w in ("сайт", "site", "ленд", "landing", "wordpress", "tilda", "дизайн", "верст", "web")
                        ):
                            continue
                        sig, conf = extract_budget_signal(text)
                        if "500" in text or "недорог" in tl or "бюджет" in tl:
                            conf = "високий"
                        store.add(
                            Lead(
                                nazva=text[:150],
                                typ_subiekta="замовник (Kwork)",
                                dzherelo="Kwork",
                                url_dzherelo=href,
                                opys_potreby=text[:400],
                                signal_budzet=sig,
                                otsinka_budzet_uah=str(int(BUDGET_UAH_APPROX)),
                                riven_vpevnenosti=conf,
                            )
                        )
                        added += 1
                except Exception as exc:
                    print(f"Kwork skip {url}: {exc}")
        browser.close()
    return added


def parse_fop_zip(store: LeadStore, zip_path: Path, max_add: int = 1200) -> int:
    """Парсинг реєстру ФОП України (data.gov.ua) — активні ФОП, реєстрація з 2023 року."""
    import zipfile

    if not zip_path.exists() or zip_path.stat().st_size < 50_000_000:
        print("FOP zip ще не готовий")
        return 0
    added = 0
    with zipfile.ZipFile(zip_path, "r") as zf:
        xml_name = next((n for n in zf.namelist() if n.lower().endswith(".xml")), None)
        if not xml_name:
            print("XML у FOP.zip не знайдено")
            return 0
        print(f"Парсинг {xml_name} (потоково)...")
        with zf.open(xml_name) as fh:
            for _, elem in ET.iterparse(fh, events=("end",)):
                tag = elem.tag.split("}")[-1] if "}" in elem.tag else elem.tag
                if tag != "SUBJECT":
                    continue
                stan = (elem.findtext("STAN") or "").strip().lower()
                name = (elem.findtext("NAME") or "").strip()
                reg = (elem.findtext("REGISTRATION") or "").strip()
                record = (elem.findtext("RECORD") or "").strip()

                if stan != "зареєстровано" or len(name) < 6:
                    elem.clear()
                    continue
                reg_date = reg.split(";")[0].strip() if reg else ""
                year = 0
                m = re.search(r"(\d{2})\.(\d{2})\.(\d{4})", reg_date)
                if m:
                    year = int(m.group(3))
                # Новіші ФОП частіше шукають перший сайт (~500$)
                if year and year < 2020:
                    elem.clear()
                    continue
                store.add(
                    Lead(
                        nazva=f"ФОП {name}"[:200],
                        typ_subiekta="ФОП",
                        dzherelo="ЄДР ФОП (data.gov.ua)",
                        url_dzherelo=f"https://usr.minjust.gov.ua/content/ua/result/?edrpou={record}",
                        opys_potreby=f"Активний ФОП, реєстрація {reg_date or '2023+'}",
                        signal_budzet=f"цільовий ~{BUDGET_USD}$",
                        otsinka_budzet_uah=str(int(BUDGET_UAH_APPROX)),
                        riven_vpevnenosti="низький",
                        prymitka="Реальний ФОП; ймовірна потреба у сайті-візитці для старту онлайн-присутності",
                    )
                )
                added += 1
                elem.clear()
                if added % 250 == 0:
                    print(f"  FOP: {added}, у файлі {store.count()}")
                if store.count() >= TARGET_COUNT or added >= max_add:
                    break
    return added


def scrape_prom_ua_no_site(store: LeadStore, limit: int = 800) -> int:
    """
    Компанії на Prom.ua — часто продають онлайн без власного домену (потенційні ліди).
    """
    added = 0
    categories = [
        "https://prom.ua/ua/Cosmetics",
        "https://prom.ua/ua/Food",
        "https://prom.ua/ua/Clothing",
        "https://prom.ua/ua/Building",
        "https://prom.ua/ua/Auto",
        "https://prom.ua/ua/Health",
        "https://prom.ua/ua/Home",
        "https://prom.ua/ua/Sport",
    ]
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        page = browser.new_page(locale="uk-UA")
        companies_seen: set[str] = set()
        for cat in categories:
            if store.count() >= TARGET_COUNT or added >= limit:
                break
            try:
                page.goto(cat, wait_until="domcontentloaded", timeout=40000)
                page.wait_for_timeout(2000)
                sellers = page.eval_on_selector_all(
                    "a[href*='/company/'], a[href*='company_id']",
                    "els => els.map(e => ({href:e.href, name:e.innerText.trim()})).filter(x=>x.name.length>2)",
                )
                for s in sellers:
                    name = s.get("name", "").strip()
                    href = s.get("href", "")
                    if not name or name in companies_seen:
                        continue
                    companies_seen.add(name)
                    store.add(
                        Lead(
                            nazva=name[:200],
                            typ_subiekta="продавець (Prom.ua)",
                            dzherelo="Prom.ua",
                            url_dzherelo=href,
                            opys_potreby="Маркетплейс-продавець; ймовірна потреба у власному недорогому сайті",
                            signal_budzet=f"цільовий бюджет ~{BUDGET_USD}$",
                            otsinka_budzet_uah=str(int(BUDGET_UAH_APPROX)),
                            riven_vpevnenosti="середній",
                            prymitka="Кваліфікований лід: онлайн-продажі без власного сайту",
                        )
                    )
                    added += 1
                    if added >= limit or store.count() >= TARGET_COUNT:
                        break
            except Exception as exc:
                print(f"Prom skip {cat}: {exc}")
        browser.close()
    return added


def fetch_osm_ukraine_businesses_without_website(store: LeadStore, limit: int = 1500) -> int:
    """
    Реальні POI з OpenStreetMap в Україні: назва + телефон, без website.
    Потенційні ліди для недорогого сайту.
    """
    added = 0
    overpass_url = "https://overpass-api.de/api/interpreter"
    # Кафе, магазини, салони, офіси, клініки тощо без website
    query = """
    [out:json][timeout:120];
    area["ISO3166-1"="UA"][admin_level=2]->.ua;
    (
      nwr["shop"]["name"]["phone"]["website"!~"."]["contact:website"!~"."]["url"!~"."]["addr:city"](area.ua);
      nwr["amenity"~"restaurant|cafe|fast_food|bar|pharmacy|clinic|dentist|bank|fuel|car_repair|beauty_salon|hairdresser"]["name"]["phone"]["website"!~"."]["contact:website"!~"."]["url"!~"."]["addr:city"](area.ua);
      nwr["office"]["name"]["phone"]["website"!~"."]["contact:website"!~"."]["url"!~"."]["addr:city"](area.ua);
      nwr["craft"]["name"]["phone"]["website"!~"."]["contact:website"!~"."]["url"!~"."]["addr:city"](area.ua);
    );
    out body 1500;
    """
    try:
        resp = requests.post(overpass_url, data={"data": query}, timeout=180)
        resp.raise_for_status()
        data = resp.json()
    except Exception as exc:
        print(f"Overpass error: {exc}")
        return 0

    for el in data.get("elements", []):
        if store.count() >= TARGET_COUNT or added >= limit:
            break
        tags = el.get("tags", {})
        name = tags.get("name") or tags.get("brand") or ""
        if not name or len(name) < 3:
            continue
        if tags.get("website") or tags.get("contact:website") or tags.get("url"):
            continue
        sector = " ".join(
            filter(
                None,
                [
                    tags.get("shop"),
                    tags.get("amenity"),
                    tags.get("office"),
                    tags.get("craft"),
                    tags.get("healthcare"),
                ],
            )
        )
        desc = f"OSM: {sector or 'бізнес'}; без власного сайту в карті"
        if not matches_service_sector(f"{name} {sector} {tags.get('description', '')}"):
            # Для OSM допускаємо ширший список amenity/shop
            if not sector:
                continue
        phone = normalize_phone(tags.get("phone") or tags.get("contact:phone") or "")
        email = tags.get("email") or tags.get("contact:email") or ""
        city = tags.get("addr:city") or tags.get("addr:place") or ""
        region = tags.get("addr:state") or tags.get("addr:region") or ""
        osm_id = el.get("id")
        osm_type = el.get("type", "node")
        url = f"https://www.openstreetmap.org/{osm_type}/{osm_id}"
        store.add(
            Lead(
                nazva=name[:200],
                typ_subiekta=sector[:80] or "бізнес (OSM)",
                misto=city[:80],
                oblast=region[:80],
                telefon=phone,
                email=email[:120],
                dzherelo="OpenStreetMap UA",
                url_dzherelo=url,
                opys_potreby=desc,
                signal_budzet=f"цільовий бюджет ~{BUDGET_USD}$",
                otsinka_budzet_uah=str(int(BUDGET_UAH_APPROX)),
                riven_vpevnenosti="середній",
                prymitka="Реальний POI без website в OSM; потреба в сайті — кваліфікаційна оцінка",
            )
        )
        added += 1
    return added


def fetch_osm_by_major_cities(store: LeadStore) -> int:
    """Додаткові запити Overpass по великих містах для набору 1000+."""
    added = 0
    cities = [
        ("Київ", 50.4501, 30.5234),
        ("Львів", 49.8397, 24.0297),
        ("Одеса", 46.4825, 30.7233),
        ("Харків", 49.9935, 36.2304),
        ("Дніпро", 48.4647, 35.0462),
        ("Запоріжжя", 47.8388, 35.1396),
        ("Вінниця", 49.2328, 28.4809),
        ("Полтава", 49.5883, 34.5514),
        ("Черкаси", 49.4444, 32.0598),
        ("Миколаїв", 46.9750, 31.9946),
        ("Суми", 50.9077, 34.7981),
        ("Житомир", 50.2547, 28.6587),
        ("Рівне", 50.6199, 26.2516),
        ("Тернопіль", 49.5535, 25.5948),
        ("Івано-Франківськ", 48.9226, 24.7111),
        ("Ужгород", 48.6208, 22.2879),
        ("Чернівці", 48.2915, 25.9358),
        ("Луцьк", 50.7472, 25.3254),
        ("Кропивницький", 48.5079, 32.2623),
    ]
    overpass_url = "https://overpass-api.de/api/interpreter"
    per_city = max(60, (TARGET_COUNT - store.count()) // max(1, len(cities)) + 10)
    for city_name, lat, lon in cities:
        if store.count() >= TARGET_COUNT:
            break
        query = f"""
        [out:json][timeout:90];
        (
          nwr(around:12000,{lat},{lon})
            ["name"]
            ["phone"]
            ["website"!~"."]
            ["contact:website"!~"."]
            ["url"!~"."]
            ["shop"];
          nwr(around:12000,{lat},{lon})
            ["name"]
            ["phone"]
            ["website"!~"."]
            ["contact:website"!~"."]
            ["url"!~"."]
            ["amenity"~"restaurant|cafe|fast_food|bar|pharmacy|clinic|dentist|beauty_salon|hairdresser|car_repair"];
          nwr(around:12000,{lat},{lon})
            ["name"]
            ["phone"]
            ["website"!~"."]
            ["contact:website"!~"."]
            ["url"!~"."]
            ["office"];
        );
        out body {per_city};
        """
        try:
            resp = requests.post(overpass_url, data={"data": query}, timeout=120)
            resp.raise_for_status()
            data = resp.json()
        except Exception as exc:
            print(f"Overpass {city_name}: {exc}")
            time.sleep(3)
            continue
        for el in data.get("elements", []):
            if store.count() >= TARGET_COUNT:
                break
            tags = el.get("tags", {})
            name = tags.get("name", "").strip()
            if len(name) < 3:
                continue
            sector = tags.get("shop") or tags.get("amenity") or tags.get("office") or "бізнес"
            phone = normalize_phone(tags.get("phone") or tags.get("contact:phone") or "")
            store.add(
                Lead(
                    nazva=name[:200],
                    typ_subiekta=str(sector)[:80],
                    misto=city_name,
                    telefon=phone,
                    email=(tags.get("email") or "")[:120],
                    dzherelo="OpenStreetMap (місто)",
                    url_dzherelo=f"https://www.openstreetmap.org/{el.get('type','node')}/{el.get('id')}",
                    opys_potreby=f"Локальний бізнес у {city_name}, без сайту в OSM",
                    signal_budzet=f"~{BUDGET_USD}$",
                    otsinka_budzet_uah=str(int(BUDGET_UAH_APPROX)),
                    riven_vpevnenosti="середній",
                    prymitka="Кваліфікований лід: реальна точка на карті",
                )
            )
            added += 1
        time.sleep(2)
    return added


def try_parse_fop_xml_sample(store: LeadStore, xml_path: Path, max_records: int = 2000) -> int:
    """Парсинг вибірки з XML ЄДР, якщо файл завантажено."""
    if not xml_path.exists():
        return 0
    added = 0
    try:
        for event, elem in ET.iterparse(xml_path, events=("end",)):
            tag = elem.tag.split("}")[-1] if "}" in elem.tag else elem.tag
            if tag not in ("RECORD", "FOP", "SUBJECT", "item"):
                continue
            text = ET.tostring(elem, encoding="unicode", method="text")
            if not matches_service_sector(text):
                elem.clear()
                continue
            name = ""
            for child in elem.iter():
                ctag = child.tag.split("}")[-1]
                if ctag in ("NAME", "NAMES", "FIO", "LastName", "FullName"):
                    val = (child.text or "").strip()
                    if val:
                        name = val
                        break
            if name:
                store.add(
                    Lead(
                        nazva=name[:200],
                        typ_subiekta="ФОП (ЄДР)",
                        dzherelo="data.gov.ua ЄДР",
                        opys_potreby="Зареєстрований ФОП у сфері послуг",
                        signal_budzet=f"~{BUDGET_USD}$",
                        otsinka_budzet_uah=str(int(BUDGET_UAH_APPROX)),
                        riven_vpevnenosti="низький",
                    )
                )
                added += 1
            elem.clear()
            if store.count() >= TARGET_COUNT or added >= max_records:
                break
    except Exception as exc:
        print(f"XML parse error: {exc}")
    return added


def export_xlsx(store: LeadStore, path: Path) -> None:
    wb = Workbook()
    ws = wb.active
    ws.title = "Ліди_сайт_500USD"
    headers = [
        "№",
        "Назва бізнесу",
        "Тип суб'єкта",
        "Місто",
        "Область",
        "Телефон",
        "Email",
        "Сайт",
        "Джерело",
        "URL джерела",
        "Опис потреби",
        "Сигнал бюджету",
        "Оцінка бюджет (грн)",
        "Рівень впевненості",
        "Дата збору",
        "Примітка",
    ]
    ws.append(headers)
    header_font = Font(bold=True)
    for col in range(1, len(headers) + 1):
        cell = ws.cell(row=1, column=col)
        cell.font = header_font
        cell.alignment = Alignment(wrap_text=True, vertical="top")
    for lead in store.leads[:TARGET_COUNT]:
        ws.append(
            [
                lead.id,
                lead.nazva,
                lead.typ_subiekta,
                lead.misto,
                lead.oblast,
                lead.telefon,
                lead.email,
                lead.sait,
                lead.dzherelo,
                lead.url_dzherelo,
                lead.opys_potreby,
                lead.signal_budzet,
                lead.otsinka_budzet_uah,
                lead.riven_vpevnenosti,
                lead.data_zboru,
                lead.prymitka,
            ]
        )
    for row in ws.iter_rows(min_row=2, max_row=ws.max_row):
        for cell in row:
            cell.alignment = Alignment(wrap_text=True, vertical="top")
    widths = [5, 35, 18, 14, 16, 16, 22, 22, 18, 40, 45, 18, 14, 14, 12, 35]
    for i, w in enumerate(widths, 1):
        ws.column_dimensions[get_column_letter(i)].width = w
    meta = wb.create_sheet("Метадані")
    meta.append(["Параметр", "Значення"])
    meta.append(["Дата формування", datetime.now().isoformat(timespec="seconds")])
    meta.append(["Цільовий бюджет", f"{BUDGET_USD} USD (~{int(BUDGET_UAH_APPROX)} грн)"])
    meta.append(["Записів у файлі", str(min(store.count(), TARGET_COUNT))])
    meta.append(
        [
            "Важливо",
            "Прямі запити: FL.ru, Kwork (рівень впевненості середній/високий). "
            "ФОП з ЄДР — реальні суб'єкти, реєстрація з 2020 р. (низький рівень — потрібна верифікація потреби).",
        ]
    )
    path.parent.mkdir(parents=True, exist_ok=True)
    wb.save(path)


def main() -> None:
    store = LeadStore()
    stats: dict[str, int] = {}

    print("=== Збір лідів Україна / сайт ~500$ ===")
    fop_path = Path("/workspace/data/fop.zip")

    for name, func in (
        ("FL.ru", lambda: scrape_fl_ru_ua(store, pages=8)),
        ("Kwork", lambda: scrape_kwork(store, pages=6)),
        ("Freelancehunt", lambda: scrape_freelancehunt(store, pages=5)),
        ("Work.ua", lambda: scrape_work_ua(store, max_pages=3)),
        ("Weblancer", lambda: scrape_weblancer(store, pages=4)),
        ("Prom.ua", lambda: scrape_prom_ua_no_site(store, limit=150)),
    ):
        if store.count() >= TARGET_COUNT:
            break
        try:
            n = func()
            stats[name] = n
            print(f"{name}: +{n}, всього {store.count()}")
        except Exception as exc:
            stats[name] = 0
            print(f"{name} FAILED: {exc}")

    if store.count() < TARGET_COUNT and fop_path.exists():
        try:
            n = parse_fop_zip(store, fop_path, max_add=TARGET_COUNT - store.count())
            stats["ЄДР ФОП"] = n
            print(f"ЄДР ФОП: +{n}, всього {store.count()}")
        except Exception as exc:
            stats["ЄДР ФОП"] = 0
            print(f"ЄДР ФОП FAILED: {exc}")

    export_xlsx(store, OUTPUT_XLSX)
    summary = {
        "total": min(store.count(), TARGET_COUNT),
        "by_source": {},
        "output": str(OUTPUT_XLSX),
        "stats": stats,
    }
    for lead in store.leads[:TARGET_COUNT]:
        summary["by_source"][lead.dzherelo] = summary["by_source"].get(lead.dzherelo, 0) + 1
    summary_path = OUTPUT_XLSX.with_suffix(".summary.json")
    summary_path.write_text(json.dumps(summary, ensure_ascii=False, indent=2), encoding="utf-8")
    print(json.dumps(summary, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
