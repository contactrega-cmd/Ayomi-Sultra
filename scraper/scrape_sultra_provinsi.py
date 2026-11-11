import json
import time
import sys
import base64

sys.path.append("/Users/regaprasetyo/Library/Python/3.9/lib/python/site-packages")
from curl_cffi import requests

SERVER_ACTION_ID = "409405684ef06ec6bfa0c43c84b25cb8ccaa4c1366"
headers = {
    "Next-Action": SERVER_ACTION_ID,
    "Content-Type": "text/plain;charset=UTF-8",
    "Accept": "text/x-component",
    "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
}

YEAR_MAP = {
    "2024": "124",
    "2025": "125",
    "2026": "126"
}

MONTH_NAMES = [
    "Januari", "Februari", "Maret", "April", "Mei", "Juni",
    "Juli", "Agustus", "September", "Oktober", "November", "Desember"
]
MONTH_SHORT = ["Jan", "Feb", "Mar", "Apr", "Mei", "Jun", "Jul", "Agu", "Sep", "Okt", "Nov", "Des"]

def fetch_table(url, table_id, th_id):
    body = json.dumps([{"locale": "id", "id": table_id, "year": th_id}])
    resp = requests.post(url, headers=headers, data=body, impersonate="chrome120", timeout=25)
    if resp.status_code != 200:
        raise Exception(f"HTTP {resp.status_code}")
    text = resp.text
    idx = text.find('1:{"status":true')
    if idx == -1:
        raise Exception("Marker not found in response")
    data = json.loads(text[idx+2:])
    return data.get("response", {})

def run():
    print("=== Scraping BPS Sultra (Provinsi Sulawesi Tenggara) ===")
    
    # 1. Scraping YoY
    yoy_table_id = "NTg5IzI=" # 589#2
    yoy_var_id = 589
    yoy_url = "https://sultra.bps.go.id/id/statistics-table/2/NTg5IzI=/inflasi-year-on-year-provinsi-sulawesi-tenggara--2022-100---persen-.html"
    
    sultra_yoy_general = {
        "id": "sultra",
        "nama": "Provinsi Sulawesi Tenggara",
        "tipe": "Provinsi",
        "bps_table_id": yoy_table_id,
        "bps_url": yoy_url,
        "var_id": yoy_var_id,
        "data_tahunan": {}
    }
    
    sultra_yoy_groups = {
        "id": "sultra",
        "nama": "Provinsi Sulawesi Tenggara",
        "tipe": "Provinsi",
        "var_id": yoy_var_id,
        "vervar_list": [],
        "data_tahunan": {}
    }
    
    print("\n[1/2] Fetching YoY Data (var 589)...")
    for y_str, th_id in YEAR_MAP.items():
        print(f"  Fetching YoY {y_str} (th_id={th_id})...")
        resp_data = fetch_table(yoy_url, yoy_table_id, th_id)
        datacontent = resp_data.get("datacontent", {})
        vervar = resp_data.get("vervar", [])
        
        if not sultra_yoy_groups["vervar_list"] and vervar:
            sultra_yoy_groups["vervar_list"] = vervar
            
        vervar_map = {item["val"]: item["label"] for item in vervar}
        
        # General inflation (vervar 1: 0. UMUM)
        monthly_general = []
        for m_idx in range(1, 13):
            k = f"1{yoy_var_id}0{th_id}{m_idx}"
            val = datacontent.get(k)
            m_name = MONTH_NAMES[m_idx - 1]
            m_short = MONTH_SHORT[m_idx - 1]
            monthly_general.append({
                "bulan_angka": m_idx,
                "bulan_nama": m_name,
                "periode": f"{m_short} {y_str}",
                "periode_lengkap": f"{m_name} {y_str}",
                "inflasi_yoy": val,
                "tahun": int(y_str)
            })
            
        sultra_yoy_general["data_tahunan"][y_str] = {
            "tahun": int(y_str),
            "th_id": th_id,
            "bulanan": monthly_general
        }
        
        # 11 Groups commodities
        year_commodities = {}
        for v_val, v_label in vervar_map.items():
            monthly_vals = {}
            for m_idx in range(1, 13):
                key = f"{v_val}{yoy_var_id}0{th_id}{m_idx}"
                monthly_vals[str(m_idx)] = datacontent.get(key)
            year_commodities[str(v_val)] = {
                "vervar_val": v_val,
                "label": v_label,
                "bulanan": monthly_vals
            }
            
        sultra_yoy_groups["data_tahunan"][y_str] = {
            "tahun": int(y_str),
            "th_id": th_id,
            "komoditas": year_commodities
        }
        print(f"    Success: Umum Sep {y_str} = {monthly_general[8]['inflasi_yoy']}%")
        time.sleep(1)

    # 2. Scraping MtM
    mtm_table_id = "NTg4IzI=" # 588#2
    mtm_var_id = 588
    mtm_url = "https://sultra.bps.go.id/id/statistics-table/2/NTg4IzI=/inflasi-month-to-month-provinsi-sulawesi-tenggara--2022-100---persen-.html"
    
    sultra_mtm_groups = {
        "id": "sultra",
        "nama": "Provinsi Sulawesi Tenggara",
        "tipe": "Provinsi",
        "bps_table_id": mtm_table_id,
        "bps_url": mtm_url,
        "var_id": mtm_var_id,
        "vervar_list": [],
        "data_tahunan": {}
    }
    
    print("\n[2/2] Fetching MtM Data (var 588)...")
    for y_str, th_id in YEAR_MAP.items():
        print(f"  Fetching MtM {y_str} (th_id={th_id})...")
        resp_data = fetch_table(mtm_url, mtm_table_id, th_id)
        datacontent = resp_data.get("datacontent", {})
        vervar = resp_data.get("vervar", [])
        
        if not sultra_mtm_groups["vervar_list"] and vervar:
            sultra_mtm_groups["vervar_list"] = vervar
            
        vervar_map = {item["val"]: item["label"] for item in vervar}
        
        year_commodities = {}
        for v_val, v_label in vervar_map.items():
            monthly_vals = {}
            for m_idx in range(1, 13):
                key = f"{v_val}{mtm_var_id}0{th_id}{m_idx}"
                monthly_vals[str(m_idx)] = datacontent.get(key)
            year_commodities[str(v_val)] = {
                "vervar_val": v_val,
                "label": v_label,
                "bulanan": monthly_vals
            }
            
        sultra_mtm_groups["data_tahunan"][y_str] = {
            "tahun": int(y_str),
            "th_id": th_id,
            "komoditas": year_commodities
        }
        print(f"    Success: Umum MtM Sep {y_str} = {year_commodities.get('1', {}).get('bulanan', {}).get('9')}%")
        time.sleep(1)

    # 3. Update JSON files in data/
    print("\n[3/3] Saving data to JSON files...")
    
    # Update data/bps_inflation_2024_2026.json
    f1 = "data/bps_inflation_2024_2026.json"
    with open(f1, "r", encoding="utf-8") as f:
        d1 = json.load(f)
    d1["sultra"] = sultra_yoy_general
    with open(f1, "w", encoding="utf-8") as f:
        json.dump(d1, f, indent=2, ensure_ascii=False)
    print(f"  Updated {f1} with key 'sultra'.")

    # Update data/bps_inflation_11_groups_2024_2026.json
    f2 = "data/bps_inflation_11_groups_2024_2026.json"
    with open(f2, "r", encoding="utf-8") as f:
        d2 = json.load(f)
    d2["wilayah"]["sultra"] = sultra_yoy_groups
    with open(f2, "w", encoding="utf-8") as f:
        json.dump(d2, f, indent=2, ensure_ascii=False)
    print(f"  Updated {f2} with key 'wilayah.sultra'.")

    # Update data/bps_inflation_11_groups_mtm_2024_2026.json
    f3 = "data/bps_inflation_11_groups_mtm_2024_2026.json"
    with open(f3, "r", encoding="utf-8") as f:
        d3 = json.load(f)
    d3["wilayah"]["sultra"] = sultra_mtm_groups
    with open(f3, "w", encoding="utf-8") as f:
        json.dump(d3, f, indent=2, ensure_ascii=False)
    print(f"  Updated {f3} with key 'wilayah.sultra'.")

    print("\nAll BPS Sultra data successfully scraped and integrated!")

if __name__ == "__main__":
    run()
