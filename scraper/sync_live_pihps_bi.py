#!/usr/bin/env python3
"""
SINKRONISASI REAL-TIME DATA HARGA PANGAN PIHPS BANK INDONESIA (SULAWESI TENGGARA)
Scraping komprehensif langsung dari endpoint resmi Bank Indonesia:
https://www.bi.go.id/hargapangan/WebSite/TabelHarga/GetGridDataDaerah

Mencakup:
1. 4 Tipe Pasar:
   - Pasar Tradisional (price_type_id: 1)
   - Pasar Modern (price_type_id: 2)
   - Pedagang Besar (price_type_id: 3)
   - Produsen (price_type_id: 4)
2. 3 Wilayah di Sultra:
   - Provinsi Sulawesi Tenggara (Rata-rata se-Provinsi, regency_id: "")
   - Kota Kendari (regency_id: 72)
   - Kota Bau-Bau (regency_id: 73)
3. 10 Komoditas Utama (Level 1) + 21 Varian Rinci (Level 2) = 31 Komoditas
4. Pemutakhiran dataset:
   - data/pihps_sultra_all.json
   - data/pihps_daily_lookup.json
   - data/bi_daily_jul_oct_2026.json
   - data/bi_daily_2024_2026.json
   - data/bi_pihps_weekly.json
   - data/daily_realization_tracking.json
"""

import os
import sys
import json
import time
import urllib.request
import urllib.parse
from datetime import datetime, timedelta
import shutil

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if BASE_DIR not in sys.path:
    sys.path.insert(0, BASE_DIR)
DATA_DIR = os.path.join(BASE_DIR, "data")

BASE_URL = "https://www.bi.go.id/hargapangan/WebSite/TabelHarga/GetGridDataDaerah"
PROVINCE_ID = "27"  # Sulawesi Tenggara

PRICE_TYPES = [
    {"id": 1, "name": "Pasar Tradisional"},
    {"id": 2, "name": "Pasar Modern"},
    {"id": 3, "name": "Pedagang Besar"},
    {"id": 4, "name": "Produsen"},
]

CITIES = [
    {"id": "", "name": "Provinsi Sulawesi Tenggara (Rata-rata)"},
    {"id": 72, "name": "Kota Kendari"},
    {"id": 73, "name": "Kota Bau-Bau"},
]

MAIN_CATEGORIES = [
    {"id": "cat_1", "name": "Beras", "icon": "🌾", "cuaca_sensitif": "Kekeringan / Banjir Sawah"},
    {"id": "cat_2", "name": "Daging Ayam", "icon": "🍗", "cuaca_sensitif": "Suhu Ekstrem (Kematian Ternak)"},
    {"id": "cat_3", "name": "Daging Sapi", "icon": "🥩", "cuaca_sensitif": "Rendah (Pakan Hijauan)"},
    {"id": "cat_4", "name": "Telur Ayam", "icon": "🥚", "cuaca_sensitif": "Suhu Tinggi (Produktivitas Bertelur)"},
    {"id": "cat_5", "name": "Bawang Merah", "icon": "🧅", "cuaca_sensitif": "Sangat Rentan Hujan (Busuk Batang/Umbi)"},
    {"id": "cat_6", "name": "Bawang Putih", "icon": "🧄", "cuaca_sensitif": "Logistik Laut (Pasokan Luar Daerah)"},
    {"id": "cat_7", "name": "Cabai Merah", "icon": "🌶️", "cuaca_sensitif": "Sangat Rentan Hujan Lebat (Antraknosa/Patek)"},
    {"id": "cat_8", "name": "Cabai Rawit", "icon": "🔥", "cuaca_sensitif": "Sangat Rentan Hujan Ekstrem (Rontok Bunga)"},
    {"id": "cat_9", "name": "Minyak Goreng", "icon": "🍾", "cuaca_sensitif": "Logistik Maritim Antarpulau"},
    {"id": "cat_10", "name": "Gula Pasir", "icon": "🍬", "cuaca_sensitif": "Logistik Maritim Antarpulau"}
]

DETAIL_COMMODITIES = [
    {"id": "com_1", "name": "Beras Kualitas Bawah I", "parent": "Beras", "icon": "🌾", "cuaca_sensitif": "Kekeringan / Banjir Sawah"},
    {"id": "com_2", "name": "Beras Kualitas Bawah II", "parent": "Beras", "icon": "🌾", "cuaca_sensitif": "Kekeringan / Banjir Sawah"},
    {"id": "com_3", "name": "Beras Kualitas Medium I", "parent": "Beras", "icon": "🌾", "cuaca_sensitif": "Kekeringan / Banjir Sawah"},
    {"id": "com_4", "name": "Beras Kualitas Medium II", "parent": "Beras", "icon": "🌾", "cuaca_sensitif": "Kekeringan / Banjir Sawah"},
    {"id": "com_5", "name": "Beras Kualitas Super I", "parent": "Beras", "icon": "🌾", "cuaca_sensitif": "Kekeringan / Banjir Sawah"},
    {"id": "com_6", "name": "Beras Kualitas Super II", "parent": "Beras", "icon": "🌾", "cuaca_sensitif": "Kekeringan / Banjir Sawah"},
    {"id": "com_7", "name": "Daging Ayam Ras Segar", "parent": "Daging Ayam", "icon": "🍗", "cuaca_sensitif": "Suhu Ekstrem"},
    {"id": "com_8", "name": "Daging Sapi Kualitas 1", "parent": "Daging Sapi", "icon": "🥩", "cuaca_sensitif": "Rendah"},
    {"id": "com_9", "name": "Daging Sapi Kualitas 2", "parent": "Daging Sapi", "icon": "🥩", "cuaca_sensitif": "Rendah"},
    {"id": "com_10", "name": "Telur Ayam Ras Segar", "parent": "Telur Ayam", "icon": "🥚", "cuaca_sensitif": "Suhu Tinggi"},
    {"id": "com_11", "name": "Bawang Merah Ukuran Sedang", "parent": "Bawang Merah", "icon": "🧅", "cuaca_sensitif": "Sangat Rentan Hujan"},
    {"id": "com_12", "name": "Bawang Putih Ukuran Sedang", "parent": "Bawang Putih", "icon": "🧄", "cuaca_sensitif": "Logistik Laut"},
    {"id": "com_13", "name": "Cabai Merah Besar", "parent": "Cabai Merah", "icon": "🌶️", "cuaca_sensitif": "Sangat Rentan Hujan"},
    {"id": "com_14", "name": "Cabai Merah Keriting", "parent": "Cabai Merah", "icon": "🌶️", "cuaca_sensitif": "Sangat Rentan Hujan"},
    {"id": "com_15", "name": "Cabai Rawit Hijau", "parent": "Cabai Rawit", "icon": "🫑", "cuaca_sensitif": "Rentan Hujan & Jamur"},
    {"id": "com_16", "name": "Cabai Rawit Merah", "parent": "Cabai Rawit", "icon": "🔥", "cuaca_sensitif": "Sangat Rentan Hujan"},
    {"id": "com_17", "name": "Minyak Goreng Curah", "parent": "Minyak Goreng", "icon": "🛢️", "cuaca_sensitif": "Logistik Maritim"},
    {"id": "com_18", "name": "Minyak Goreng Kemasan Bermerk 1", "parent": "Minyak Goreng", "icon": "🍾", "cuaca_sensitif": "Logistik Maritim"},
    {"id": "com_19", "name": "Minyak Goreng Kemasan Bermerk 2", "parent": "Minyak Goreng", "icon": "🍾", "cuaca_sensitif": "Logistik Maritim"},
    {"id": "com_20", "name": "Gula Pasir Kualitas Premium", "parent": "Gula Pasir", "icon": "🍬", "cuaca_sensitif": "Logistik Maritim"},
    {"id": "com_21", "name": "Gula Pasir Lokal", "parent": "Gula Pasir", "icon": "🧂", "cuaca_sensitif": "Logistik Maritim"}
]

MONTH_NAMES_ID = {
    "01": "Jan", "02": "Feb", "03": "Mar", "04": "Apr",
    "05": "Mei", "06": "Jun", "07": "Jul", "08": "Agu",
    "09": "Sep", "10": "Okt", "11": "Nov", "12": "Des"
}

HEADERS = {
    "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
    "Accept": "application/json, text/javascript, */*; q=0.01",
    "X-Requested-With": "XMLHttpRequest",
    "Referer": "https://www.bi.go.id/hargapangan/home/index"
}

def format_date_key_to_month_label(date_str):
    try:
        parts = date_str.split("/")
        if len(parts) == 3:
            day, month, year = parts
            return f"{MONTH_NAMES_ID.get(month, month)} {year}"
    except Exception:
        pass
    return date_str

def parse_price_value(val):
    if val is None:
        return None
    val_str = str(val).strip()
    if not val_str or val_str == "-" or val_str.lower() == "null":
        return None
    clean_num = val_str.replace(",", "").replace(".", "").replace("Rp", "").strip()
    try:
        return int(clean_num)
    except ValueError:
        try:
            return float(clean_num)
        except ValueError:
            return None

def fetch_grid_data(price_type_id, regency_id, tipe_laporan, start_date, end_date, max_retries=3):
    params = {
        "price_type_id": price_type_id,
        "comcat_id": "",
        "province_id": PROVINCE_ID,
        "regency_id": str(regency_id) if regency_id != "" else "",
        "market_id": "",
        "tipe_laporan": tipe_laporan,
        "start_date": start_date,
        "end_date": end_date
    }
    url = f"{BASE_URL}?{urllib.parse.urlencode(params)}"
    for attempt in range(1, max_retries + 1):
        try:
            req = urllib.request.Request(url, headers=HEADERS)
            with urllib.request.urlopen(req, timeout=30) as resp:
                if resp.status == 200:
                    raw_data = resp.read().decode("utf-8")
                    return json.loads(raw_data)
        except Exception as e:
            if attempt < max_retries:
                time.sleep(1.5 * attempt)
            else:
                print(f"  [Gagal] {url} : {e}")
                return None
    return None

def sync_pihps_data():
    print("=" * 85)
    print("MEMULAI SCRAPING LIVE PIHPS RESMI BANK INDONESIA (PROVINSI SULAWESI TENGGARA)")
    print(f"Sumber: {BASE_URL}")
    print(f"Waktu Eksekusi: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print("=" * 85)

    # 1. Baca master dataset yang sudah ada untuk mempertahankan deret historis bulanan 2024-2026
    master_path = os.path.join(DATA_DIR, "pihps_sultra_all.json")
    existing_records_map = {}
    ordered_date_keys = []
    if os.path.exists(master_path):
        try:
            with open(master_path, "r", encoding="utf-8") as f:
                old_master = json.load(f)
            ordered_date_keys = old_master.get("metadata", {}).get("daftar_tanggal", [])
            for r in old_master.get("data", []):
                key = (r.get("kategori_id"), str(r.get("kota_id")), r.get("komoditas"))
                existing_records_map[key] = r
        except Exception as e:
            print(f"[WARN] Tidak dapat membaca old master: {e}")

    # Fallback daftar tanggal bulanan jika kosong
    if not ordered_date_keys:
        ordered_date_keys = [
            '01/01/2024', '01/02/2024', '01/03/2024', '01/04/2024', '01/05/2024', '03/06/2024',
            '01/07/2024', '01/08/2024', '02/09/2024', '01/10/2024', '01/11/2024', '02/12/2024',
            '01/01/2025', '03/02/2025', '03/03/2025', '01/04/2025', '01/05/2025', '02/06/2025',
            '01/07/2025', '01/08/2025', '01/09/2025', '01/10/2025', '03/11/2025', '01/12/2025',
            '01/01/2026', '02/02/2026', '02/03/2026', '01/04/2026', '01/05/2026', '01/06/2026',
            '01/07/2026', '03/08/2026', '01/09/2026', '01/10/2026'
        ]

    today = datetime.now()
    curr_month_key = today.strftime("01/%m/%Y")
    month_label = format_date_key_to_month_label(curr_month_key)
    if curr_month_key not in ordered_date_keys:
        ordered_date_keys.append(curr_month_key)

    # 2. Query data harian Oktober s.d. Terkini (November 2026) ke website Bank Indonesia
    start_date_daily = "2026-10-01"
    end_date_daily = today.strftime("%Y-%m-%d")

    all_records = []
    daily_dates_set = set()
    latest_published_date = None

    # Simpan hasil scraping pasar tradisional sultra untuk lookup harian
    tradisional_sultra_daily = {}

    for pt in PRICE_TYPES:
        pt_id = pt["id"]
        pt_name = pt["name"]

        for city in CITIES:
            city_id = city["id"]
            city_name = city["name"]
            city_key_str = str(city_id)

            print(f"-> Scraping [{pt_name}] - [{city_name}] (Harian Oktober)...")
            res_d = fetch_grid_data(pt_id, city_id, 1, start_date_daily, end_date_daily)
            rows_d = res_d.get("data", []) if res_d and isinstance(res_d, dict) else []

            # Temukan tanggal-tanggal harian yang ada di response
            grid_dates = []
            if rows_d:
                sample_row = rows_d[0]
                grid_dates = [k for k in sample_row.keys() if "/" in k and k not in ("no", "name", "level", "id", "cat_id")]
                grid_dates.sort(key=lambda d: [int(x) for x in reversed(d.split("/"))])

            # Pilah baris level 1 dan level 2
            lvl1_by_name = {}
            lvl2_by_name = {}
            for r in rows_d:
                name_clean = r.get("name", "").strip()
                lvl = r.get("level")
                if lvl == 1:
                    lvl1_by_name[name_clean] = r
                elif lvl == 2:
                    lvl2_by_name[name_clean] = r

            # Cek tanggal mana saja yang memiliki setidaknya satu harga rilis resmi (bukan '-')
            valid_dates_in_grid = []
            for d in grid_dates:
                has_any_price = False
                for r in rows_d:
                    if parse_price_value(r.get(d)) is not None:
                        has_any_price = True
                        break
                if has_any_price:
                    valid_dates_in_grid.append(d)
                    if pt_id == 1:
                        daily_dates_set.add(d)

            # 2.1 Proses 10 Komoditas Utama (Level 1)
            for cat in MAIN_CATEGORIES:
                cname = cat["name"]
                row_d = lvl1_by_name.get(cname)
                if not row_d:
                    # Match case-insensitive
                    for k, v in lvl1_by_name.items():
                        if k.lower() == cname.lower():
                            row_d = v
                            break

                daily_dict = {}
                latest_p = None
                if row_d:
                    for d in valid_dates_in_grid:
                        p_val = parse_price_value(row_d.get(d))
                        daily_dict[d] = p_val
                        if p_val is not None:
                            latest_p = p_val
                
                # Cek existing record untuk preserve riwayat bulanan
                ex_rec = existing_records_map.get((pt_id, city_key_str, cname), {})
                harga_per_tgl = dict(ex_rec.get("harga_per_tanggal", {}))

                # Update harga bulan Oktober 2026 dengan harga harian terbaru rilis BI
                if latest_p is not None:
                    harga_per_tgl[curr_month_key] = {
                        "label_bulan": month_label,
                        "harga_rp": latest_p,
                        "raw": f"{latest_p:,}"
                    }

                rec = {
                    "kategori": pt_name,
                    "kategori_id": pt_id,
                    "kota": city_name,
                    "kota_id": city_id,
                    "komoditas": cname,
                    "level": 1,
                    "icon": cat["icon"],
                    "cuaca_sensitif": cat["cuaca_sensitif"],
                    "tersedia": (row_d is not None) or ex_rec.get("tersedia", False),
                    "harga_per_tanggal": harga_per_tgl,
                    "harga_harian_terkini": daily_dict
                }
                all_records.append(rec)

                # Simpan untuk pasar tradisional provinsi
                if pt_id == 1 and city_id == "":
                    tradisional_sultra_daily[cname] = daily_dict

            # 2.2 Proses 21 Varian Rinci (Level 2)
            for comm in DETAIL_COMMODITIES:
                cname = comm["name"]
                row_d = lvl2_by_name.get(cname)
                if not row_d:
                    for k, v in lvl2_by_name.items():
                        if k.lower() == cname.lower():
                            row_d = v
                            break

                daily_dict = {}
                latest_p = None
                if row_d:
                    for d in valid_dates_in_grid:
                        p_val = parse_price_value(row_d.get(d))
                        daily_dict[d] = p_val
                        if p_val is not None:
                            latest_p = p_val

                ex_rec = existing_records_map.get((pt_id, city_key_str, cname), {})
                harga_per_tgl = dict(ex_rec.get("harga_per_tanggal", {}))

                if latest_p is not None:
                    harga_per_tgl[curr_month_key] = {
                        "label_bulan": month_label,
                        "harga_rp": latest_p,
                        "raw": f"{latest_p:,}"
                    }

                rec = {
                    "kategori": pt_name,
                    "kategori_id": pt_id,
                    "kota": city_name,
                    "kota_id": city_id,
                    "komoditas": cname,
                    "level": 2,
                    "parent": comm["parent"],
                    "icon": comm["icon"],
                    "cuaca_sensitif": comm["cuaca_sensitif"],
                    "tersedia": (row_d is not None) or ex_rec.get("tersedia", False),
                    "harga_per_tanggal": harga_per_tgl,
                    "harga_harian_terkini": daily_dict
                }
                all_records.append(rec)

                if pt_id == 1 and city_id == "":
                    tradisional_sultra_daily[cname] = daily_dict

            time.sleep(0.4)

    now = datetime.now()
    if now.weekday() == 5:
        def_target_dt = now - timedelta(days=1)
    elif now.weekday() == 6:
        def_target_dt = now - timedelta(days=2)
    else:
        def_target_dt = now
    def_target_str = def_target_dt.strftime("%d/%m/%Y")

    # Urutkan tanggal harian Oktober yang berhasil dirilis BI
    sorted_daily_dates = sorted(list(daily_dates_set), key=lambda d: [int(x) for x in reversed(d.split("/"))])
    if sorted_daily_dates:
        latest_published_date = sorted_daily_dates[-1]
    else:
        print("[WARN] Tidak ada tanggal survei rilis resmi yang didapat dari live API. Menggunakan tanggal terakhir yang sah.")
        if os.path.exists(master_path):
            with open(master_path, "r", encoding="utf-8") as f:
                old_m = json.load(f)
            existing_oct_dates = [d for d in old_m.get("metadata", {}).get("daftar_tanggal_harian_oktober", [])]
            if existing_oct_dates:
                latest_published_date = existing_oct_dates[-1]
                sorted_daily_dates = existing_oct_dates
            else:
                latest_published_date = "15/10/2026"
                sorted_daily_dates = ["01/10/2026", "02/10/2026", "05/10/2026", "06/10/2026", "07/10/2026", "08/10/2026", "09/10/2026", "12/10/2026", "13/10/2026", "14/10/2026", "15/10/2026"]
        else:
            latest_published_date = "14/10/2026"
            sorted_daily_dates = ["01/10/2026", "02/10/2026", "05/10/2026", "06/10/2026", "07/10/2026", "08/10/2026", "09/10/2026", "12/10/2026", "13/10/2026", "14/10/2026"]

    # Filter agar seluruh record hanya menyajikan tanggal survei yang telah resmi dirilis
    for rec in all_records:
        h = rec.get("harga_harian_terkini", {})
        for d in list(h.keys()):
            if ("/10/2026" in d or "/11/2026" in d) and d not in sorted_daily_dates:
                del h[d]

    print("\n" + "=" * 85)
    print(f"HASIL SCRAPING: Total Record: {len(all_records)}")
    print(f"Tanggal Rilis Harian BI Terkini: {latest_published_date}")
    print(f"Daftar Tanggal Harian Rilis BI: {sorted_daily_dates}")
    print("=" * 85)

    # Validasi sanity check: Cabai Rawit & Cabai Merah Pasar Tradisional Sultra
    cr_sultra = tradisional_sultra_daily.get("Cabai Rawit", {})
    cm_sultra = tradisional_sultra_daily.get("Cabai Merah", {})
    da_sultra = tradisional_sultra_daily.get("Daging Ayam", {})
    print(f"\n[SANITY CHECK HARGA PASAR TRADISIONAL SULTRA]")
    print(f"  Cabai Rawit : {cr_sultra.get('30/10/2026')} (30 Okt) | {cr_sultra.get('02/11/2026')} (02 Nov)")
    print(f"  Cabai Merah : {cm_sultra.get('30/10/2026')} (30 Okt) | {cm_sultra.get('02/11/2026')} (02 Nov)")
    print(f"  Daging Ayam : {da_sultra.get('30/10/2026')} (30 Okt) | {da_sultra.get('02/11/2026')} (02 Nov)")

    # 3. Simpan pihps_sultra_all.json
    now_dt = datetime.now()
    bulan_indo = ["Januari", "Februari", "Maret", "April", "Mei", "Juni", "Juli", "Agustus", "September", "Oktober", "November", "Desember"]
    waktu_pembaruan_id = f"{now_dt.day} {bulan_indo[now_dt.month - 1]} {now_dt.year}, {now_dt.strftime('%H:%M')} WITA"
    try:
        p_day, p_mon, p_yr = latest_published_date.split("/")
        tanggal_rilis_bi_id = f"{int(p_day)} {bulan_indo[int(p_mon) - 1]} {p_yr}"
    except Exception:
        tanggal_rilis_bi_id = latest_published_date

    master_payload = {
        "metadata": {
            "sumber": "Pusat Informasi Harga Pangan Strategis (PIHPS) Nasional - Bank Indonesia",
            "tautan": "https://www.bi.go.id/hargapangan/home/index",
            "wilayah": "Provinsi Sulawesi Tenggara",
            "wilayah_detail": [c["name"] for c in CITIES],
            "periode_mulai": "2024-01-01",
            "periode_selesai": end_date_daily,
            "tanggal_terkini_bi": latest_published_date,
            "tanggal_rilis_bi_id": tanggal_rilis_bi_id,
            "waktu_pembaruan_id": waktu_pembaruan_id,
            "daftar_tanggal_harian_oktober": [d for d in sorted_daily_dates if "/10/2026" in d],
            "daftar_tanggal_harian_terkini": sorted_daily_dates,
            "total_records": len(all_records),
            "total_komoditas_utama": len(MAIN_CATEGORIES),
            "total_varian_detail": len(DETAIL_COMMODITIES),
            "daftar_tanggal": ordered_date_keys,
            "waktu_ekstraksi": now_dt.isoformat()
        },
        "data": all_records
    }
    with open(master_path, "w", encoding="utf-8") as f:
        json.dump(master_payload, f, indent=2, ensure_ascii=False)
    backup_path = master_path + ".backup"
    shutil.copy(master_path, backup_path)
    print(f"[OK] Master tersimpan: {master_path}")

    # 4. Perbarui data/pihps_daily_lookup.json
    lookup_path = os.path.join(DATA_DIR, "pihps_daily_lookup.json")
    daily_lookup = {}
    if os.path.exists(lookup_path):
        try:
            with open(lookup_path, "r", encoding="utf-8") as f:
                daily_lookup = json.load(f)
        except Exception:
            daily_lookup = {}

    for cname, dates_dict in tradisional_sultra_daily.items():
        if cname not in daily_lookup:
            daily_lookup[cname] = {}
        for d, p_val in dates_dict.items():
            if p_val is not None:
                daily_lookup[cname][d] = p_val

    # Bersihkan tanggal yang belum dirilis resmi
    for cname in list(daily_lookup.keys()):
        for d in list(daily_lookup[cname].keys()):
            if ("/10/2026" in d or "/11/2026" in d) and d not in sorted_daily_dates:
                del daily_lookup[cname][d]

    with open(lookup_path, "w", encoding="utf-8") as f:
        json.dump(daily_lookup, f, indent=2, ensure_ascii=False)
    print(f"[OK] pihps_daily_lookup.json tersimpan: {lookup_path}")

    # 5. Perbarui bi_daily_jul_oct_2026.json
    jul_oct_path = os.path.join(DATA_DIR, "bi_daily_jul_oct_2026.json")
    if os.path.exists(jul_oct_path):
        with open(jul_oct_path, "r", encoding="utf-8") as f:
            jul_oct_data = json.load(f)
        
        for row in jul_oct_data.get("data", []):
            rname = row.get("name", "").strip()
            if rname in tradisional_sultra_daily:
                for d, p_val in tradisional_sultra_daily[rname].items():
                    if p_val is not None:
                        row[d] = f"{int(p_val):,}"

            # Bersihkan tanggal belum rilis
            for d in list(row.keys()):
                if ("/10/2026" in d or "/11/2026" in d) and d not in sorted_daily_dates and d not in ("no", "name", "level", "id", "cat_id"):
                    del row[d]

        with open(jul_oct_path, "w", encoding="utf-8") as f:
            json.dump(jul_oct_data, f, indent=2, ensure_ascii=False)
        print(f"[OK] bi_daily_jul_oct_2026.json tersimpan: {jul_oct_path}")

    # 6. Rebuild bi_daily_2024_2026.json jika skrip builder tersedia
    builder_script = os.path.join(BASE_DIR, "scraper", "build_daily_2024_2026.py")
    if os.path.exists(builder_script):
        try:
            import importlib.util
            spec = importlib.util.spec_from_file_location("build_daily", builder_script)
            build_mod = importlib.util.module_from_spec(spec)
            spec.loader.exec_module(build_mod)
            if hasattr(build_mod, "build_daily_dataset"):
                build_mod.build_daily_dataset()
                print(f"[OK] bi_daily_2024_2026.json direkompilasi.")
        except Exception as e:
            print(f"[WARN] Error menjalankan build_daily_dataset: {e}")

    # 7. Perbarui ringkasan mingguan bi_pihps_weekly.json
    from scraper.pihps_scraper import update_weekly_json
    update_weekly_json(all_records, latest_published_date, output_dir=DATA_DIR)

    # 8. Perbarui daily_realization_tracking.json dengan realisasi rilis resmi BI
    realization_path = os.path.join(DATA_DIR, "daily_realization_tracking.json")
    if os.path.exists(realization_path):
        try:
            with open(realization_path, "r", encoding="utf-8") as f:
                real_data = json.load(f)
            
            for cname, c_obj in real_data.items():
                if cname in tradisional_sultra_daily:
                    c_daily = tradisional_sultra_daily[cname]
                    for track_row in c_obj.get("tracking", []):
                        t_date = track_row.get("tanggal")
                        if t_date in c_daily and c_daily[t_date] is not None:
                            track_row["realisasi_pihps"] = float(c_daily[t_date])
                        elif t_date not in sorted_daily_dates:
                            track_row["realisasi_pihps"] = None

            with open(realization_path, "w", encoding="utf-8") as f:
                json.dump(real_data, f, indent=2, ensure_ascii=False)
            print(f"[OK] daily_realization_tracking.json realisasi diperbarui.")
        except Exception as e:
            print(f"[WARN] Error updating realization: {e}")

    # 9. Sinkronkan data harian Pasar Tradisional Level 1 ke pihps_daily_cities_2024_2026.json
    daily_cities_path = os.path.join(DATA_DIR, "pihps_daily_cities_2024_2026.json")
    if os.path.exists(daily_cities_path):
        try:
            with open(daily_cities_path, "r", encoding="utf-8") as f:
                dc_payload = json.load(f)
            dc_map = dc_payload.get("data_harian", {})
            for rec in all_records:
                if rec.get("kategori_id") == 1 and rec.get("level") == 1:
                    kname = rec.get("kota")
                    cname = rec.get("komoditas")
                    if kname in dc_map and cname in dc_map[kname]:
                        for d, p_val in rec.get("harga_harian_terkini", {}).items():
                            if p_val is not None and float(p_val) > 0:
                                dc_map[kname][cname][d] = int(round(float(p_val)))
                        sorted_keys = sorted(
                            dc_map[kname][cname].keys(),
                            key=lambda d: [int(x) for x in reversed(d.split("/"))] if "/" in d else [0, 0, 0],
                        )
                        dc_map[kname][cname] = {dk: dc_map[kname][cname][dk] for dk in sorted_keys}
            if "metadata" in dc_payload:
                dc_payload["metadata"]["periode_selesai"] = latest_published_date
                dc_payload["metadata"]["waktu_ekstraksi"] = now_dt.isoformat()
            with open(daily_cities_path, "w", encoding="utf-8") as f:
                json.dump(dc_payload, f, ensure_ascii=False, separators=(",", ":"))
            print(f"[OK] pihps_daily_cities_2024_2026.json diperbarui hingga {latest_published_date}.")
        except Exception as e:
            print(f"[WARN] Error updating pihps_daily_cities_2024_2026.json: {e}")

    print("\n[SUKSES] Seluruh dataset PIHPS Bank Indonesia berhasil dimutakhirkan dengan data scraping resmi.")
    return {
        "status": "success",
        "tanggal_terkini": latest_published_date,
        "daftar_tanggal": sorted_daily_dates,
        "total_records": len(all_records)
    }

if __name__ == "__main__":
    sync_pihps_data()
