import argparse
import logging
import sys

from config import load_config, Article, Config, NewspaperConfig, SectionConfig, CONFIG_PATH
from scrapers import scrape_newspaper

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    datefmt="%H:%M:%S",
)
logger = logging.getLogger(__name__)


def classify_and_flag(articles: list[Article], priority_authors: list[str]) -> tuple[list[Article], list[Article]]:
    opinion = []
    news = []

    for article in articles:
        if article.author and article.author.lower() in priority_authors:
            article.is_priority_author = True

        if article.section_type == "opinion":
            opinion.append(article)
        else:
            news.append(article)

    return opinion, news


def apply_limits(articles: list[Article], max_count: int) -> list[Article]:
    priority = [a for a in articles if a.is_priority_author]
    regular = [a for a in articles if not a.is_priority_author]
    remaining_slots = max(0, max_count - len(priority))
    return priority + regular[:remaining_slots]


def main():
    parser = argparse.ArgumentParser(description="Dominican News Digest")
    parser.add_argument("--dry-run", action="store_true", help="Print HTML to stdout instead of sending email")
    parser.add_argument("--scrape-only", action="store_true", help="Scrape only, print titles (no AI, no email)")
    args = parser.parse_args()

    if args.scrape_only:
        import yaml
        with open(CONFIG_PATH, encoding="utf-8") as f:
            raw = yaml.safe_load(f)
        newspapers = []
        for np in raw["newspapers"]:
            sections = [SectionConfig(path=s["path"], type=s["type"], max_articles=s.get("max_articles", 10)) for s in np["sections"]]
            newspapers.append(NewspaperConfig(name=np["name"], base_url=np["base_url"].rstrip("/"), sections=sections))
    else:
        cfg = load_config()
        newspapers = cfg.newspapers

    # 1. Scrape
    all_articles: list[Article] = []
    errors: list[str] = []

    for newspaper in newspapers:
        logger.info("=== Scraping %s ===", newspaper.name)
        try:
            articles = scrape_newspaper(newspaper)
            all_articles.extend(articles)
            logger.info("  Total: %d articles from %s", len(articles), newspaper.name)
        except Exception as e:
            msg = f"{newspaper.name} no disponible: {e}"
            logger.error(msg)
            errors.append(msg)

    logger.info("Scraping complete: %d total articles", len(all_articles))

    if args.scrape_only:
        for a in all_articles:
            tag = "OPINION" if a.section_type == "opinion" else "NEWS"
            author = f" [{a.author}]" if a.author else ""
            print(f"  [{tag}] {a.newspaper}: {a.title}{author}")
        print(f"\nTotal: {len(all_articles)} articles")
        return

    # 2. Classify and flag priority authors
    opinion, news = classify_and_flag(all_articles, cfg.priority_authors)
    priority_found = [a.author for a in opinion + news if a.is_priority_author]
    if priority_found:
        logger.info("Priority authors found: %s", ", ".join(set(priority_found)))

    # 3. Apply limits (opinion has a global cap; news relies on per-section limits in config)
    opinion = apply_limits(opinion, cfg.max_opinion_articles)
    logger.info("After limits: %d opinion, %d news", len(opinion), len(news))

    # 4. Summarize
    from summarizer import summarize_all
    opinion, newspaper_overviews, news = summarize_all(opinion, news, cfg.anthropic_api_key)

    # 5. Build email
    from email_builder import build_email, _format_date_spanish
    html = build_email(opinion, news, newspaper_overviews, errors if errors else None)

    if args.dry_run:
        print(html)
        logger.info("Dry run complete — HTML printed to stdout")
        return

    # 6. Send
    from sender import send_email
    date_str = _format_date_spanish()
    subject = f"{cfg.subject_prefix} — {date_str}"
    success = send_email(cfg.email_to, subject, html, cfg.resend_api_key)

    if success:
        logger.info("Done! Digest sent to %s (%d opinion, %d news)", cfg.email_to, len(opinion), len(news))
    else:
        logger.error("Failed to send digest email")
        sys.exit(1)


if __name__ == "__main__":
    main()
