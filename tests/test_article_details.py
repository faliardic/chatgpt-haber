from __future__ import annotations

from copy import deepcopy

import pytest

from chatgpt_haber.sources import enrich_article_details, extract_article_detail, extract_article_detail_with_status


class FakeResponse:
    def __init__(self, text: str) -> None:
        self.text = text

    def raise_for_status(self) -> None:
        return None


def install_fake_get(monkeypatch: pytest.MonkeyPatch, html_by_url: dict[str, str], calls: dict[str, int]) -> None:
    import requests

    def fake_get(url: str, **_kwargs):
        calls[url] = calls.get(url, 0) + 1
        if url == "https://example.com/error":
            raise requests.RequestException("blocked")
        return FakeResponse(html_by_url[url])

    monkeypatch.setattr(requests, "get", fake_get)


def test_extract_article_detail_prefers_json_ld_article_body(monkeypatch):
    html = """
    <html><head>
      <script type="application/ld+json">
      {"@type":"NewsArticle","articleBody":"Birinci anlamlı paragraf haberin ana gelişmesini geniş biçimde anlatır. İkinci anlamlı paragraf kamuoyuna yansıyan ayrıntıları ve bağlamı verir. Üçüncü anlamlı paragraf sonraki adımları ve etkileri açıklar."}
      </script>
    </head><body><article><p>Kısa gövde dikkate alınmaz.</p></article></body></html>
    """
    calls: dict[str, int] = {}
    install_fake_get(monkeypatch, {"https://example.com/json": html}, calls)

    paragraphs, status = extract_article_detail_with_status("https://example.com/json", "Test başlık")

    assert status == "json_ld_extracted"
    assert len(paragraphs) == 3
    assert calls == {"https://example.com/json": 1}


def test_extract_article_detail_uses_semantic_html_and_filters_noise(monkeypatch):
    html = """
    <main><article>
      <p>Test başlık</p>
      <p>Birinci anlamlı paragraf gelişmenin neden önemli olduğunu yeterli ayrıntıyla açıklar.</p>
      <p>Birinci anlamlı paragraf gelişmenin neden önemli olduğunu yeterli ayrıntıyla açıklar.</p>
      <div class="reklam">Reklam alanı hemen kapatılmalıdır.</div>
      <footer>Kaynak ve sosyal medya paylaşım metni.</footer>
      <p>İkinci anlamlı paragraf kararın arka planını ve ilgili kurumların açıklamalarını aktarır.</p>
      <p>Üçüncü anlamlı paragraf bundan sonra izlenecek süreci ve beklenen takvimi anlatır.</p>
    </article></main>
    """
    calls: dict[str, int] = {}
    install_fake_get(monkeypatch, {"https://example.com/html": html}, calls)

    paragraphs = extract_article_detail("https://example.com/html", "Test başlık")

    assert len(paragraphs) == 3
    assert all("Reklam" not in paragraph for paragraph in paragraphs)
    assert all("Kaynak" not in paragraph for paragraph in paragraphs)


def test_extract_article_detail_applies_minimum_and_og_fallback(monkeypatch):
    html = """
    <html><head>
      <meta property="og:description" content="Bu açıklama kaynak sayfa erişilemediğinde haber detayında kullanılabilecek kadar anlamlı bir özet sağlar.">
    </head><body><article><p>Çok kısa.</p></article></body></html>
    """
    calls: dict[str, int] = {}
    install_fake_get(monkeypatch, {"https://example.com/og": html}, calls)

    paragraphs, status = extract_article_detail_with_status("https://example.com/og", "Başlık")

    assert status == "summary_fallback"
    assert len(paragraphs) == 1
    assert "anlamlı bir özet" in paragraphs[0]


def test_extract_article_detail_caps_to_twelve_paragraphs(monkeypatch):
    paragraphs = "".join(
        f"<p>{index}. anlamlı paragraf kararın ayrıntılarını ve etkilerini yeterli uzunlukta açıklar.</p>"
        for index in range(1, 18)
    )
    calls: dict[str, int] = {}
    install_fake_get(monkeypatch, {"https://example.com/many": f"<article>{paragraphs}</article>"}, calls)

    result = extract_article_detail("https://example.com/many", "Başlık")

    assert len(result) == 12


def test_enrich_article_details_caches_url_and_sets_fallback_metrics(monkeypatch):
    html = """
    <article>
      <p>Birinci anlamlı paragraf güncel gelişmeyi yeterli ayrıntıyla açıklar.</p>
      <p>İkinci anlamlı paragraf ilgili kurumların açıklamalarını aktarır.</p>
      <p>Üçüncü anlamlı paragraf sonraki adımların takvimini ve etkilerini anlatır.</p>
    </article>
    """
    calls: dict[str, int] = {}
    install_fake_get(
        monkeypatch,
        {
            "https://example.com/shared": html,
            "https://example.com/error": "",
        },
        calls,
    )
    article = {
        "headline": "Paylaşılan haber",
        "dek": "Kısa özet",
        "body": ["RSS özeti korunur."],
        "source_bundle": [{"url": "https://example.com/shared"}],
    }
    issue = {
        "pages": [
            {
                "articles": [deepcopy(article)],
                "briefs": [
                    deepcopy(article),
                    {
                        "headline": "Erişilemeyen haber",
                        "dek": "RSS özeti detay boş kalmasın diye kullanılır.",
                        "body": [],
                        "source_bundle": [{"url": "https://example.com/error"}],
                    },
                ],
            }
        ]
    }

    enrich_article_details(issue)

    assert calls["https://example.com/shared"] == 1
    assert issue["pages"][0]["articles"][0]["detail_status"] == "source_extracted"
    assert issue["pages"][0]["briefs"][0]["detail_status"] == "source_extracted"
    assert issue["pages"][0]["briefs"][1]["detail_status"] == "summary_fallback"
    assert issue["pages"][0]["briefs"][1]["detail_paragraph_count"] == 1
    assert issue["pages"][0]["briefs"][1]["detail_character_count"] > 0
