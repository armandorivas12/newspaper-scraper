import os
from dataclasses import dataclass, field
from pathlib import Path

import yaml
from dotenv import load_dotenv

load_dotenv()

CONFIG_PATH = Path(__file__).parent / "config.yaml"


@dataclass
class SectionConfig:
    path: str
    type: str
    max_articles: int


@dataclass
class NewspaperConfig:
    name: str
    base_url: str
    sections: list[SectionConfig]


@dataclass
class Config:
    email_to: str
    subject_prefix: str
    max_opinion_articles: int
    max_news_articles: int
    priority_authors: list[str]
    newspapers: list[NewspaperConfig]
    anthropic_api_key: str
    resend_api_key: str


@dataclass
class Article:
    title: str
    url: str
    newspaper: str
    section_type: str
    author: str | None = None
    body: str = ""
    summary: str = ""
    is_priority_author: bool = False
    date: str | None = None


def load_config() -> Config:
    with open(CONFIG_PATH, encoding="utf-8") as f:
        raw = yaml.safe_load(f)

    newspapers = []
    for np in raw["newspapers"]:
        sections = [
            SectionConfig(
                path=s["path"],
                type=s["type"],
                max_articles=s.get("max_articles", 10),
            )
            for s in np["sections"]
        ]
        newspapers.append(
            NewspaperConfig(
                name=np["name"],
                base_url=np["base_url"].rstrip("/"),
                sections=sections,
            )
        )

    priority_authors = [name.lower() for name in raw.get("priority_authors", [])]

    anthropic_key = os.environ.get("ANTHROPIC_API_KEY", "")
    resend_key = os.environ.get("RESEND_API_KEY", "")

    if not anthropic_key:
        raise ValueError("ANTHROPIC_API_KEY environment variable is required")
    if not resend_key:
        raise ValueError("RESEND_API_KEY environment variable is required")

    return Config(
        email_to=raw["email"]["to"],
        subject_prefix=raw["email"].get("subject_prefix", "Resumen Diario"),
        max_opinion_articles=raw["limits"].get("max_opinion_articles", 15),
        max_news_articles=raw["limits"].get("max_news_articles", 25),
        priority_authors=priority_authors,
        newspapers=newspapers,
        anthropic_api_key=anthropic_key,
        resend_api_key=resend_key,
    )
