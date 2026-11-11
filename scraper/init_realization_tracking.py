#!/usr/bin/env python3
"""
Generator & Initializer: Daily Realization vs Forecast Tracking
Menggabungkan baseline proyeksi 7 hari dari SARIMAX, Prophet, dan ARIMA
serta memelihara nilai realisasi rilis resmi PIHPS.
"""

import os
import json

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DATA_DIR = os.path.join(BASE_DIR, "data")

SARIMAX_FILE = os.path.join(DATA_DIR, "sarimax_forecast_all_commodities.json")
PROPHET_FILE = os.path.join(DATA_DIR, "prophet_forecast_all_commodities.json")
ARIMA_FILE = os.path.join(DATA_DIR, "arima_forecast_all_commodities.json")
TRACKING_FILE = os.path.join(DATA_DIR, "daily_realization_tracking.json")

def clean_day_name(hari_raw):
    # E.g. "Senin, 12 Okt 2026" -> "Senin"
    if "," in hari_raw:
        return hari_raw.split(",")[0].strip()
    return hari_raw.strip()

def build_tracking_data():
    if not (os.path.exists(SARIMAX_FILE) and os.path.exists(PROPHET_FILE) and os.path.exists(ARIMA_FILE)):
        print("[ERROR] Berkas model proyeksi belum lengkap di direktori data/")
        return None

    with open(SARIMAX_FILE, "r", encoding="utf-8") as f:
        sarimax_data = json.load(f)
    with open(PROPHET_FILE, "r", encoding="utf-8") as f:
        prophet_data = json.load(f)
    with open(ARIMA_FILE, "r", encoding="utf-8") as f:
        arima_data = json.load(f)

    # Muat data eksisting jika ada untuk melestarikan input realisasi yang sudah diinput
    existing_tracking = {}
    if os.path.exists(TRACKING_FILE):
        try:
            with open(TRACKING_FILE, "r", encoding="utf-8") as f:
                existing_tracking = json.load(f)
        except Exception:
            existing_tracking = {}

    commodities = list(sarimax_data.keys())
    output = {}

    for c in commodities:
        s_com = sarimax_data.get(c, {})
        p_com = prophet_data.get(c, {})
        a_com = arima_data.get(c, {})

        s_proj = s_com.get("proyeksi_7_hari", [])
        p_proj = p_com.get("proyeksi_7_hari", [])
        a_proj = a_com.get("proyeksi_7_hari", [])

        satuan = s_com.get("satuan", "kg")
        icon = s_com.get("icon", "📦")
        harga_terakhir = s_com.get("harga_terakhir", 0)
        tanggal_terakhir = s_com.get("tanggal_terakhir", "09/10/2026")

        existing_c = existing_tracking.get(c, {}).get("tracking", [])
        existing_lookup = {item["tanggal"]: item.get("realisasi_pihps") for item in existing_c if "tanggal" in item}

        tracking_list = []
        for i in range(min(len(s_proj), len(p_proj), len(a_proj), 5)):
            s_item = s_proj[i]
            p_item = p_proj[i]
            a_item = a_proj[i]

            tgl = s_item.get("tanggal")
            hari = clean_day_name(s_item.get("hari", f"H+{i+1}"))
            label = s_item.get("label", tgl)
            step = i + 1

            s_val = round(float(s_item.get("harga_proyeksi", 0)), 2)
            p_val = round(float(p_item.get("harga_proyeksi", 0)), 2)
            a_val = round(float(a_item.get("harga_proyeksi", 0)), 2)

            # Pertahankan nilai realisasi lama jika sudah ada
            realisasi_val = existing_lookup.get(tgl, None)

            tracking_list.append({
                "step": step,
                "hari": hari,
                "tanggal": tgl,
                "label": label,
                "realisasi_pihps": realisasi_val,
                "proyeksi_sarimax": s_val,
                "proyeksi_prophet": p_val,
                "proyeksi_arima": a_val
            })

        output[c] = {
            "komoditas": c,
            "satuan": satuan,
            "icon": icon,
            "baseline_date": tanggal_terakhir,
            "baseline_price": harga_terakhir,
            "tracking": tracking_list
        }

    with open(TRACKING_FILE, "w", encoding="utf-8") as f:
        json.dump(output, f, indent=2, ensure_ascii=False)

    print(f"[SUCCESS] Dataset tracking berhasil dibuat untuk {len(output)} komoditas di {TRACKING_FILE}")
    return output

if __name__ == "__main__":
    build_tracking_data()
