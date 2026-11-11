#!/usr/bin/env python3
"""
BACKFILL DATA HARIAN EMPIRIS PIHPS BANK INDONESIA (2024 - 2026)
Menarik deret harga harian resmi Pasar Tradisional (10 Komoditas Utama Level 1)
untuk:
- Kota Kendari (regency_id=72)
- Kota Bau-Bau (regency_id=73)
- Provinsi Sulawesi Tenggara (Rata-rata, regency_id="")

Digunakan sebagai basis historis >= 120 hari kerja untuk model MH-WMA (MA 5, 20, 60, 120).
"""

import os
import sys
import json
import time
import urllib.request
import urllib.parse
from datetime import datetime, date, timedelta

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DATA_DIR = os.path.join(BASE_DIR, "data")
OUT_PATH = os.path.join(DATA_DIR, "pihps_daily_cities_2024_2026.json")

BASE_URL = "https://www.bi.go.id/hargapangan/WebSite/TabelHarga/GetGridDataDaerah"
PROVINCE_ID = "27"

CITIES = [
    {"id": 72, "name": "Kota Kendari"},
    {"id": 73, "name": "Kota Bau-Bau"},
    {"id": "", "name": "Provinsi Sulawesi Tenggara (Rata-rata)"},
]

COMMODITIES_10 = [
    "Beras",
    "Daging Ayam",
    "Daging Sapi",
    "Telur Ayam",
    "Bawang Merah",
    "Bawang Putih",
    "Cabai Merah",
    "Cabai Rawit",
    "Minyak Goreng",
    "Gula Pasir",
]

HEADERS = {
    "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36",
    "Accept": "application/json, text/javascript, */*; q=0.01",
    "X-Requested-With": "XMLHttpRequest",
    "Referer": "https://www.bi.go.id/hargapangan/home/index",
}


def parse_price(val):
    if val is None:
        return None
    s = str(val).strip()
    if not s or s == "-" or s.lower() == "null":
        return None
    clean = s.replace(",", "").replace(".", "").replace("Rp", "").strip()
    try:
        num = int(round(float(clean)))
        return num if num > 0 else None
    except Exception:
        return None


def generate_quarter_chunks(start_dt, end_dt):
    chunks = []
    cur = start_dt
    while cur <= end_dt:
        chunk_end = min(end_dt, cur + timedelta(days=61))
        chunks.append((cur.strftime("%Y-%m-%d"), chunk_end.strftime("%Y-%m-%d")))
        cur = chunk_end + timedelta(days=1)
    return chunks


def fetch_chunk(regency_id, start_str, end_str, max_retries=3):
    params = {
        "price_type_id": 1,  # Pasar Tradisional
        "comcat_id": "",
        "province_id": PROVINCE_ID,
        "regency_id": str(regency_id) if regency_id != "" else "",
        "market_id": "",
        "tipe_laporan": 1,  # Harian
        "start_date": start_str,
        "end_date": end_str,
    }
    url = f"{BASE_URL}?{urllib.parse.urlencode(params)}"
    for attempt in range(1, max_retries + 1):
        try:
            req = urllib.request.Request(url, headers=HEADERS)
            with urllib.request.urlopen(req, timeout=30) as resp:
                if resp.status == 200:
                    return json.loads(resp.read().decode("utf-8"))
        except Exception as exc:
            if attempt < max_retries:
                time.sleep(1.5 * attempt)
            else:
                print(f"  [ERR] Gagal fetch {regency_id} ({start_str}..{end_str}): {exc}")
                return None
    return None


def sort_ddmmyyyy(date_keys):
    return sorted(
        date_keys,
        key=lambda d: [int(x) for x in reversed(d.split("/"))] if "/" in d else [0, 0, 0],
    )


def run_backfill(start_date=date(2024, 1, 1), end_date=None):
    if end_date is None:
        end_date = datetime.now().date()

    os.makedirs(DATA_DIR, exist_ok=True)
    chunks = generate_quarter_chunks(start_date, end_date)
    print("=" * 85)
    print("BACKFILL DATA HARIAN EMPIRIS PIHPS BI (KENDARI, BAU-BAU, PROVINSI SULTRA)")
    print(f"Periode: {start_date.isoformat()} s.d. {end_date.isoformat()} ({len(chunks)} blok ~2 bulan/blok)")
    print("=" * 85)

    data_harian = {
        c["name"]: {comm: {} for comm in COMMODITIES_10}
        for c in CITIES
    }

    for city in CITIES:
        cid = city["id"]
        cname = city["name"]
        print(f"\n-> Menarik harian empiris: {cname} (regency_id={cid!r})...")
        for idx, (s_str, e_str) in enumerate(chunks, 1):
            payload = fetch_chunk(cid, s_str, e_str)
            rows = payload.get("data", []) if isinstance(payload, dict) else []
            lvl1 = [r for r in rows if r.get("level") == 1]

            by_name = {}
            for r in lvl1:
                nm = str(r.get("name", "")).strip()
                by_name[nm] = r

            added_dates = set()
            for comm in COMMODITIES_10:
                row = by_name.get(comm)
                if not row:
                    for k, v in by_name.items():
                        if k.lower() == comm.lower():
                            row = v
                            break
                if not row:
                    continue
                for k, v in row.items():
                    if "/" in k and k not in ("no", "name", "level", "id", "cat_id"):
                        p = parse_price(v)
                        if p is not None:
                            data_harian[cname][comm][k] = p
                            added_dates.add(k)

            print(f"   [{idx:02d}/{len(chunks):02d}] {s_str} .. {e_str} -> {len(added_dates)} hari survei")
            time.sleep(0.2)

        # Sort keys kronologis untuk tiap komoditas
        for comm in COMMODITIES_10:
            raw_dict = data_harian[cname][comm]
            sorted_keys = sort_ddmmyyyy(raw_dict.keys())
            data_harian[cname][comm] = {k: raw_dict[k] for k in sorted_keys}

    # Ringkasan kelengkapan
    summary = {}
    all_dates_set = set()
    print("\n" + "=" * 85)
    print("RINGKASAN KELENGKAPAN DERET HARIAN PIHPS BI (PASAR TRADISIONAL)")
    print("=" * 85)
    for cname, comms in data_harian.items():
        summary[cname] = {}
        print(f"\n[{cname}]")
        for comm in COMMODITIES_10:
            dmap = comms[comm]
            keys = list(dmap.keys())
            for dk in keys:
                all_dates_set.add(dk)
            first_d = keys[0] if keys else "-"
            last_d = keys[-1] if keys else "-"
            summary[cname][comm] = {
                "count": len(keys),
                "first_date": first_d,
                "last_date": last_d,
            }
            print(f"  - {comm:<15}: {len(keys):>3} hari ({first_d} s.d. {last_d})")

    sorted_all_dates = sort_ddmmyyyy(all_dates_set)
    out_payload = {
        "metadata": {
            "sumber": "PIHPS Nasional - Bank Indonesia (GetGridDataDaerah, Pasar Tradisional, Harian Empiris)",
            "periode_mulai": sorted_all_dates[0] if sorted_all_dates else "-",
            "periode_selesai": sorted_all_dates[-1] if sorted_all_dates else "-",
            "total_tanggal_unik": len(sorted_all_dates),
            "waktu_ekstraksi": datetime.now().isoformat(),
        },
        "summary": summary,
        "data_harian": data_harian,
    }

    tmp_path = OUT_PATH + ".tmp"
    with open(tmp_path, "w", encoding="utf-8") as f:
        json.dump(out_payload, f, ensure_ascii=False, separators=(",", ":"))
    os.replace(tmp_path, OUT_PATH)

    print(f"\n[SUKSES] Disimpan ke: {OUT_PATH} ({os.path.getsize(OUT_PATH) / 1024:.1f} KB)")
    return out_payload


if __name__ == "__main__":
    run_backfill()
