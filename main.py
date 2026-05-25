import json
import os
from jinja2 import Environment, FileSystemLoader
from playwright.sync_api import sync_playwright

BASE_DIR = os.path.dirname(__file__)

DATA_FILE = os.path.join(BASE_DIR, "data", "issue.json")
TEMPLATE_DIR = os.path.join(BASE_DIR, "templates")
OUTPUT_DIR = os.path.join(BASE_DIR, "output")

os.makedirs(OUTPUT_DIR, exist_ok=True)

with open(DATA_FILE, "r", encoding="utf-8") as f:
    data = json.load(f)

env = Environment(loader=FileSystemLoader(TEMPLATE_DIR))

all_pages_html = ""

for page_data in data["pages"]:
    template_name = page_data.get("template", "page.html")
    template_path = os.path.join(TEMPLATE_DIR, template_name)

    if page_data.get("section") == "front_page":
        template = env.get_template("front_page.html")
    elif os.path.exists(template_path) and os.path.getsize(template_path) > 0:
        template = env.get_template(template_name)
    else:
        template = env.get_template("page.html")

    rendered = template.render(
        newspaper=data,
        page=page_data
    )

    all_pages_html += rendered

temp_html = os.path.join(OUTPUT_DIR, "temp.html")

with open(temp_html, "w", encoding="utf-8") as f:
    f.write(all_pages_html)

pdf_path = os.path.join(OUTPUT_DIR, "CHATGPT_HABER.pdf")

with sync_playwright() as p:
    browser = p.chromium.launch()
    page = browser.new_page(viewport={"width": 1240, "height": 1754})

    page.goto(f"file:///{temp_html.replace(os.sep, '/')}", wait_until="networkidle")

    page.pdf(
        path=pdf_path,
        format="A4",
        print_background=True,
        prefer_css_page_size=True
    )

    browser.close()

print("PDF oluşturuldu:")
print(pdf_path)
