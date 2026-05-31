import logging
import re
import time

import anthropic

from config import Article

logger = logging.getLogger(__name__)

OPINION_SYSTEM = (
    "Eres un asistente de resumen de noticias. Resume este artículo de opinión/análisis "
    "de República Dominicana en 3-4 oraciones en español. Captura el argumento principal "
    "del autor, la evidencia o razonamiento clave, y su conclusión. Sé conciso pero "
    "preserva la sustancia de su posición."
)

NEWS_BATCH_SYSTEM = (
    "Eres un asistente de resumen de noticias de República Dominicana. "
    "Te daré una lista de titulares de noticias. Responde en este formato exacto:\n\n"
    "RESUMEN: [2-3 oraciones describiendo los temas y eventos principales del día en este periódico]\n"
    "ARTICULOS:\n"
    "1. [una oración resumiendo el artículo 1]\n"
    "2. [una oración resumiendo el artículo 2]\n"
    "...y así para cada artículo. Sé muy breve en cada línea."
)


def summarize_opinion(articles: list[Article], api_key: str) -> list[Article]:
    """One Claude call per opinion article."""
    client = anthropic.Anthropic(api_key=api_key)

    for article in articles:
        if not article.body:
            article.summary = article.title
            continue

        user_content = f"Título: {article.title}\n"
        if article.author:
            user_content += f"Autor: {article.author}\n"
        user_content += f"\n{article.body}"

        try:
            response = client.messages.create(
                model="claude-haiku-4-5-20251001",
                max_tokens=250,
                system=OPINION_SYSTEM,
                messages=[{"role": "user", "content": user_content}],
            )
            article.summary = response.content[0].text.strip()
        except Exception as e:
            logger.warning("Failed to summarize opinion '%s': %s", article.title, e)
            article.summary = article.title

        time.sleep(0.3)

    return articles


def summarize_news_batch(newspaper_name: str, articles: list[Article], api_key: str) -> tuple[str, list[Article]]:
    """One Claude call for all news articles from one newspaper.
    Returns (newspaper_overview, articles_with_summaries).
    """
    client = anthropic.Anthropic(api_key=api_key)

    if not articles:
        return "", articles

    # Build numbered list of article titles + first sentence of body
    article_lines = []
    for i, a in enumerate(articles, 1):
        snippet = a.body[:200].split("\n")[0] if a.body else ""
        article_lines.append(f"{i}. {a.title}" + (f" — {snippet}" if snippet else ""))

    user_content = f"Periódico: {newspaper_name}\nArtículos:\n" + "\n".join(article_lines)

    overview = ""
    try:
        response = client.messages.create(
            model="claude-haiku-4-5-20251001",
            max_tokens=600,
            system=NEWS_BATCH_SYSTEM,
            messages=[{"role": "user", "content": user_content}],
        )
        raw = response.content[0].text.strip()

        # Parse RESUMEN
        m = re.search(r"RESUMEN:\s*(.+?)(?=\nARTICULOS:|\Z)", raw, re.DOTALL)
        if m:
            overview = m.group(1).strip()

        # Parse numbered summaries
        summaries = re.findall(r"^\d+\.\s*(.+)$", raw, re.MULTILINE)
        for i, article in enumerate(articles):
            if i < len(summaries):
                article.summary = summaries[i].strip()
            else:
                article.summary = article.title

    except Exception as e:
        logger.warning("Failed to batch-summarize news for %s: %s", newspaper_name, e)
        for article in articles:
            article.summary = article.title

    return overview, articles


def summarize_all(
    opinion: list[Article],
    news: list[Article],
    api_key: str,
) -> tuple[list[Article], dict[str, str], list[Article]]:
    """Summarize everything. Returns (opinion, newspaper_overviews, news)."""

    logger.info("Summarizing %d opinion articles (1 call each)...", len(opinion))
    opinion = summarize_opinion(opinion, api_key)

    # Group news by newspaper and batch
    news_by_paper: dict[str, list[Article]] = {}
    for a in news:
        news_by_paper.setdefault(a.newspaper, []).append(a)

    newspaper_overviews: dict[str, str] = {}
    summarized_news: list[Article] = []

    logger.info("Summarizing news in %d newspaper batches...", len(news_by_paper))
    for paper_name, paper_articles in news_by_paper.items():
        logger.info("  Batch: %s (%d articles)", paper_name, len(paper_articles))
        overview, paper_articles = summarize_news_batch(paper_name, paper_articles, api_key)
        newspaper_overviews[paper_name] = overview
        summarized_news.extend(paper_articles)

    total_calls = len(opinion) + len(news_by_paper)
    logger.info("Summarization complete: %d Claude calls total", total_calls)

    return opinion, newspaper_overviews, summarized_news
