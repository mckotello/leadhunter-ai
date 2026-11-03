import asyncio
import logging
import re
import time
from dataclasses import dataclass, field
from urllib.parse import urljoin, urlparse

import httpx
from bs4 import BeautifulSoup

from app.config import settings
from app.utils.ssrf import SSRFError, safe_fetch_html, validate_public_url

logger = logging.getLogger(__name__)

EMAIL_RE = re.compile(r"[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}")
PHONE_RE = re.compile(r"(\+7|8)[\s\-]?\(?\d{3}\)?[\s\-]?\d{3}[\s\-]?\d{2}[\s\-]?\d{2}")


@dataclass
class SiteSignals:
    has_mobile_viewport: bool = False
    has_contact_form: bool = False
    has_online_catalog: bool = False
    has_personal_account: bool = False
    has_online_payment: bool = False
    crm_hints: list[str] = field(default_factory=list)
    technical_issues: list[str] = field(default_factory=list)
    design_notes: str = ""


@dataclass
class ParsedCompany:
    name: str | None = None
    description: str | None = None
    region: str | None = None
    phone: str | None = None
    email: str | None = None
    social_links: dict = field(default_factory=dict)
    contact_pages: list[str] = field(default_factory=list)
    service_pages: list[str] = field(default_factory=list)
    products_services: list[str] = field(default_factory=list)
    signals: SiteSignals = field(default_factory=SiteSignals)
    raw_text_sample: str = ""
    source_url: str = ""


class ParserAgent:
    def __init__(self) -> None:
        self._last_fetch: dict[str, float] = {}

    async def _rate_limit(self, domain: str) -> None:
        delay = 1.0 / max(settings.http_rate_limit_per_domain, 0.1)
        last = self._last_fetch.get(domain, 0.0)
        wait = delay - (time.monotonic() - last)
        if wait > 0:
            await asyncio.sleep(wait)
        self._last_fetch[domain] = time.monotonic()

    async def parse(self, url: str, company_name: str | None = None) -> ParsedCompany:
        try:
            safe_url = validate_public_url(url)
        except SSRFError as exc:
            logger.warning("SSRF blocked for %s: %s", url, exc)
            return ParsedCompany(name=company_name, source_url=url)

        domain = urlparse(safe_url).hostname or ""
        await self._rate_limit(domain)

        headers = {"User-Agent": "LeadHunterBot/1.0 (+https://example.com/bot)"}
        html, final_url = await self._fetch_with_retries(safe_url, headers)

        if not html:
            return ParsedCompany(name=company_name, source_url=final_url or safe_url)

        soup = BeautifulSoup(html, "lxml")
        parsed = ParsedCompany(
            name=company_name or self._extract_title(soup),
            description=self._meta_description(soup),
            source_url=final_url,
        )
        text = soup.get_text(" ", strip=True)
        parsed.raw_text_sample = text[:4000]

        emails = EMAIL_RE.findall(text)
        if emails:
            parsed.email = emails[0]
        phones = PHONE_RE.findall(text)
        if phones:
            parsed.phone = phones[0]

        parsed.social_links = self._extract_social(soup)
        parsed.contact_pages = self._find_links(soup, final_url, ("contact", "kontakt", "контакт"))
        parsed.service_pages = self._find_links(soup, final_url, ("service", "uslugi", "услуг", "catalog", "каталог"))
        parsed.products_services = self._extract_list_items(soup)[:15]
        parsed.signals = self._analyze_signals(soup, text)
        return parsed

    async def _fetch_with_retries(
        self, url: str, headers: dict[str, str]
    ) -> tuple[str | None, str]:
        last_url = url
        async with httpx.AsyncClient(timeout=settings.http_timeout, follow_redirects=False) as client:
            for attempt in range(settings.http_max_retries):
                try:
                    html, last_url = await safe_fetch_html(client, url, headers)
                    return html, last_url
                except SSRFError as exc:
                    logger.warning("SSRF blocked during fetch %s: %s", url, exc)
                    return None, last_url
                except httpx.HTTPError as exc:
                    logger.warning("Fetch attempt %s failed for %s: %s", attempt + 1, url, exc)
                    await asyncio.sleep(0.5 * (attempt + 1))
        return None, last_url

    def _extract_title(self, soup: BeautifulSoup) -> str | None:
        if soup.title and soup.title.string:
            return soup.title.string.strip()[:512]
        h1 = soup.find("h1")
        return h1.get_text(strip=True)[:512] if h1 else None

    def _meta_description(self, soup: BeautifulSoup) -> str | None:
        tag = soup.find("meta", attrs={"name": "description"})
        if tag and tag.get("content"):
            return str(tag["content"]).strip()[:2000]
        og = soup.find("meta", property="og:description")
        if og and og.get("content"):
            return str(og["content"]).strip()[:2000]
        return None

    def _extract_social(self, soup: BeautifulSoup) -> dict:
        links: dict[str, str] = {}
        for a in soup.find_all("a", href=True):
            href = a["href"]
            for key, marker in (
                ("vk", "vk.com"),
                ("telegram", "t.me"),
                ("instagram", "instagram.com"),
                ("youtube", "youtube.com"),
                ("facebook", "facebook.com"),
            ):
                if marker in href and key not in links:
                    links[key] = href
        return links

    def _find_links(self, soup: BeautifulSoup, base: str, keywords: tuple[str, ...]) -> list[str]:
        found: list[str] = []
        for a in soup.find_all("a", href=True):
            href = a["href"]
            label = (a.get_text(" ", strip=True) + " " + href).lower()
            if any(k in label for k in keywords):
                full = urljoin(base, href)
                if full not in found:
                    found.append(full)
        return found[:10]

    def _extract_list_items(self, soup: BeautifulSoup) -> list[str]:
        items: list[str] = []
        for li in soup.find_all("li"):
            text = li.get_text(" ", strip=True)
            if 5 < len(text) < 120:
                items.append(text)
        return items

    def _analyze_signals(self, soup: BeautifulSoup, text: str) -> SiteSignals:
        lower = text.lower()
        signals = SiteSignals()
        viewport = soup.find("meta", attrs={"name": "viewport"})
        signals.has_mobile_viewport = viewport is not None
        signals.has_contact_form = soup.find("form") is not None
        signals.has_online_catalog = any(
            w in lower for w in ("каталог", "catalog", "shop", "магазин", "товар")
        )
        signals.has_personal_account = any(
            w in lower for w in ("личный кабинет", "personal account", "sign in", "войти в кабинет")
        )
        signals.has_online_payment = any(
            w in lower for w in ("оплат", "payment", "checkout", "корзин", "cart")
        )
        for crm in ("bitrix24", "amocrm", "salesforce", "hubspot"):
            if crm in lower:
                signals.crm_hints.append(crm)
        if not signals.has_mobile_viewport:
            signals.technical_issues.append("Не обнаружен meta viewport (возможна слабая мобильная адаптация)")
        if len(text) < 300:
            signals.technical_issues.append("Мало текстового контента на главной странице")
        signals.design_notes = "Эвристическая оценка по структуре HTML и ключевым словам"
        return signals
