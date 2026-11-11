import urllib.request
import json
import re

urls = {
    "Konawe": "https://sultra.bps.go.id/id/statistics-table/2/NjAxIzI=/inflasi-year-on-year-kabupaten-konawe--2022-100---persen-.html",
    "Kolaka": "https://sultra.bps.go.id/id/statistics-table/2/NjA1IzI=/inflasi-year-on-year-kabupaten-kolaka--2022-100---persen-.html",
    "Baubau": "https://sultra.bps.go.id/id/statistics-table/2/NjAwIzI=/inflasi-year-on-year-kota-baubau--2022-100---persen-.html",
    "Kendari": "https://sultra.bps.go.id/id/statistics-table/2/NTk5IzI=/inflasi-year-on-year-kota-kendari--2022-100---persen-.html"
}

headers = {
    "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,*/*;q=0.8",
    "Accept-Language": "id,en-US;q=0.7,en;q=0.3"
}

for name, url in urls.items():
    print(f"Fetching {name}...")
    try:
        req = urllib.request.Request(url, headers=headers)
        with urllib.request.urlopen(req, timeout=15) as resp:
            html = resp.read().decode('utf-8', errors='ignore')
            print(f"Success {name}: length={len(html)}")
            with open(f"data/bps_raw_{name.lower()}.html", "w", encoding="utf-8") as out:
                out.write(html)
    except Exception as e:
        print(f"Error {name}: {e}")
