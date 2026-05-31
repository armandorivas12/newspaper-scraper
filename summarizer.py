import logging

import anthropic

from config import Article

logger = logging.getLogger(__name__)

OPINION_SYSTEM = (
    "Eres un asistente de resumen de noticias. Resume este artículo de opinión/análisis "
    "de República Dominicana en 3-4 oraciones en español. Captura el argumento principal "
    "del autor, la evidencia o razonamiento clave, y su conclusión. Sé conciso pero "
    "preserva la sustancia de su posición."
)

NEWS_SYSTEM = (
    "Eres un asistente de resumen de noticias. Resume este artículo de noticias de "
    "República Dominicana en 1 oración en español. Captura solo el hecho más esencial "
    "— quién hizo qué, o qué pasó. Sé extremadamente breve."
)


def summarize_articles(articles: list[Article], api_key: str) -> list[Article]:
    client = anthropic.Anthropic(api_key=api_key)

    for article in articles:
        if not article.body:
            article.summary = article.title
            continue

        is_opinion = article.section_type == "opinion"
        system_prompt = OPINION_SYSTEM if is_opinion else NEWS_SYSTEM
        max_tokens = 250 if is_opinion else 100

        user_content = f"Título: {article.title}\n"
        if article.author:
            user_content += f"Autor: {article.author}\n"
        user_content += f"\n{article.body}"

        try:
            response = client.messages.create(
                model="claude-haiku-4-5-20251001",
                max_tokens=max_tokens,
                system=system_prompt,
                messages=[{"role": "user", "content": user_content}],
            )
            article.summary = response.content[0].text.strip()
        except Exception as e:
            logger.warning("Failed to summarize '%s': %s", article.title, e)
            article.summary = article.title

    return articles
