import json
import time
import sys
import base64

sys.path.append("/Users/regaprasetyo/Library/Python/3.9/lib/python/site-packages")
from curl_cffi import requests

TARGETS = [
    {
        "id_wilayah": "konawe",
        "nama": "Kabupaten Konawe",
        "tipe": "Kabupaten",
        "bps_table_id": base64.b64encode(b"607#2").decode(),
        "var_id": 607,
        "url": f"https://sultra.bps.go.id/id/statistics-table/2/{base64.b64encode(b'607#2').decode()}/inflasi-month-to-month-kabupaten-konawe--2022-100---persen-.html"
    },
    {
        "id_wilayah": "kolaka",
        "nama": "Kabupaten Kolaka",
        "tipe": "Kabupaten",
        "bps_table_id": base64.b64encode(b"608#2").decode(),
        "var_id": 608,
        "url": f"https://sultra.bps.go.id/id/statistics-table/2/{base64.b64encode(b'608#2').decode()}/inflasi-month-to-month-kabupaten-kolaka--2022-100---persen-.html"
    },
    {
        "id_wilayah": "baubau",
        "nama": "Kota Baubau",
        "tipe": "Kota",
        "bps_table_id": base64.b64encode(b"606#2").decode(),
        "var_id": 606,
        "url": f"https://sultra.bps.go.id/id/statistics-table/2/{base64.b64encode(b'606#2').decode()}/inflasi-month-to-month-kota-baubau--2022-100---persen-.html"
    },
    {
        "id_wilayah": "kendari",
        "nama": "Kota Kendari",
        "tipe": "Kota",
        "bps_table_id": base64.b64encode(b"595#2").decode(),
        "var_id": 595,
        "url": f"https://sultra.bps.go.id/id/statistics-table/2/{base64.b64encode(b'595#2').decode()}/inflasi-month-to-month-kota-kendari--2022-100---persen-.html"
    }
]

YEAR_MAP = {
    "2024": "124",
    "2025": "125",
    "2026": "126"
}

SERVER_ACTION_ID = "409405684ef06ec6bfa0c43c84b25cb8ccaa4c1366"

headers = {
    "Next-Action": SERVER_ACTION_ID,
    "Content-Type": "text/plain;charset=UTF-8",
    "Accept": "text/x-component",
    "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
}

STANDARD_11_GROUPS = [
    {"kode": "01", "nama": "Makanan, Minuman, dan Tembakau"},
    {"kode": "02", "nama": "Pakaian dan Alas Kaki"},
    {"kode": "03", "nama": "Perumahan, Air, Listrik, dan Bahan Bakar Rumah Tangga"},
    {"kode": "04", "nama": "Perlengkapan, Peralatan, dan Pemeliharaan Rutin Rumah Tangga"},
    {"kode": "05", "nama": "Kesehatan"},
    {"kode": "06", "nama": "Transportasi"},
    {"kode": "07", "nama": "Informasi, Komunikasi, dan Jasa Keuangan"},
    {"kode": "08", "nama": "Rekreasi, Olahraga, dan Budaya"},
    {"kode": "09", "nama": "Pendidikan"},
    {"kode": "10", "nama": "Penyediaan Makanan dan Minuman / Restoran"},
    {"kode": "11", "nama": "Perawatan Pribadi dan Jasa Lainnya"}
]

results = {
    "metadata": {
        "sumber": "Badan Pusat Statistik (BPS) Provinsi Sulawesi Tenggara",
        "indikator": "Inflasi Month-to-Month (MtM)",
        "basis": "2022=100",
        "tahun_tersedia": [2024, 2025, 2026],
        "kelompok_standar": STANDARD_11_GROUPS
    },
    "wilayah": {}
}

for target in TARGETS:
    w_id = target["id_wilayah"]
    print(f"\n=======================================================")
    print(f"Scraping MtM: {target['nama']} (var_id={target['var_id']})")
    print(f"=======================================================")
    
    results["wilayah"][w_id] = {
        "id": w_id,
        "nama": target["nama"],
        "tipe": target["tipe"],
        "var_id": target["var_id"],
        "vervar_list": [],
        "data_tahunan": {}
    }

    for year_str, th_id in YEAR_MAP.items():
        print(f"  --> Fetching Year {year_str} (th_id={th_id})...")
        body = json.dumps([{"locale": "id", "id": target["bps_table_id"], "year": th_id}])
        try:
            resp = requests.post(target["url"], headers=headers, data=body, impersonate="chrome120", timeout=25)
            if resp.status_code != 200:
                print(f"      [ERROR] HTTP {resp.status_code}")
                continue

            text = resp.text
            idx = text.find('1:{"status":true')
            if idx == -1:
                print(f"      [WARN] Next-Action marker not found in response (len {len(text)})")
                continue

            resp_json = json.loads(text[idx+2:])
            resp_data = resp_json.get("response", {})
            datacontent = resp_data.get("datacontent", {})
            vervar = resp_data.get("vervar", [])

            if not results["wilayah"][w_id]["vervar_list"] and vervar:
                results["wilayah"][w_id]["vervar_list"] = vervar

            vervar_map = {item["val"]: item["label"] for item in vervar}

            year_commodities = {}
            for v_val, v_label in vervar_map.items():
                monthly_vals = {}
                for m_idx in range(1, 13):
                    key = f"{v_val}{target['var_id']}0{th_id}{m_idx}"
                    val = datacontent.get(key)
                    monthly_vals[m_idx] = val

                year_commodities[str(v_val)] = {
                    "vervar_val": v_val,
                    "label": v_label,
                    "bulanan": monthly_vals
                }

            results["wilayah"][w_id]["data_tahunan"][year_str] = {
                "tahun": int(year_str),
                "th_id": th_id,
                "komoditas": year_commodities
            }

            non_null_count = sum(1 for c in year_commodities.values() if any(v is not None for v in c["bulanan"].values()))
            print(f"      [OK] Received {len(year_commodities)} commodity items, {non_null_count} items with data.")
            time.sleep(1.0)
        except Exception as e:
            print(f"      [EXCEPTION] {e}")

output_path = "data/bps_inflation_11_groups_mtm_2024_2026.json"
with open(output_path, "w", encoding="utf-8") as f:
    json.dump(results, f, indent=2)

print(f"\n[DONE] All MtM data successfully written to {output_path}")
