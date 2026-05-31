from datetime import date

from config import Article


def _format_date_spanish() -> str:
    months = [
        "enero", "febrero", "marzo", "abril", "mayo", "junio",
        "julio", "agosto", "septiembre", "octubre", "noviembre", "diciembre",
    ]
    t = date.today()
    return f"{t.day} de {months[t.month - 1]} de {t.year}"


def _opinion_card(article: Article) -> str:
    border = "border-left: 4px solid #D4A017;" if article.is_priority_author else "border-left: 4px solid #ddd;"
    star = "&#9733; " if article.is_priority_author else ""
    author_html = f'<div style="font-weight:bold;font-size:15px;color:#333;margin-bottom:4px;">{star}{article.author or "Sin autor"}</div>' if article.author or article.is_priority_author else ""

    return f"""
    <div style="padding:14px 16px;margin-bottom:12px;{border}background:#fafafa;border-radius:4px;">
      {author_html}
      <div style="font-size:16px;margin-bottom:8px;">
        <a href="{article.url}" style="color:#1a0dab;text-decoration:none;font-weight:600;">{article.title}</a>
      </div>
      <div style="font-size:14px;color:#444;line-height:1.5;margin-bottom:8px;">{article.summary}</div>
      <div style="font-size:12px;color:#888;">{article.newspaper} &middot; <a href="{article.url}" style="color:#888;">Leer art&iacute;culo &rarr;</a></div>
    </div>"""


def _news_item(article: Article) -> str:
    return f"""
      <tr>
        <td style="padding:6px 0;font-size:14px;border-bottom:1px solid #f0f0f0;">
          <a href="{article.url}" style="color:#1a0dab;text-decoration:none;font-weight:500;">{article.title}</a>
          <span style="color:#555;"> &mdash; {article.summary}</span>
        </td>
      </tr>"""


def build_email(opinion_articles: list[Article], news_articles: list[Article], errors: list[str] | None = None) -> str:
    date_str = _format_date_spanish()

    opinion_html = "\n".join(_opinion_card(a) for a in opinion_articles)
    if not opinion_articles:
        opinion_html = '<div style="padding:12px;color:#888;font-style:italic;">No se encontraron art&iacute;culos de opini&oacute;n hoy.</div>'

    news_by_paper: dict[str, list[Article]] = {}
    for a in news_articles:
        news_by_paper.setdefault(a.newspaper, []).append(a)

    news_sections = []
    for paper_name, articles in news_by_paper.items():
        rows = "\n".join(_news_item(a) for a in articles)
        news_sections.append(f"""
    <div style="margin-bottom:16px;">
      <div style="font-weight:bold;font-size:14px;color:#333;padding:8px 0;border-bottom:2px solid #1a0dab;">{paper_name}</div>
      <table style="width:100%;border-collapse:collapse;">{rows}</table>
    </div>""")

    news_html = "\n".join(news_sections)
    if not news_articles:
        news_html = '<div style="padding:12px;color:#888;font-style:italic;">No se encontraron noticias hoy.</div>'

    errors_html = ""
    if errors:
        items = "".join(f"<li>{e}</li>" for e in errors)
        errors_html = f'<div style="background:#fff3cd;border:1px solid #ffc107;padding:10px;border-radius:4px;margin-bottom:16px;font-size:13px;color:#856404;"><strong>Avisos:</strong><ul style="margin:4px 0 0 0;padding-left:20px;">{items}</ul></div>'

    total = len(opinion_articles) + len(news_articles)

    return f"""<!DOCTYPE html>
<html>
<head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1.0"></head>
<body style="margin:0;padding:0;background:#f5f5f5;font-family:-apple-system,BlinkMacSystemFont,'Segoe UI',Roboto,sans-serif;">
<div style="max-width:600px;margin:0 auto;background:#fff;">

  <div style="background:#1a0dab;padding:24px 20px;text-align:center;">
    <div style="color:#fff;font-size:22px;font-weight:bold;">Resumen Diario</div>
    <div style="color:#ccc;font-size:14px;margin-top:4px;">{date_str}</div>
  </div>

  <div style="padding:20px;">
    {errors_html}

    <div style="font-size:18px;font-weight:bold;color:#333;margin-bottom:14px;padding-bottom:8px;border-bottom:2px solid #D4A017;">
      &#9998; Opini&oacute;n y An&aacute;lisis
    </div>
    {opinion_html}

    <div style="font-size:18px;font-weight:bold;color:#333;margin:24px 0 14px 0;padding-bottom:8px;border-bottom:2px solid #1a0dab;">
      &#128240; Noticias del D&iacute;a
    </div>
    {news_html}
  </div>

  <div style="background:#f5f5f5;padding:16px 20px;text-align:center;font-size:12px;color:#999;">
    Generado autom&aacute;ticamente &middot; {date_str} &middot; {total} art&iacute;culos
  </div>

</div>
</body>
</html>"""
