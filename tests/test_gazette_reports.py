from pathlib import Path

from services.gazette_reports import generate_earthquake_report, generate_source_report, write_reports
from services.user_profile import DEFAULT_PROFILE, load_profile, save_profile


def sample_issue():
    return {
        "issue": {"issue_date": "2026-06-01"},
        "pages": [
            {
                "page_no": 1,
                "articles": [
                    {
                        "id": "a1",
                        "headline": "Ekonomi haberi",
                        "importance": 1,
                        "importance_score": 72,
                        "source_bundle": [{"name": "ANKA Haber Ajansı"}],
                        "image": {"path": "x.jpg"},
                    }
                ],
                "briefs": [],
            }
        ],
    }


def test_generate_source_report_counts_sources():
    report = generate_source_report(sample_issue())

    assert report["sources"][0]["source"] == "ANKA Haber Ajansı"
    assert report["sources"][0]["total"] == 1
    assert report["sources"][0]["image_rate"] == 1


def test_write_reports_creates_json_and_html(tmp_path):
    paths = write_reports(sample_issue(), tmp_path)

    assert paths["source_report"].exists()
    assert paths["source_report_html"].exists()
    assert paths["quality_report"].exists()


def test_earthquake_report_lists_only_earthquake_items():
    issue = sample_issue()
    issue["pages"][0]["articles"].append({"id": "e1", "headline": "Depremde hasar oluştu", "earthquake_classification": "serious_earthquake_event"})

    report = generate_earthquake_report(issue)

    assert [item["id"] for item in report["earthquake_items"]] == ["e1"]


def test_user_profile_roundtrip(tmp_path, monkeypatch):
    monkeypatch.setenv("APPDATA", str(tmp_path))
    path = save_profile({"ankara": 3, "ekonomi": 1, "unknown": 3})

    assert path.exists()
    profile = load_profile()
    assert profile["ankara"] == 3
    assert profile["ekonomi"] == 1
    assert set(DEFAULT_PROFILE).issubset(profile)
