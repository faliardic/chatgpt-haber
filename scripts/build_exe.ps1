$ErrorActionPreference = "Stop"

$projectRoot = Split-Path -Parent $PSScriptRoot
Set-Location $projectRoot

python -m pip install --upgrade pip
python -m pip install -e .
python -m pip install pyinstaller

$env:PLAYWRIGHT_BROWSERS_PATH = "0"
python -m playwright install chromium

python -m PyInstaller `
  --clean `
  --noconfirm `
  --noconsole `
  --name ChatGPTHaber `
  --collect-all playwright `
  --add-data "templates;templates" `
  --add-data "static;static" `
  --add-data "data;data" `
  --add-data "schemas;schemas" `
  chatgpt_haber\one_click.py

Write-Host ""
Write-Host "Hazir: $projectRoot\dist\ChatGPTHaber\ChatGPTHaber.exe"
Write-Host "Bu klasoru komple baska bilgisayara kopyalayabilirsiniz."
