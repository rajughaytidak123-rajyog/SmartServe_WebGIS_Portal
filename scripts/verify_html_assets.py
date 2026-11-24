import os
import re
from pathlib import Path

html_files = ['index.html', 'discover.html', 'accessibility.html', 'insights.html', 'about.html']
all_ok = True

for h in html_files:
    print(f"=== Checking {h} ===")
    content = Path(h).read_text(encoding='utf-8')
    refs = re.findall(r'(?:href|src)=["\']([^"\']+)["\']', content)
    for r in refs:
        if r.startswith('http') or r.startswith('//') or r.startswith('#') or r.startswith('data:'):
            continue
        clean_r = r.split('?')[0].split('#')[0]
        if not clean_r:
            continue
        p = Path(clean_r)
        if p.exists():
            print(f"  [OK] {r} -> ({p.stat().st_size} bytes)")
        else:
            print(f"  [MISSING!] {r} -> {p.resolve()}")
            all_ok = False

if all_ok:
    print("\n[SUCCESS] 100% of all local assets in HTML files exist!")
else:
    print("\n[ERROR] Missing assets found!")
    exit(1)
