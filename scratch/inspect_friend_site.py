import urllib.request
import re

url = "https://harnishsavant.github.io/Vibe_Pune_NearByService/discover.html"
try:
    req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0"})
    with urllib.request.urlopen(req) as response:
        html = response.read().decode("utf-8", errors="ignore")
        print("HTTP Status:", response.getcode())
        print("HTML Length:", len(html))
        
        # Title
        titles = re.findall(r"<title>(.*?)</title>", html, re.I | re.S)
        print("Title:", titles[0].strip() if titles else "None")
        
        # Navigation Links
        navs = re.findall(r"<nav.*?</nav>", html, re.I | re.S)
        print("\nNav content:")
        for n in navs:
            print(n[:500])
            
        links = re.findall(r'<a[^>]+href=["\']([^"\']+)["\'][^>]*>(.*?)</a>', html, re.I | re.S)
        print("\nFound Links (first 25):")
        for href, text in links[:25]:
            clean_text = re.sub(r'<[^>]+>', '', text).strip()
            print(f"  - {clean_text} -> {href}")

        # Headings / Sections
        h1s = re.findall(r"<h[1-3][^>]*>(.*?)</h[1-3]>", html, re.I | re.S)
        print("\nHeadings:")
        for h in h1s[:15]:
            clean_h = re.sub(r'<[^>]+>', '', h).strip()
            print(f"  * {clean_h}")
            
except Exception as e:
    print("Error:", e)
