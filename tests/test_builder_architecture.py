from __future__ import annotations

import ast
from pathlib import Path

import chatgpt_haber.builder as builder
import chatgpt_haber.cli as cli
import chatgpt_haber.sources as sources


def test_issue_from_rss_has_single_canonical_definition():
    definitions: list[tuple[str, str]] = []
    for path in Path("chatgpt_haber").rglob("*.py"):
        tree = ast.parse(path.read_text(encoding="utf-8"))
        for node in ast.walk(tree):
            if isinstance(node, ast.FunctionDef) and node.name == "issue_from_rss":
                definitions.append((path.as_posix(), node.name))

    assert definitions == [("chatgpt_haber/builder.py", "issue_from_rss")]


def test_cli_uses_canonical_builder_issue_from_rss():
    assert cli.issue_from_rss is builder.issue_from_rss


def test_removed_ankara_and_personal_radar_symbols_do_not_return():
    removed_symbols = {
        "ANKARA" + "_LOCAL_FEEDS",
        "fetch_" + "ankara_local_articles",
        "ankara" + "_articles",
        "PERSONAL" + "_RADAR_CATEGORIES",
        "article" + "_text",
        "keyword" + "_score",
        "category" + "_score",
        "best_article" + "_for_category",
        "personalize" + "_article",
        "personal_radar" + "_page_articles",
    }

    assert not any(hasattr(sources, symbol) for symbol in removed_symbols)


def test_anka_agency_support_is_preserved(monkeypatch):
    rss_article = {"id": "rss-story", "importance": 2}
    anka_article = {"id": "anka-story", "importance": 1}

    monkeypatch.setattr(sources, "parse_feed_articles", lambda feeds, limit: [rss_article])
    monkeypatch.setattr(sources, "extract_anka_articles", lambda limit: [anka_article])
    monkeypatch.setattr(sources, "prioritize_articles", lambda articles: articles)

    articles = sources.fetch_rss_articles()

    assert sources.ANKA_HOMEPAGE_URL == "https://ankahaber.net/"
    assert callable(sources.extract_anka_articles)
    assert anka_article in articles
