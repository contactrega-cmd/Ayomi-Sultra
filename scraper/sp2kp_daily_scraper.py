"""
SP2KP Daily Scraper for 17 Kabupaten/Kota in Sulawesi Tenggara
Mengambil rekaman harga harian 10 komoditas strategis dari SP2KP Kemendag RI (2024 - 2026).
"""

import os
import json
import ssl
import time
from datetime import datetime
import urllib.request
from concurrent.futures import ThreadPoolExecutor

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DATA_DIR = os.path.join(BASE_DIR, "data")
os.makedirs(DATA_DIR, exist_ok=True)
OUT_FILE = os.path.join(DATA_DIR, "sp2kp_daily_sultra.json")

SP2KP_API_URL = "https://api-sp2kp.kemendag.go.id/report/api/average-price/export-variant-daily-json"

# Konfigurasi 10 Komoditas Pangan Strategis Sesuai Penyetaraan PIHPS - SP2KP
COMMODITY_CONFIG = [
    {
        "pihps_name": "Beras",
        "primary_id": 51,    # Beras Premium
        "fallback_id": 52,   # Beras Medium
        "icon": "🌾",
        "satuan": "kg"
    },
    {
        "pihps_name": "Daging Ayam",
        "primary_id": 27,    # Daging Ayam Ras
        "fallback_id": 43,   # Daging Ayam Kampung
        "icon": "🍗",
        "satuan": "kg"
    },
    {
        "pihps_name": "Daging Sapi",
        "primary_id": 19,    # Daging Sapi Paha Belakang
        "fallback_id": 53,   # Daging Sapi Paha Depan
        "icon": "🥩",
        "satuan": "kg"
    },
    {
        "pihps_name": "Telur Ayam",
        "primary_id": 25,    # Telur Ayam Ras
        "fallback_id": None,
        "icon": "🥚",
        "satuan": "kg"
    },
    {
        "pihps_name": "Bawang Merah",
        "primary_id": 13,    # Bawang Merah
        "fallback_id": None,
        "icon": "🧅",
        "satuan": "kg"
    },
    {
        "pihps_name": "Bawang Putih",
        "primary_id": 38,    # Bawang Putih Honan
        "fallback_id": 39,   # Bawang Putih Kating
        "icon": "🧄",
        "satuan": "kg"
    },
    {
        "pihps_name": "Cabai Merah",
        "primary_id": 2,     # Cabai Merah Keriting
        "fallback_id": 9,    # Cabai Merah Besar
        "icon": "🌶️",
        "satuan": "kg"
    },
    {
        "pihps_name": "Cabai Rawit",
        "primary_id": 10,    # Cabai Rawit Merah
        "fallback_id": 11,   # Cabai Rawit Hijau
        "icon": "🔥",
        "satuan": "kg"
    },
    {
        "pihps_name": "Minyak Goreng",
        "primary_id": 18,    # Minyakita
        "fallback_id": 16,   # Minyak Sawit Curah
        "icon": "🍾",
        "satuan": "liter"
    },
    {
        "pihps_name": "Gula Pasir",
        "primary_id": 14,    # Gula Pasir Curah
        "fallback_id": 15,   # Gula Pasir Kemasan
        "icon": "🍬",
        "satuan": "kg"
    }
]

# Daftar 17 Kabupaten/Kota Se-Sultra
KAB_KOTA_LIST = [
    "Kab. Kolaka",
    "Kab. Konawe",
    "Kab. Muna",
    "Kab. Buton",
    "Kab. Konawe Selatan",
    "Kab. Bombana",
    "Kab. Wakatobi",
    "Kab. Kolaka Utara",
    "Kab. Konawe Utara",
    "Kab. Buton Utara",
    "Kab. Kolaka Timur",
    "Kab. Konawe Kepulauan",
    "Kab. Muna Barat",
    "Kab. Buton Tengah",
    "Kab. Buton Selatan",
    "Kota Kendari",
    "Kota Bau-Bau"
]

def clean_kab_name(raw_name):
    """Standarisasi nama Kabupaten/Kota agar seragam dengan dashboard."""
    if not raw_name:
        return ""
    rn = raw_name.strip()
    # Normalize common naming patterns
    if rn.lower() == "kendari" or rn.lower() == "kota kendari":
        return "Kota Kendari"
    if rn.lower() == "baubau" or rn.lower() == "bau-bau" or rn.lower() == "kota bau-bau" or rn.lower() == "kota baubau":
        return "Kota Bau-Bau"
    if not rn.startswith("Kab.") and not rn.startswith("Kota "):
        return f"Kab. {rn}"
    return rn

def fetch_variant_data(vid, start_date="2024-01-01", end_date=None, max_retries=3):
    """Mengambil data time series harian dari SP2KP untuk 1 variant_id dengan retry."""
    if not vid:
        return []
    
    if not end_date:
        end_date = datetime.now().strftime("%Y-%m-%d")
    
    ctx = ssl.create_default_context()
    ctx.check_hostname = False
    ctx.verify_mode = ssl.CERT_NONE

    for attempt in range(1, max_retries + 1):
        try:
            boundary = f"----WebKitBoundarySP2KP_{vid}_{int(time.time()*1000)}"
            fields = [
                ("start_date", start_date),
                ("end_date", end_date),
                ("level", "2"),
                ("variant_id", str(vid)),
                ("kode_provinsi", "74"),
                ("kode_kab_kota", ""),
                ("skip_sat_sun", "true"),
                ("tipe_komoditas", "")
            ]
            body = b""
            for k, v in fields:
                body += f"--{boundary}\r\nContent-Disposition: form-data; name=\"{k}\"\r\n\r\n{v}\r\n".encode("utf-8")
            body += f"--{boundary}--\r\n".encode("utf-8")

            req = urllib.request.Request(
                SP2KP_API_URL,
                data=body,
                headers={
                    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
                    "Content-Type": f"multipart/form-data; boundary={boundary}"
                }
            )

            with urllib.request.urlopen(req, context=ctx, timeout=45) as r:
                res = json.loads(r.read().decode("utf-8"))
                data = res.get("data") or []
                if data:
                    return data
                elif attempt < max_retries:
                    time.sleep(1.5 * attempt)
        except Exception as e:
            if attempt < max_retries:
                time.sleep(2 * attempt)
            else:
                print(f"Error fetching variant {vid} (attempt {attempt}): {e}")
    return []

def iso_to_id_date(iso_str):
    """Mengubah '2026-10-15' menjadi '15/10/2026'."""
    try:
        parts = iso_str.split("-")
        return f"{parts[2]}/{parts[1]}/{parts[0]}"
    except Exception:
        return iso_str

def run_scraper(start_date="2026-10-01", end_date=None):
    if not end_date:
        end_date = datetime.now().strftime("%Y-%m-%d")
    print(f"Memulai scraping SP2KP Sulawesi Tenggara ({start_date} s.d. {end_date})...")
    t0 = time.time()

    # Kumpulkan seluruh ID varian yang diperlukan (primary + fallback)
    variant_ids_to_fetch = set()
    for cfg in COMMODITY_CONFIG:
        variant_ids_to_fetch.add(cfg["primary_id"])
        if cfg["fallback_id"]:
            variant_ids_to_fetch.add(cfg["fallback_id"])

    print(f"Total varian unik yang akan ditarik: {len(variant_ids_to_fetch)}")

    # Tarik data secara paralel (max_workers=4 untuk stabilitas koneksi)
    raw_results = {}
    with ThreadPoolExecutor(max_workers=4) as executor:
        futures = {executor.submit(fetch_variant_data, vid, start_date, end_date): vid for vid in variant_ids_to_fetch}
        for future in futures:
            vid = futures[future]
            try:
                data = future.result()
                raw_results[vid] = data
                print(f"  ✓ Selesai varian ID {vid:2d}: {len(data)} wilayah tercakup")
            except Exception as exc:
                print(f"  ✗ Gagal varian ID {vid:2d}: {exc}")
                raw_results[vid] = []

    # Coba ulang sekuensial jika ada varian yang gagal/kosong
    for vid in sorted(variant_ids_to_fetch):
        if not raw_results.get(vid):
            print(f"  -> Mencoba ulang varian ID {vid:2d} secara sekuensial...")
            time.sleep(1.5)
            retried = fetch_variant_data(vid, start_date, end_date, max_retries=3)
            raw_results[vid] = retried
            print(f"  ✓ Selesai coba ulang varian ID {vid:2d}: {len(retried)} wilayah tercakup")

    # Susun struktur SP2KP Daily Lookup per Wilayah -> Komoditas -> Tanggal (DD/MM/YYYY)
    # Muat data eksisting terlebih dahulu agar riwayat data historis tetap terjaga utuh
    existing_data = {}
    if os.path.exists(OUT_FILE):
        try:
            with open(OUT_FILE, "r", encoding="utf-8") as f:
                existing_data = json.load(f).get("data_harian", {})
        except Exception as e:
            print(f"Pemberitahuan memuat data eksisting: {e}")

    sp2kp_lookup = {}
    for kab in KAB_KOTA_LIST:
        sp2kp_lookup[kab] = {}
        for cfg in COMMODITY_CONFIG:
            cn = cfg["pihps_name"]
            sp2kp_lookup[kab][cn] = {}
            if kab in existing_data and cn in existing_data[kab]:
                sp2kp_lookup[kab][cn] = dict(existing_data[kab][cn])

    # Helper untuk memetakan raw API records
    # raw_map[vid][clean_kab] = { iso_date: price }
    raw_map = {}
    for vid, w_list in raw_results.items():
        raw_map[vid] = {}
        for w in w_list:
            c_kab = clean_kab_name(w.get("wilayah", ""))
            raw_map[vid][c_kab] = {}
            for item in w.get("daftarHarga", []):
                d_iso = item.get("date")
                h_val = item.get("harga", 0)
                if d_iso:
                    raw_map[vid][c_kab][d_iso] = h_val

    # Gabungkan primary dan fallback
    for cfg in COMMODITY_CONFIG:
        c_name = cfg["pihps_name"]
        p_id = cfg["primary_id"]
        f_id = cfg["fallback_id"]

        for kab in KAB_KOTA_LIST:
            p_data = raw_map.get(p_id, {}).get(kab, {})
            f_data = raw_map.get(f_id, {}).get(kab, {}) if f_id else {}

            all_dates = set(p_data.keys()).union(set(f_data.keys()))
            for d_iso in sorted(all_dates):
                d_id = iso_to_id_date(d_iso)
                val = p_data.get(d_iso, 0)
                if (val is None or val == 0) and f_data:
                    val = f_data.get(d_iso, 0)
                
                if val and val > 0:
                    sp2kp_lookup[kab][c_name][d_id] = int(val)

    # Tambahkan Rata-rata Provinsi untuk SP2KP (bisa digunakan jika diperlukan)
    prov_name = "Provinsi Sulawesi Tenggara (SP2KP)"
    sp2kp_lookup[prov_name] = {}
    for cfg in COMMODITY_CONFIG:
        c_name = cfg["pihps_name"]
        sp2kp_lookup[prov_name][c_name] = {}
        # Kumpulkan semua tanggal dari 17 kab
        date_pools = {}
        for kab in KAB_KOTA_LIST:
            for d_id, pr in sp2kp_lookup[kab][c_name].items():
                if pr > 0:
                    if d_id not in date_pools:
                        date_pools[d_id] = []
                    date_pools[d_id].append(pr)
        for d_id, p_list in date_pools.items():
            if p_list:
                sp2kp_lookup[prov_name][c_name][d_id] = int(round(sum(p_list) / len(p_list)))

    # Tentukan tanggal rilis terkini yang benar-benar terisi data dari data_harian
    valid_sp2kp_dates = set()
    for kab in KAB_KOTA_LIST:
        for cfg in COMMODITY_CONFIG:
            cn = cfg["pihps_name"]
            for d_id, pr in sp2kp_lookup.get(kab, {}).get(cn, {}).items():
                if pr and pr > 0:
                    valid_sp2kp_dates.add(d_id)
    if valid_sp2kp_dates:
        latest_id_date = sorted(valid_sp2kp_dates, key=lambda d: [int(x) for x in reversed(d.split("/"))])[-1]
        lp = latest_id_date.split("/")
        actual_latest_iso = f"{lp[2]}-{lp[1]}-{lp[0]}"
    else:
        actual_latest_iso = end_date

    # Buat paket JSON akhir
    bulan_names = ["Januari", "Februari", "Maret", "April", "Mei", "Juni", "Juli", "Agustus", "September", "Oktober", "November", "Desember"]
    e_parts = actual_latest_iso.split("-")
    try:
        tgl_terkini_id = f"{int(e_parts[2])} {bulan_names[int(e_parts[1]) - 1]} {e_parts[0]}"
    except Exception:
        tgl_terkini_id = actual_latest_iso

    final_output = {
        "metadata": {
            "sumber": "Sistem Pemantauan Pasar dan Kebutuhan Pokok (SP2KP) - Kementerian Perdagangan RI",
            "tautan": "https://sp2kp.kemendag.go.id/statistik/tabulasi-harga",
            "provinsi": "Sulawesi Tenggara",
            "kode_provinsi": "74",
            "periode_mulai": "2024-01-01",
            "periode_selesai": actual_latest_iso,
            "tanggal_terkini": actual_latest_iso,
            "tanggal_terkini_id": tgl_terkini_id,
            "waktu_ekstraksi": time.strftime("%Y-%m-%dT%H:%M:%S"),
            "total_wilayah": len(KAB_KOTA_LIST),
            "total_komoditas": len(COMMODITY_CONFIG)
        },
        "kab_kota_list": KAB_KOTA_LIST,
        "komoditas_list": [cfg["pihps_name"] for cfg in COMMODITY_CONFIG],
        "data_harian": sp2kp_lookup
    }

    with open(OUT_FILE, "w", encoding="utf-8") as f:
        json.dump(final_output, f, ensure_ascii=False, indent=2)

    elapsed = time.time() - t0
    print(f"\nBerhasil menyimpan data SP2KP ke {OUT_FILE}!")
    print(f"Total waktu: {elapsed:.2f} detik")
    print(f"Ukuran file: {os.path.getsize(OUT_FILE) / 1024:.1f} KB")

    # Tampilkan sample verifikasi
    print("\n--- SAMPLE VERIFIKASI HARGA 28 OKT 2026 ---")
    sample_kabs = ["Kab. Kolaka", "Kab. Konawe", "Kab. Bombana", "Kab. Muna"]
    target_date = "28/10/2026"
    for k in sample_kabs:
        print(f"\n{k}:")
        for cfg in COMMODITY_CONFIG[:4]:
            cn = cfg["pihps_name"]
            p = sp2kp_lookup.get(k, {}).get(cn, {}).get(target_date, 0)
            print(f"  - {cn:<14}: Rp {p:,}" if p else f"  - {cn:<14}: - (0)")

if __name__ == "__main__":
    run_scraper()
