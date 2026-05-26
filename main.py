from datetime import date
from pathlib import Path

from chatgpt_haber.issue import BASE_DIR, normalize_issue, read_json, validate_issue_data, write_json
from chatgpt_haber.render import render_html, render_pdf
from chatgpt_haber.sources import issue_from_rss


def main() -> None:
    output_dir = BASE_DIR / "dist"
    html_path = output_dir / "CHATGPT_HABER.html"
    pdf_path = output_dir / "CHATGPT_HABER.pdf"
    issue_date = date.today().isoformat()
    paper_size = "A3"

    issue_data = issue_from_rss(issue_date, paper_size)
    if issue_data is None:
        data_file = BASE_DIR / "data" / "issue.json"
        issue_data = normalize_issue(read_json(data_file), issue_date=issue_date, paper_size=paper_size)

    validate_issue_data(issue_data)
    write_json(output_dir / "issue.json", issue_data)
    render_html(issue_data, html_path)
    render_pdf(html_path, pdf_path)

    print("HTML oluşturuldu:")
    print(Path(html_path))
    print("PDF oluşturuldu:")
    print(Path(pdf_path))


if __name__ == "__main__":
    main()
