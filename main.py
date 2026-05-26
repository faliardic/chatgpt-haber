from pathlib import Path

from chatgpt_haber.issue import BASE_DIR, normalize_issue, read_json, validate_issue_data, write_json
from chatgpt_haber.render import render_html, render_pdf


def main() -> None:
    data_file = BASE_DIR / "data" / "issue.json"
    output_dir = BASE_DIR / "output"
    html_path = output_dir / "CHATGPT_HABER.html"
    pdf_path = output_dir / "CHATGPT_HABER.pdf"

    issue_data = normalize_issue(read_json(data_file))
    validate_issue_data(issue_data)
    write_json(output_dir / "issue.json", issue_data)
    render_html(issue_data, html_path)
    render_pdf(html_path, pdf_path)

    print("PDF oluşturuldu:")
    print(Path(pdf_path))


if __name__ == "__main__":
    main()
