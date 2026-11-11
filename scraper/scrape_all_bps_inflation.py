import json
import time
from curl_cffi import requests

TARGETS = [
    {
        "id_wilayah": "konawe",
        "nama": "Kabupaten Konawe",
        "tipe": "Kabupaten",
        "bps_table_id": "NjAxIzI=",
        "var_id": 601,
        "url": "https://sultra.bps.go.id/id/statistics-table/2/NjAxIzI=/inflasi-year-on-year-kabupaten-konawe--2022-100---persen-.html"
    },
    {
        "id_wilayah": "kolaka",
        "nama": "Kabupaten Kolaka",
        "tipe": "Kabupaten",
        "bps_table_id": "NjA1IzI=",
        "var_id": 605,
        "url": "https://sultra.bps.go.id/id/statistics-table/2/NjA1IzI=/inflasi-year-on-year-kabupaten-kolaka--2022-100---persen-.html"
    },
    {
        "id_wilayah": "baubau",
        "nama": "Kota Baubau",
        "tipe": "Kota",
        "bps_table_id": "NjAwIzI=",
        "var_id": 600,
        "url": "https://sultra.bps.go.id/id/statistics-table/2/NjAwIzI=/inflasi-year-on-year-kota-baubau--2022-100---persen-.html"
    },
    {
        "id_wilayah": "kendari",
        "nama": "Kota Kendari",
        "tipe": "Kota",
        "bps_table_id": "NTk5IzI=",
        "var_id": 599,
        "url": "https://sultra.bps.go.id/id/statistics-table/2/NTk5IzI=/inflasi-year-on-year-kota-kendari--2022-100---persen-.html"
    },
    {
        "id_wilayah": "sultra",
        "nama": "Provinsi Sulawesi Tenggara",
        "tipe": "Provinsi",
        "bps_table_id": "NTg5IzI=",
        "var_id": 589,
        "url": "https://sultra.bps.go.id/id/statistics-table/2/NTg5IzI=/inflasi-year-on-year-provinsi-sulawesi-tenggara--2022-100---persen-.html"
    }
]

YEAR_MAP = {
    "2024": "124",
    "2025": "125",
    "2026": "126"
}

MONTH_NAMES = [
    "Januari", "Februari", "Maret", "April", "Mei", "Juni",
    "Juli", "Agustus", "September", "Oktober", "November", "Desember"
]

SERVER_ACTION_ID = "409405684ef06ec6bfa0c43c84b25cb8ccaa4c1366"

headers = {
    "Next-Action": SERVER_ACTION_ID,
    "Content-Type": "text/plain;charset=UTF-8",
    "Accept": "text/x-component",
    "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
}

results = {}

for target in TARGETS:
    w_id = target["id_wilayah"]
    print(f"\nProcessing {target['nama']} (var={target['var_id']})...")
    results[w_id] = {
        "id": w_id,
        "nama": target["nama"],
        "tipe": target["tipe"],
        "bps_table_id": target["bps_table_id"],
        "bps_url": target["url"],
        "var_id": target["var_id"],
        "data_tahunan": {}
    }

    for year_str, th_id in YEAR_MAP.items():
        print(f"  Fetching {year_str} (th_id={th_id})...")
        body = json.dumps([{"locale": "id", "id": target["bps_table_id"], "year": th_id}])
        try:
            resp = requests.post(target["url"], headers=headers, data=body, impersonate="chrome120", timeout=20)
            if resp.status_code != 200:
                print(f"    Error {resp.status_code}")
                continue

            text = resp.text
            idx = text.find('1:{"status":true')
            if idx == -1:
                print(f"    Could not find response JSON in body (len {len(text)})")
                continue

            resp_json = json.loads(text[idx+2:])
            resp_data = resp_json.get("response", {})
            datacontent = resp_data.get("datacontent", {})

            # Vervar 1 is 0. UMUM
            # Key format: vervar(1) + var_id + turvar(0) + th_id + turtahun(1..12)
            monthly_data = []
            for m_idx in range(1, 13):
                key = f"1{target['var_id']}0{th_id}{m_idx}"
                val = datacontent.get(key)
                m_name = MONTH_NAMES[m_idx - 1]
                monthly_data.append({
                    "bulan_angka": m_idx,
                    "bulan_nama": m_name,
                    "periode": f"{m_name[:3]} {year_str}",
                    "periode_lengkap": f"{m_name} {year_str}",
                    "tahun": int(year_str),
                    "inflasi_yoy": val if val is not None else None
                })

            results[w_id]["data_tahunan"][year_str] = {
                "tahun": int(year_str),
                "th_id": th_id,
                "bulanan": monthly_data
            }
            valid_vals = [d["inflasi_yoy"] for d in monthly_data if d["inflasi_yoy"] is not None]
            print(f"    Success: {len(valid_vals)} months with data (e.g. Jan={monthly_data[0]['inflasi_yoy']}%, Sep={monthly_data[8]['inflasi_yoy']}%)")
            time.sleep(1)
        except Exception as e:
            print(f"    Exception: {e}")

output_path = "data/bps_inflation_2024_2026.json"
with open(output_path, "w", encoding="utf-8") as f:
    json.dump(results, f, indent=2)

print(f"\nALL DATA SCRAPED SUCCESSFULLY! Saved to {output_path}")
