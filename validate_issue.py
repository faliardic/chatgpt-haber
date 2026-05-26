from pathlib import Path
import sys

from chatgpt_haber.issue import normalize_issue, read_json, validate_issue_data


BASE_DIR = Path(__file__).resolve().parent
ISSUE_PATH = BASE_DIR / "data" / "issue.json"


def fail(message: str) -> None:
    print(f"VALIDATION ERROR: {message}")
    sys.exit(1)


def main() -> None:
    if not ISSUE_PATH.exists():
        fail(f"issue.json bulunamadı: {ISSUE_PATH}")

    try:
        issue_data = normalize_issue(read_json(ISSUE_PATH))
        validate_issue_data(issue_data)
    except Exception as error:
        fail(str(error))

    print("OK: issue.json 3 sayfalık gazete sözleşmesinden geçti.")
    print(f"OK: Dosya: {ISSUE_PATH}")


if __name__ == "__main__":
    main()
