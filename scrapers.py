import logging
import re
import time
from urllib.parse import urljoin

import requests
from bs4 import BeautifulSoup

from config import Article, NewspaperConfig, SectionConfig

logger = logging.getLogger(__name__)

HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
    "(KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
}
REQUEST_DELAY = 1.0


def _fetch(url: str) -> BeautifulSoup | None:
    try:
        resp = requests.get(url, headers=HEADERS, timeout=15)
        resp.raise_for_status()
        return BeautifulSoup(resp.content, "html.parser")
    except Exception as e:
        logger.warning("Failed to fetch %s: %s", url, e)
        return None


def _extract_text(soup: BeautifulSoup, max_chars: int = 2000) -> str:
    article_body = soup.find("article") or soup.find("div", class_=re.compile(r"article|content|body", re.I))
    container = article_body if article_body else soup

    paragraphs = container.find_all("p")
    text = "\n".join(p.get_text(strip=True) for p in paragraphs if p.get_text(strip=True))
    return text[:max_chars]


MONTHS_ES = {
    1: "ene", 2: "feb", 3: "mar", 4: "abr", 5: "may", 6: "jun",
    7: "jul", 8: "ago", 9: "sep", 10: "oct", 11: "nov", 12: "dic",
}


def _parse_date_from_url(url: str) -> str | None:
    # Listín format: /20260531/ (8 digits)
    m = re.search(r"/(\d{4})(\d{2})(\d{2})/", url)
    if m:
        y, mo, d = int(m.group(1)), int(m.group(2)), int(m.group(3))
        return f"{d} {MONTHS_ES.get(mo, mo)} {y}"
    # Diario Libre format: /2026/05/31/
    m = re.search(r"/(\d{4})/(\d{2})/(\d{2})/", url)
    if m:
        y, mo, d = int(m.group(1)), int(m.group(2)), int(m.group(3))
        return f"{d} {MONTHS_ES.get(mo, mo)} {y}"
    return None


def _is_article_url(href: str, section_path: str) -> bool:
    """Check if a URL looks like an article (has a date pattern in it)."""
    section_clean = section_path.rstrip("/")
    if section_clean not in href:
        return False
    if re.search(r"/\d{8}/", href) or re.search(r"/\d{4}/\d{2}/\d{2}/", href):
        return True
    if href.endswith(".html") and re.search(r"_\d+\.html$", href):
        return True
    return False


# ─── Listín Diario ──────────────────────────────────────────

def _scrape_listin_section(base_url: str, section: SectionConfig, newspaper_name: str) -> list[Article]:
    listing_url = base_url + section.path
    soup = _fetch(listing_url)
    if not soup:
        return []

    articles = []
    links_seen = set()

    for a_tag in soup.find_all("a", href=True):
        href = a_tag["href"]
        if not href.endswith(".html"):
            continue
        if section.path not in href:
            continue
        if not re.search(r"/\d{8}/", href):
            continue
        full_url = urljoin(base_url, href)
        if full_url in links_seen:
            continue
        links_seen.add(full_url)

        title = a_tag.get_text(strip=True)
        if not title or len(title) < 10:
            continue

        articles.append(Article(
            title=title,
            url=full_url,
            newspaper=newspaper_name,
            section_type=section.type,
            date=_parse_date_from_url(full_url),
        ))

        if len(articles) >= section.max_articles:
            break

    for article in articles:
        time.sleep(REQUEST_DELAY)
        soup = _fetch(article.url)
        if not soup:
            continue

        h1 = soup.find("h1")
        if h1:
            article.title = h1.get_text(strip=True)

        author_link = soup.find("a", href=re.compile(r"/autor/"))
        if author_link:
            article.author = author_link.get_text(strip=True)

        article.body = _extract_text(soup)

    return articles


def scrape_listin(newspaper: NewspaperConfig, **kwargs) -> list[Article]:
    all_articles = []
    for section in newspaper.sections:
        logger.info("Scraping %s %s", newspaper.name, section.path)
        articles = _scrape_listin_section(newspaper.base_url, section, newspaper.name)
        all_articles.extend(articles)
        logger.info("  Found %d articles", len(articles))
    return all_articles


# ─── Diario Libre ───────────────────────────────────────────

def _scrape_diariolibre_section(base_url: str, section: SectionConfig, newspaper_name: str) -> list[Article]:
    listing_url = base_url + section.path
    soup = _fetch(listing_url)
    if not soup:
        return []

    articles = []
    links_seen = set()

    for a_tag in soup.find_all("a", href=True):
        href = a_tag["href"]
        if section.path.rstrip("/") not in href:
            continue
        if not re.search(r"/\d{4}/\d{2}/\d{2}/", href):
            continue
        full_url = urljoin(base_url, href)
        if full_url in links_seen:
            continue
        links_seen.add(full_url)

        title = a_tag.get_text(strip=True)
        if not title or len(title) < 10:
            continue

        articles.append(Article(
            title=title,
            url=full_url,
            newspaper=newspaper_name,
            section_type=section.type,
            date=_parse_date_from_url(full_url),
        ))

        if len(articles) >= section.max_articles:
            break

    for article in articles:
        time.sleep(REQUEST_DELAY)
        soup = _fetch(article.url)
        if not soup:
            continue

        h1 = soup.find("h1")
        if h1:
            article.title = h1.get_text(strip=True)

        author_link = soup.find("a", href=re.compile(r"/autor/"))
        if author_link:
            article.author = author_link.get_text(strip=True)

        article.body = _extract_text(soup)

    return articles


def scrape_diario_libre(newspaper: NewspaperConfig, **kwargs) -> list[Article]:
    all_articles = []
    for section in newspaper.sections:
        logger.info("Scraping %s %s", newspaper.name, section.path)
        articles = _scrape_diariolibre_section(newspaper.base_url, section, newspaper.name)
        all_articles.extend(articles)
        logger.info("  Found %d articles", len(articles))
    return all_articles


# ─── Hoy ────────────────────────────────────────────────────

def _scrape_hoy_section(base_url: str, section: SectionConfig, newspaper_name: str) -> list[Article]:
    listing_url = base_url + section.path
    soup = _fetch(listing_url)
    if not soup:
        return []

    articles = []
    links_seen = set()

    for a_tag in soup.find_all("a", href=True):
        href = a_tag["href"]
        if not href.endswith(".html"):
            continue
        section_path = section.path.rstrip("/")
        if section_path not in href:
            continue
        if not re.search(r"_\d+\.html$", href):
            continue
        full_url = urljoin(base_url, href)
        if full_url in links_seen:
            continue
        links_seen.add(full_url)

        title = a_tag.get_text(strip=True)
        if not title or len(title) < 10:
            continue

        articles.append(Article(
            title=title,
            url=full_url,
            newspaper=newspaper_name,
            section_type=section.type,
            date=_parse_date_from_url(full_url),
        ))

        if len(articles) >= section.max_articles:
            break

    for article in articles:
        time.sleep(REQUEST_DELAY)
        soup = _fetch(article.url)
        if not soup:
            continue

        h1 = soup.find("h1")
        if h1:
            article.title = h1.get_text(strip=True)

        author_link = soup.find("a", href=re.compile(r"/autor(es)?/"))
        if author_link:
            author_name = author_link.get_text(strip=True)
            if author_name:
                article.author = author_name

        article.body = _extract_text(soup)

    return articles


def scrape_hoy(newspaper: NewspaperConfig, **kwargs) -> list[Article]:
    all_articles = []
    for section in newspaper.sections:
        logger.info("Scraping %s %s", newspaper.name, section.path)
        articles = _scrape_hoy_section(newspaper.base_url, section, newspaper.name)
        all_articles.extend(articles)
        logger.info("  Found %d articles", len(articles))
    return all_articles


# ─── Dispatcher ─────────────────────────────────────────────

SCRAPERS = {
    "listín diario": scrape_listin,
    "listin diario": scrape_listin,
    "diario libre": scrape_diario_libre,
    "hoy": scrape_hoy,
}


def scrape_newspaper(newspaper: NewspaperConfig) -> list[Article]:
    key = newspaper.name.lower()
    scraper_fn = SCRAPERS.get(key)
    if not scraper_fn:
        logger.error("No scraper registered for '%s'", newspaper.name)
        return []
    try:
        return scraper_fn(newspaper)
    except Exception as e:
        logger.error("Scraper failed for %s: %s", newspaper.name, e)
        return []
