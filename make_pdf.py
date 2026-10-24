import os
import subprocess
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent
html_path = BASE_DIR / 'project_documentation.html'
pdf_path = BASE_DIR / 'AI_Campus_Infrastructure_Project_Documentation.pdf'

browsers = [
    r'C:\Program Files (x86)\Microsoft\Edge\Application\msedge.exe',
    r'C:\Program Files\Google\Chrome\Application\chrome.exe'
]

browser_bin = None
for b in browsers:
    if os.path.exists(b):
        browser_bin = b
        break

if not browser_bin:
    print('No browser found')
    exit(1)

file_url = html_path.as_uri()
cmd = [
    browser_bin,
    '--headless',
    '--disable-gpu',
    '--no-pdf-header-footer',
    f'--print-to-pdf={pdf_path}',
    file_url
]

print(f'Using browser: {browser_bin}')
print(f'Input: {file_url}')
print(f'Output: {pdf_path}')

res = subprocess.run(cmd, capture_output=True, text=True)
print(f'Return code: {res.returncode}')
if pdf_path.exists():
    size_kb = pdf_path.stat().st_size / 1024
    print(f'[SUCCESS] PDF created! Size: {size_kb:.1f} KB ({pdf_path.stat().st_size} bytes)')
else:
    print(f'[ERROR] PDF was not created. Stderr: {res.stderr}')
