"""
SP2KP Kementerian Perdagangan RI Scraper for Sulawesi Tenggara
Mengambil data harga harian 10 komoditas strategis untuk seluruh 17 Kabupaten/Kota di Sulawesi Tenggara.
Penyetaraan Komoditas (PIHPS vs SP2KP):
1. Beras -> Beras Premium (ID 51)
2. Daging Ayam -> Daging Ayam Ras (ID 27)
3. Daging Sapi -> Daging Sapi Paha Belakang (ID 19)
4. Telur Ayam -> Telur Ayam Ras (ID 25)
5. Bawang Merah -> Bawang Merah (ID 13)
6. Bawang Putih -> Bawang Putih Honan (ID 38)
7. Cabai Merah -> Cabai Merah Keriting (ID 2)
8. Cabai Rawit -> Cabai Rawit Merah (ID 10)
9. Minyak Goreng -> Minyakita (ID 18)
10. Gula Pasir -> Gula Pasir Curah (ID 14)
"""

import os
import json
import ssl
import urllib.request
from datetime import datetime, timedelta

DATA_DIR = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "data")
os.makedirs(DATA_DIR, exist_ok=True)
OUT_FILE = os.path.join(DATA_DIR, "sp2kp_sultra_all.json")

SP2KP_API_URL = "https://api-sp2kp.kemendag.go.id/report/api/average-price/export-variant-daily-json"

# Penyetaraan Komoditas
COMMODITY_MAPPING = [
    {
        "id": "beras",
        "pihps_name": "Beras",
        "sp2kp_name": "Beras Premium",
        "variant_id": 51,
        "icon": "🌾",
        "satuan": "kg",
        "het_hap": 14900,
        "label_regulasi": "HET Zona 2"
    },
    {
        "id": "daging_ayam",
        "pihps_name": "Daging Ayam",
        "sp2kp_name": "Daging Ayam Ras",
        "variant_id": 27,
        "icon": "🍗",
        "satuan": "kg",
        "het_hap": 36750,
        "label_regulasi": "HAP Konsumen"
    },
    {
        "id": "daging_sapi",
        "pihps_name": "Daging Sapi",
        "sp2kp_name": "Daging Sapi Paha Belakang",
        "variant_id": 19,
        "icon": "🥩",
        "satuan": "kg",
        "het_hap": 140000,
        "label_regulasi": "HAP Konsumen"
    },
    {
        "id": "telur_ayam",
        "pihps_name": "Telur Ayam",
        "sp2kp_name": "Telur Ayam Ras",
        "variant_id": 25,
        "icon": "🥚",
        "satuan": "kg",
        "het_hap": 27000,
        "label_regulasi": "HAP Konsumen"
    },
    {
        "id": "bawang_merah",
        "pihps_name": "Bawang Merah",
        "sp2kp_name": "Bawang Merah",
        "variant_id": 13,
        "icon": "🧅",
        "satuan": "kg",
        "het_hap": 41500,
        "label_regulasi": "HAP Konsumen"
    },
    {
        "id": "bawang_putih",
        "pihps_name": "Bawang Putih",
        "sp2kp_name": "Bawang Putih Honan",
        "variant_id": 38,
        "icon": "🧄",
        "satuan": "kg",
        "het_hap": 36000,
        "label_regulasi": "HAP Acuan"
    },
    {
        "id": "cabai_merah",
        "pihps_name": "Cabai Merah",
        "sp2kp_name": "Cabai Merah Keriting",
        "variant_id": 2,
        "icon": "🌶️",
        "satuan": "kg",
        "het_hap": 55000,
        "label_regulasi": "HAP Konsumen"
    },
    {
        "id": "cabai_rawit",
        "pihps_name": "Cabai Rawit",
        "sp2kp_name": "Cabai Rawit Merah",
        "variant_id": 10,
        "icon": "🔥",
        "satuan": "kg",
        "het_hap": 57000,
        "label_regulasi": "HAP Konsumen"
    },
    {
        "id": "minyak_goreng",
        "pihps_name": "Minyak Goreng",
        "sp2kp_name": "Minyakita",
        "variant_id": 18,
        "icon": "🍾",
        "satuan": "liter",
        "het_hap": 15700,
        "label_regulasi": "HET Kemendag"
    },
    {
        "id": "gula_pasir",
        "pihps_name": "Gula Pasir",
        "sp2kp_name": "Gula Pasir Curah",
        "variant_id": 14,
        "icon": "🍬",
        "satuan": "kg",
        "het_hap": 17500,
        "label_regulasi": "HAP Konsumen"
    }
]

ALL_17_KAB_KOTA_SULTRA = [
    {"kode": "7401", "nama": "Kab. Kolaka", "ibukota": "Kolaka", "tipe": "Kabupaten", "ada_di_pihps": False},
    {"kode": "7402", "nama": "Kab. Konawe", "ibukota": "Unaaha", "tipe": "Kabupaten", "ada_di_pihps": False},
    {"kode": "7403", "nama": "Kab. Muna", "ibukota": "Raha", "tipe": "Kabupaten", "ada_di_pihps": False},
    {"kode": "7404", "nama": "Kab. Buton", "ibukota": "Pasarwajo", "tipe": "Kabupaten", "ada_di_pihps": False},
    {"kode": "7405", "nama": "Kab. Konawe Selatan", "ibukota": "Andoolo", "tipe": "Kabupaten", "ada_di_pihps": False},
    {"kode": "7406", "nama": "Kab. Bombana", "ibukota": "Rumbia", "tipe": "Kabupaten", "ada_di_pihps": False},
    {"kode": "7407", "nama": "Kab. Wakatobi", "ibukota": "Wangi-Wangi", "tipe": "Kabupaten", "ada_di_pihps": False},
    {"kode": "7408", "nama": "Kab. Kolaka Utara", "ibukota": "Lasusua", "tipe": "Kabupaten", "ada_di_pihps": False},
    {"kode": "7409", "nama": "Kab. Konawe Utara", "ibukota": "Wanggudu", "tipe": "Kabupaten", "ada_di_pihps": False},
    {"kode": "7410", "nama": "Kab. Buton Utara", "ibukota": "Buranga", "tipe": "Kabupaten", "ada_di_pihps": False},
    {"kode": "7411", "nama": "Kab. Kolaka Timur", "ibukota": "Tirawuta", "tipe": "Kabupaten", "ada_di_pihps": False},
    {"kode": "7412", "nama": "Kab. Konawe Kepulauan", "ibukota": "Langara", "tipe": "Kabupaten", "ada_di_pihps": False},
    {"kode": "7413", "nama": "Kab. Muna Barat", "ibukota": "Laworo", "tipe": "Kabupaten", "ada_di_pihps": False},
    {"kode": "7414", "nama": "Kab. Buton Tengah", "ibukota": "Labungkari", "tipe": "Kabupaten", "ada_di_pihps": False},
    {"kode": "7415", "nama": "Kab. Buton Selatan", "ibukota": "Batauga", "tipe": "Kabupaten", "ada_di_pihps": False},
    {"kode": "7471", "nama": "Kota Kendari", "ibukota": "Kendari", "tipe": "Kota", "ada_di_pihps": True},
    {"kode": "7472", "nama": "Kota Bau-Bau", "ibukota": "Bau-Bau", "tipe": "Kota", "ada_di_pihps": True}
]


def fetch_sp2kp_commodity_prices(variant_id, start_date="2026-10-15", end_date="2026-10-23"):
    """Fetch daily prices for all regencies in Sultra for a variant."""
    ctx = ssl.create_default_context()
    ctx.check_hostname = False
    ctx.verify_mode = ssl.CERT_NONE

    boundary = "----WebKitFormBoundaryAyomiSultraSP2KP"
    fields = [
        ("start_date", start_date),
        ("end_date", end_date),
        ("level", "2"),
        ("variant_id", str(variant_id)),
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
            "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7)",
            "Content-Type": f"multipart/form-data; boundary={boundary}"
        }
    )

    try:
        with urllib.request.urlopen(req, context=ctx, timeout=20) as r:
            res = json.loads(r.read().decode("utf-8"))
            return res.get("data") or []
    except Exception as e:
        print(f"Error fetching variant_id {variant_id}: {e}")
        return []


def run_sp2kp_sync():
    print("=" * 80)
    print("SINKRONISASI HARGA PANGAN SP2KP KEMENDAG RI - 17 KAB/KOTA SULTRA")
    print("=" * 80)

    start_date = "2026-10-15"
    end_date = "2026-10-23"

    results_by_kab = {k["kode"]: {
        "kode": k["kode"],
        "nama": k["nama"],
        "ibukota": k["ibukota"],
        "tipe": k["tipe"],
        "ada_di_pihps": k["ada_di_pihps"],
        "komoditas": {}
    } for k in ALL_17_KAB_KOTA_SULTRA}

    # Normalize name helper
    def norm_name(s):
        return s.lower().replace("kab.", "").replace("kota", "").replace("-", " ").strip()

    for item in COMMODITY_MAPPING:
        vid = item["variant_id"]
        pname = item["pihps_name"]
        sname = item["sp2kp_name"]
        print(f"Mengunduh {pname} (SP2KP: {sname}, ID: {vid})...")

        raw_data = fetch_sp2kp_commodity_prices(vid, start_date=start_date, end_date=end_date)
        print(f"  -> Diterima data untuk {len(raw_data)} Kab/Kota")

        for row in raw_data:
            r_kode = str(row.get("kode", "")).strip()
            r_wilayah = str(row.get("wilayah", "")).strip()
            daftar_harga = row.get("daftarHarga", [])

            # Match to ALL_17_KAB_KOTA_SULTRA
            matched_kode = None
            if r_kode in results_by_kab:
                matched_kode = r_kode
            else:
                for k in ALL_17_KAB_KOTA_SULTRA:
                    if norm_name(k["nama"]) in norm_name(r_wilayah) or norm_name(r_wilayah) in norm_name(k["nama"]):
                        matched_kode = k["kode"]
                        break

            if not matched_kode:
                continue

            # Calculate latest price, previous price, and diff
            clean_prices = []
            for dp in daftar_harga:
                p_val = dp.get("harga")
                d_str = dp.get("date")
                if p_val is not None:
                    clean_prices.append({"date": d_str, "harga": round(float(p_val))})

            latest_p = clean_prices[-1]["harga"] if clean_prices else None
            prev_p = clean_prices[-2]["harga"] if len(clean_prices) >= 2 else latest_p
            diff_rp = (latest_p - prev_p) if (latest_p and prev_p) else 0
            diff_pct = round((diff_rp / prev_p * 100), 2) if (prev_p and prev_p > 0) else 0.0

            # Compare to HET / HAP
            het_val = item["het_hap"]
            dev_het_rp = (latest_p - het_val) if latest_p else None
            dev_het_pct = round((dev_het_rp / het_val * 100), 2) if (latest_p and het_val) else None

            status_het = "Aman"
            if dev_het_pct is not None:
                if dev_het_pct > 20:
                    status_het = "Sangat Tinggi"
                elif dev_het_pct > 0:
                    status_het = "Di Atas Acuan"
                elif dev_het_pct >= -5:
                    status_het = "Sesuai Acuan"
                else:
                    status_het = "Di Bawah Acuan"

            results_by_kab[matched_kode]["komoditas"][item["id"]] = {
                "pihps_name": pname,
                "sp2kp_name": sname,
                "icon": item["icon"],
                "satuan": item["satuan"],
                "harga_terkini": latest_p,
                "harga_sebelumnya": prev_p,
                "perubahan_rp": diff_rp,
                "perubahan_pct": diff_pct,
                "het_hap": het_val,
                "label_regulasi": item["label_regulasi"],
                "deviasi_het_rp": dev_het_rp,
                "deviasi_het_pct": dev_het_pct,
                "status_het": status_het,
                "deret_harga": clean_prices
            }

    # Build Summary Matrix
    output_payload = {
        "metadata": {
            "sumber": "Sistem Pemantauan Pasar dan Kebutuhan Pokok (SP2KP) - Kementerian Perdagangan RI",
            "tautan": "https://sp2kp.kemendag.go.id/statistik/tabulasi-harga",
            "provinsi": "Sulawesi Tenggara",
            "kode_provinsi": "74",
            "periode_mulai": start_date,
            "periode_selesai": end_date,
            "tanggal_terkini": end_date,
            "tanggal_terkini_id": "23 Oktober 2026",
            "waktu_ekstraksi": datetime.now().isoformat(),
            "total_kab_kota": len(ALL_17_KAB_KOTA_SULTRA),
            "total_komoditas": len(COMMODITY_MAPPING)
        },
        "penyetaraan_komoditas": COMMODITY_MAPPING,
        "kab_kota_list": ALL_17_KAB_KOTA_SULTRA,
        "data_per_kab_kota": results_by_kab
    }

    with open(OUT_FILE, "w", encoding="utf-8") as f:
        json.dump(output_payload, f, indent=2, ensure_ascii=False)

    print(f"\n[SUKSES] Dataset SP2KP 17 Kab/Kota Sultra disimpan ke: {OUT_FILE}")
    print("=" * 80)
    return output_payload


if __name__ == "__main__":
    run_sp2kp_sync()
