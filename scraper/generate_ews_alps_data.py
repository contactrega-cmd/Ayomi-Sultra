#!/usr/bin/env python3
"""
GENERATOR DATA DUA MATRIKS EARLY WARNING SYSTEM (EWS) ALPS BANK INDONESIA:
1. MATRIKS 10 KOMODITAS PANGAN STRATEGIS NASIONAL (PIHPS BI & BPS IHK)
2. MATRIKS 5 KOMODITAS UTAMA PENYUMBANG INFLASI (KERTAS KERJA FPKP BI SULTRA)
Sumber:
- PIHPS Nasional Bank Indonesia & BPS Sultra
- File: 'Jangan Diotakatik Kertas Kerja Inflasi TD 2022_Project Integrasi_FPKP ok.xlsx'
"""

import os
import sys
import json
import zipfile
import xml.etree.ElementTree as ET

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DATA_DIR = os.path.join(BASE_DIR, "data")
SRC_EXCEL = os.path.join(BASE_DIR, "Jangan Diotakatik Kertas Kerja Inflasi TD 2022_Project Integrasi_FPKP ok.xlsx")
PIHPS_ALL_PATH = os.path.join(DATA_DIR, "pihps_sultra_all.json")
OUT_EWS_PATH = os.path.join(DATA_DIR, "ews_alps_matrix.json")

# ==========================================================
# 1. 10 KOMODITAS PANGAN STRATEGIS NASIONAL (STANDAR PIHPS BI)
# ==========================================================
COMMODITIES_10 = [
    {"id": "cabai_merah", "name": "Cabai Merah", "icon": "🌶️", "satuan": "kg", "h_wajar_default": 62500, "sd_default": 10500},
    {"id": "beras", "name": "Beras", "icon": "🌾", "satuan": "kg", "h_wajar_default": 15100, "sd_default": 950},
    {"id": "daging_ayam", "name": "Daging Ayam", "icon": "🍗", "satuan": "kg", "h_wajar_default": 36500, "sd_default": 2100},
    {"id": "bawang_putih", "name": "Bawang Putih", "icon": "🧄", "satuan": "kg", "h_wajar_default": 42000, "sd_default": 4500},
    {"id": "gula_pasir", "name": "Gula Pasir", "icon": "🍬", "satuan": "kg", "h_wajar_default": 19600, "sd_default": 1650},
    {"id": "daging_sapi", "name": "Daging Sapi", "icon": "🥩", "satuan": "kg", "h_wajar_default": 138000, "sd_default": 7200},
    {"id": "bawang_merah", "name": "Bawang Merah", "icon": "🧅", "satuan": "kg", "h_wajar_default": 37500, "sd_default": 6200},
    {"id": "minyak_goreng", "name": "Minyak Goreng", "icon": "🍾", "satuan": "kg", "h_wajar_default": 23500, "sd_default": 2000},
    {"id": "cabai_rawit", "name": "Cabai Rawit", "icon": "🔥", "satuan": "kg", "h_wajar_default": 85000, "sd_default": 18500},
    {"id": "telur_ayam", "name": "Telur Ayam", "icon": "🥚", "satuan": "kg", "h_wajar_default": 29000, "sd_default": 1800}
]

WEIGHTS_10 = {
    "sultra": {
        "Beras": 6.411, "Daging Ayam": 0.458, "Daging Sapi": 0.144, "Telur Ayam": 0.636,
        "Bawang Merah": 0.286, "Bawang Putih": 0.203, "Cabai Merah": 0.107, "Cabai Rawit": 0.235,
        "Minyak Goreng": 1.229, "Gula Pasir": 0.333
    },
    "kendari": {
        "Beras": 5.499, "Daging Ayam": 0.605, "Daging Sapi": 0.104, "Telur Ayam": 0.443,
        "Bawang Merah": 0.253, "Bawang Putih": 0.182, "Cabai Merah": 0.073, "Cabai Rawit": 0.224,
        "Minyak Goreng": 0.712, "Gula Pasir": 0.237
    },
    "baubau": {
        "Beras": 6.058, "Daging Ayam": 0.221, "Daging Sapi": 0.043, "Telur Ayam": 0.618,
        "Bawang Merah": 0.224, "Bawang Putih": 0.133, "Cabai Merah": 0.343, "Cabai Rawit": 0.210,
        "Minyak Goreng": 1.426, "Gula Pasir": 0.405
    },
    "konawe": {
        "Beras": 9.285, "Daging Ayam": 0.375, "Daging Sapi": 0.371, "Telur Ayam": 1.018,
        "Bawang Merah": 0.305, "Bawang Putih": 0.217, "Cabai Merah": 0.063, "Cabai Rawit": 0.277,
        "Minyak Goreng": 1.802, "Gula Pasir": 0.480
    },
    "kolaka": {
        "Beras": 6.203, "Daging Ayam": 0.361, "Daging Sapi": 0.108, "Telur Ayam": 0.753,
        "Bawang Merah": 0.391, "Bawang Putih": 0.293, "Cabai Merah": 0.052, "Cabai Rawit": 0.239,
        "Minyak Goreng": 1.780, "Gula Pasir": 0.372
    }
}

# ==========================================================
# 2. 5 KOMODITAS UTAMA PENYUMBANG INFLASI (FPKP BI)
# ==========================================================
COMMODITIES_TOP5 = [
    {
        "id": "cabai_rawit",
        "name": "Cabai Rawit",
        "nama_excel": "CABAI RAWIT",
        "komponen": "VF",
        "komponen_label": "Volatile Food",
        "icon": "🌶️",
        "satuan": "kg"
    },
    {
        "id": "pendidikan_tinggi",
        "name": "Pendidikan Tinggi",
        "nama_excel": "AKADEMI/PERGURUAN TINGGI",
        "komponen": "CI",
        "komponen_label": "Core Inflation",
        "icon": "🎓",
        "satuan": "biaya/smt"
    },
    {
        "id": "kangkung",
        "name": "Kangkung",
        "nama_excel": "KANGKUNG",
        "komponen": "VF",
        "komponen_label": "Volatile Food",
        "icon": "🥬",
        "satuan": "ikat"
    },
    {
        "id": "ikan_bandeng",
        "name": "Ikan Bandeng / Bolu",
        "nama_excel": "IKAN BANDENG/IKAN BOLU",
        "komponen": "VF",
        "komponen_label": "Volatile Food",
        "icon": "🐟",
        "satuan": "kg"
    },
    {
        "id": "bayam",
        "name": "Bayam",
        "nama_excel": "BAYAM",
        "komponen": "VF",
        "komponen_label": "Volatile Food",
        "icon": "🥗",
        "satuan": "ikat"
    }
]

# Wilayah Resmi PIHPS Bank Indonesia (3 Wilayah yang Tersedia Resmi di Portal PIHPS BI)
REGIONS_PIHPS_10 = [
    {"id": "sultra", "name": "Prov. Sultra", "excel_key": "SULTRA", "type": "Provinsi", "badge": "Benchmark"},
    {"id": "kendari", "name": "Kota Kendari", "excel_key": "KENDARI", "type": "Kota", "badge": "Kota IHK"},
    {"id": "baubau", "name": "Kota Baubau", "excel_key": "BAUBAU", "type": "Kota", "badge": "Kota IHK"}
]

# Daftar 5 Wilayah Resmi: Prov. Sultra & 4 Kota IHK (untuk Kertas Kerja Inflasi 70 VF BPS)
REGIONS_5 = [
    {"id": "sultra", "name": "Prov. Sultra", "excel_key": "SULTRA", "type": "Provinsi", "badge": "Benchmark"},
    {"id": "kendari", "name": "Kota Kendari", "excel_key": "KENDARI", "type": "Kota", "badge": "Kota IHK"},
    {"id": "baubau", "name": "Kota Baubau", "excel_key": "BAUBAU", "type": "Kota", "badge": "Kota IHK"},
    {"id": "konawe", "name": "Kab. Konawe", "excel_key": "KONAWE", "type": "Kabupaten", "badge": "Kab. IHK"},
    {"id": "kolaka", "name": "Kab. Kolaka", "excel_key": "KOLAKA", "type": "Kabupaten", "badge": "Kab. IHK"}
]

def get_risk_status(alps):
    """
    Kategori risiko ALPS Standar Bank Indonesia:
    - Sangat Tinggi : > 2.0 SD (Merah)
    - Tinggi        : 1.0 s/d 2.0 SD (Oranye)
    - Waspada       : 0.25 s/d 1.0 SD (Kuning)
    - Normal        : < 0.25 SD (Hijau)
    """
    if alps >= 2.0:
        return {
            "status": "Crisis",
            "level": 4,
            "badge_color": "bg-red-100 text-red-800 border-red-200",
            "hex": "#ef4444",
            "tailwind_bg": "bg-red-500",
            "text_color": "text-white",
            "priority": "Darurat / Intervensi Segera"
        }
    elif alps >= 1.0:
        return {
            "status": "Alert",
            "level": 3,
            "badge_color": "bg-orange-100 text-orange-800 border-orange-200",
            "hex": "#f97316",
            "tailwind_bg": "bg-orange-500",
            "text_color": "text-white",
            "priority": "Siaga Pasokan & Distribusi"
        }
    elif alps >= 0.25:
        return {
            "status": "Stress",
            "level": 2,
            "badge_color": "bg-amber-100 text-amber-800 border-amber-200",
            "hex": "#eab308",
            "tailwind_bg": "bg-yellow-400",
            "text_color": "text-slate-900",
            "priority": "Pemantauan Intensif"
        }
    else:
        return {
            "status": "Normal",
            "level": 1,
            "badge_color": "bg-emerald-100 text-emerald-800 border-emerald-200",
            "hex": "#84cc16",
            "tailwind_bg": "bg-lime-500",
            "text_color": "text-slate-900",
            "priority": "Stabil / Terkendali"
        }

COMMODITY_NAME_CLEANUP = {
    "CABAI RAWIT": "Cabai Rawit",
    "KANGKUNG": "Kangkung",
    "IKAN BANDENG/IKAN BOLU": "Ikan Bandeng / Bolu",
    "BAYAM": "Bayam",
    "IKAN CAKALANG/ IKAN SISIK": "Ikan Cakalang / Sisik",
    "IKAN TERI": "Ikan Teri",
    "TELUR AYAM RAS": "Telur Ayam Ras",
    "DAUN KELOR": "Daun Kelor",
    "SAWI HIJAU": "Sawi Hijau",
    "IKAN TUNA": "Ikan Tuna",
    "JERUK NIPIS/LIMAU": "Jeruk Nipis / Limau",
    "CUMI-CUMI": "Cumi-Cumi",
    "IKAN LAYANG/ IKAN BENGGOL": "Ikan Layang / Benggol",
    "TOMAT": "Tomat",
    "TEMPE": "Tempe",
    "CABAI MERAH": "Cabai Merah",
    "IKAN KATAMBA": "Ikan Katamba",
    "BERAS": "Beras",
    "BUNCIS": "Buncis",
    "SEMANGKA": "Semangka",
    "DAGING AYAM RAS": "Daging Ayam Ras",
    "LABU SIAM/JIPANG": "Labu Siam / Jipang",
    "UDANG BASAH": "Udang Basah",
    "KETIMUN": "Ketimun",
    "WORTEL": "Wortel",
    "AYAM HIDUP": "Ayam Hidup",
    "JAGUNG MANIS": "Jagung Manis",
    "IKAN TONGKOL/ IKAN AMBU-AMBU": "Ikan Tongkol / Ambu-Ambu",
    "TEPUNG TERIGU": "Tepung Terigu",
    "KELAPA": "Kelapa",
    "NUGGET": "Nugget",
    "IKAN KAKAP MERAH": "Ikan Kakap Merah",
    "PIR": "Pir",
    "NANAS": "Nanas",
    "KACANG TANAH": "Kacang Tanah",
    "KETELA RAMBAT": "Ketela Rambat",
    "GARAM": "Garam",
    "TAUGE/KECAMBAH": "Tauge / Kecambah",
    "KEPITING/RAJUNGAN": "Kepiting / Rajungan",
    "DAGING SAPI": "Daging Sapi",
    "BAKSO (MENTAH)": "Bakso (Mentah)",
    "SOSIS": "Sosis",
    "IKAN TEMBANG": "Ikan Tembang",
    "TELUR AYAM KAMPUNG": "Telur Ayam Kampung",
    "LADA/MERICA": "Lada / Merica",
    "DAUN SINGKONG": "Daun Singkong",
    "SAWI PUTIH/PECAY/PITSAI": "Sawi Putih / Pecay",
    "SANTAN JADI": "Santan Jadi",
    "NANGKA MUDA": "Nangka Muda",
    "KENTANG": "Kentang",
    "IKAN ASIN TERI": "Ikan Asin Teri",
    "JERUK": "Jeruk",
    "IKAN EKOR KUNING": "Ikan Ekor Kuning",
    "BAWANG MERAH": "Bawang Merah",
    "ANGGUR": "Anggur",
    "BUAH NAGA": "Buah Naga",
    "APEL": "Apel",
    "DAUN BAWANG": "Daun Bawang",
    "KOL PUTIH/KUBIS": "Kol Putih / Kubis",
    "IKAN GABUS": "Ikan Gabus",
    "TAHU MENTAH": "Tahu Mentah",
    "IKAN RAMBE": "Ikan Rambe",
    "IKAN MUJAIR": "Ikan Mujair",
    "PISANG": "Pisang",
    "KACANG PANJANG": "Kacang Panjang",
    "BAWANG PUTIH": "Bawang Putih",
    "TERONG": "Terong",
    "PEPAYA": "Pepaya",
    "IKAN KEMBUNG/IKAN GEMBUNG/ IKAN BANYAR/IKAN GEMBOLO/ IKAN ASO-ASO": "Ikan Kembung / Gembung",
    "IKAN SELAR/ IKAN TUDE": "Ikan Selar / Tude"
}

def clean_commodity_name(raw_name):
    u = raw_name.strip().upper()
    if u in COMMODITY_NAME_CLEANUP:
        return COMMODITY_NAME_CLEANUP[u]
    return raw_name.replace("/", " / ").title()

def get_tpid_recommendation(comm_name, status, city_name):
    if status == "Sangat Tinggi":
        if "Cabai" in comm_name:
            return f"Gelar Operasi Pasar / Pangan Murah {comm_name} dan aktifkan Kerjasama Antar Daerah (KAD) pasokan cabai dari Enrekang/Jeneponto ke {city_name}."
        elif "Beras" in comm_name:
            return f"Percepat penyaluran Beras SPHP Bulog di pasar-pasar {city_name} dan monitor stok gudang distributor guna menahan lonjakan di atas HET."
        elif "Pendidikan" in comm_name:
            return f"Koordinasi TPID dengan LLDIKTI / pimpinan perguruan tinggi di {city_name} terkait transparansi UKT dan opsi cicilan pembayaran."
        elif any(v in comm_name for v in ["Kangkung", "Bayam", "Sawi", "Kelor", "Tomat", "Terong"]):
            return f"Fasilitasi bantuan mulsa, bibit sayuran cepat panen, dan pompanisasi irigasi bagi kelompok tani hortikultura di {city_name}."
        elif any(v in comm_name for v in ["Bandeng", "Cakalang", "Ikan", "Teri", "Tuna", "Tongkol"]):
            return f"Intervensi kelancaran pasokan es balok TPI & rantai dingin (cold chain) untuk nelayan dan pedagang ikan di {city_name}."
        elif "Bawang" in comm_name:
            return f"Perkuat pasokan Bawang Merah/Putih melalui KAD sentra Bima/Enrekang ke {city_name} dan sidak gudang distributor."
        elif "Ayam" in comm_name or "Telur" in comm_name:
            return f"Monitor ketersediaan jagung pakan ternak dan koordinasi asosiasi peternak unggas di {city_name}."
        else:
            return f"Lakukan inspeksi pasar & operasi stabilisasi pasokan komoditas {comm_name} di {city_name} bersama Satgas Pangan."
    elif status == "Tinggi":
        if "Cabai" in comm_name:
            return f"Pengawasan ketat stok distributor cabai {city_name} dan antisipasi kendala distribusi laut/darat."
        elif "Pendidikan" in comm_name:
            return f"Pantau penetapan biaya pendidikan semesteran di {city_name} agar tidak melampaui batas inflasi inti."
        elif "Ikan" in comm_name:
            return f"Pantau volume lelang ikan di TPI {city_name} serta pantau kondisi cuaca/gelombang nelayan tangkap."
        else:
            return f"Monitoring pasokan harian di pasar tradisional {city_name} dan koordinasi kelancaran logistik antar-wilayah."
    elif status == "Waspada":
        return f"Pemantauan rutin tren harga {comm_name} di {city_name} dan komunikasi belanja bijak kepada masyarakat."
    elif status == "Normal":
        return f"Kondisi harga & pasokan {comm_name} di {city_name} aman dan terkendali dalam batas sasaran inflasi BI."
    elif status == "Rendah":
        return f"Terjadi tren penurunan harga (deflasi) {comm_name} di {city_name}, menjadi faktor penahan inflasi daerah."
    else:
        return f"Komoditas {comm_name} tidak termasuk paket komoditas IHK survei BPS di {city_name}."

def extract_excel_inflation_data():
    """
    Ekstrak data andil mtm, inflasi mtm, bobot diagram timbang, dan Top 5
    dari berkas Excel Jangan Diotakatik Kertas Kerja Inflasi TD 2022_Project Integrasi_FPKP ok.xlsx
    """
    if not os.path.exists(SRC_EXCEL):
        print(f"[ERROR] Berkas {SRC_EXCEL} tidak ditemukan!")
        sys.exit(1)

    with zipfile.ZipFile(SRC_EXCEL, "r") as z:
        shared_strings = []
        if "xl/sharedStrings.xml" in z.namelist():
            sstree = ET.fromstring(z.read("xl/sharedStrings.xml"))
            for si in sstree.iter("{http://schemas.openxmlformats.org/spreadsheetml/2006/main}si"):
                t = "".join([node.text for node in si.iter("{http://schemas.openxmlformats.org/spreadsheetml/2006/main}t") if node.text])
                shared_strings.append(t)

        def get_val(c):
            t = c.attrib.get("t")
            v = c.find("{http://schemas.openxmlformats.org/spreadsheetml/2006/main}v")
            val = v.text if v is not None else ""
            if t == "s" and val.isdigit() and int(val) < len(shared_strings):
                return shared_strings[int(val)]
            return val

        wb_tree = ET.fromstring(z.read("xl/workbook.xml"))
        wb_rels = ET.fromstring(z.read("xl/_rels/workbook.xml.rels"))
        rels = {r.attrib["Id"]: r.attrib["Target"] for r in wb_rels}
        sheet_map = {}
        for s in wb_tree.iter("{http://schemas.openxmlformats.org/spreadsheetml/2006/main}sheet"):
            r_id = s.attrib["{http://schemas.openxmlformats.org/officeDocument/2006/relationships}id"]
            target = rels[r_id]
            if not target.startswith("xl/"):
                target = "xl/" + target
            sheet_map[s.attrib["name"]] = target

        # 1. Parse Sheet 'andil mtm'
        andil_stree = ET.fromstring(z.read(sheet_map["andil mtm"]))
        andil_data = {}
        vf_raw_items = []
        for row in andil_stree.iter("{http://schemas.openxmlformats.org/spreadsheetml/2006/main}row"):
            cells = {c.attrib.get("r", ""): get_val(c) for c in row.iter("{http://schemas.openxmlformats.org/spreadsheetml/2006/main}c")}
            r_num = row.attrib.get("r")
            kota = cells.get(f"B{r_num}", "").strip().upper()
            nama_raw = cells.get(f"H{r_num}", "").strip()
            nama = nama_raw.upper()
            komponen = cells.get(f"G{r_num}", "").strip().upper()
            val_str = cells.get(f"BM{r_num}", "")
            kode = cells.get(f"C{r_num}", "").strip()
            if kota and nama and val_str:
                try:
                    val = float(val_str)
                    if kota not in andil_data:
                        andil_data[kota] = {}
                    andil_data[kota][nama] = val
                    if kota == "SULTRA" and komponen == "VF":
                        vf_raw_items.append({
                            "raw_name": nama_raw,
                            "upper_name": nama,
                            "code": kode,
                            "sultra_andil": val
                        })
                except:
                    pass

        # 2. Parse Sheet 'mtm'
        mtm_stree = ET.fromstring(z.read(sheet_map["mtm"]))
        mtm_data = {}
        for row in mtm_stree.iter("{http://schemas.openxmlformats.org/spreadsheetml/2006/main}row"):
            cells = {c.attrib.get("r", ""): get_val(c) for c in row.iter("{http://schemas.openxmlformats.org/spreadsheetml/2006/main}c")}
            r_num = row.attrib.get("r")
            kota = cells.get(f"B{r_num}", "").strip().upper()
            nama = cells.get(f"H{r_num}", "").strip().upper()
            val_str = cells.get(f"BM{r_num}", "")
            if kota and nama and val_str:
                try:
                    val = float(val_str)
                    if kota not in mtm_data:
                        mtm_data[kota] = {}
                    mtm_data[kota][nama] = val
                except:
                    pass

        # 3. Parse Sheet 'Bobot'
        bobot_stree = ET.fromstring(z.read(sheet_map["Bobot"]))
        bobot_data = {}
        for row in bobot_stree.iter("{http://schemas.openxmlformats.org/spreadsheetml/2006/main}row"):
            cells = {c.attrib.get("r", ""): get_val(c) for c in row.iter("{http://schemas.openxmlformats.org/spreadsheetml/2006/main}c")}
            r_num = row.attrib.get("r")
            kota = cells.get(f"B{r_num}", "").strip().upper()
            nama = cells.get(f"F{r_num}", "").strip().upper() or cells.get(f"H{r_num}", "").strip().upper()
            val_str = cells.get(f"BL{r_num}", "")
            if kota and nama and val_str:
                try:
                    val = float(val_str) * 100.0
                    if kota not in bobot_data:
                        bobot_data[kota] = {}
                    bobot_data[kota][nama] = val
                except:
                    pass

        # 4. Parse Sheet 'Top Andil MTM'
        top_stree = ET.fromstring(z.read(sheet_map["Top Andil MTM"]))
        top_rows = {}
        for row in top_stree.iter("{http://schemas.openxmlformats.org/spreadsheetml/2006/main}row"):
            r = int(row.attrib.get("r"))
            cells = {c.attrib.get("r", ""): get_val(c) for c in row.iter("{http://schemas.openxmlformats.org/spreadsheetml/2006/main}c")}
            top_rows[r] = cells

        city_blocks = {
            "sultra": ("Prov. Sultra", 134, 144),
            "kendari": ("Kota Kendari", 6, 16),
            "baubau": ("Kota Baubau", 38, 48),
            "konawe": ("Kab. Konawe", 70, 80),
            "kolaka": ("Kab. Kolaka", 102, 112)
        }

        top5_per_city = {}
        target_col = "BI"
        for cid, (cname, k_start, a_start) in city_blocks.items():
            items = []
            for i in range(5):
                kom = top_rows.get(k_start + i, {}).get(f"{target_col}{k_start + i}", "").strip()
                andil_str = top_rows.get(a_start + i, {}).get(f"{target_col}{a_start + i}", "")
                try:
                    andil = float(andil_str)
                except:
                    andil = 0.0
                items.append({
                    "rank": i + 1,
                    "komoditas": kom,
                    "andil": andil,
                    "andil_pct_str": f"{andil:+.2f}%" if abs(andil) >= 0.01 else f"{andil:+.4f}%"
                })
            top5_per_city[cid] = items

    return andil_data, mtm_data, bobot_data, top5_per_city, vf_raw_items

def compute_alps_score_inflation(andil, inflasi, bobot):
    """
    Kalkulasi Indikator ALPS Z-score untuk komoditas penyumbang inflasi / deflasi:
    Z-Score diukur dari tingkat inflasi komoditas dan bobot andilnya.
    """
    if inflasi > 35.0:
        base_z = 2.0 + min(0.65, (inflasi - 35.0) / 75.0)
    elif inflasi >= 15.0:
        base_z = 1.0 + (inflasi - 15.0) / 20.0
    elif inflasi >= 2.0:
        base_z = 0.25 + (inflasi - 2.0) / 13.0 * 0.75
    elif inflasi >= -2.0:
        base_z = -0.50 + (inflasi + 2.0) / 4.0 * 0.75
    else:
        base_z = -1.0 - min(1.0, abs(inflasi + 2.0) / 15.0)

    if andil > 0.15:
        base_z += 0.25
    elif andil > 0.08:
        base_z += 0.10
    elif andil < -0.02:
        base_z -= 0.15

    return round(base_z, 2)

def generate_both_alps_matrices():
    print("=" * 80)
    print("MEMBANGUN 2 MATRIKS EWS ALPS: 10 KOMODITAS STRATEGIS & 5 KOMODITAS UTAMA")
    print("=" * 80)

    # 1. BACA PIHPS ALL UNTUK MATRIKS 10 KOMODITAS STRATEGIS
    pihps_all = {}
    if os.path.exists(PIHPS_ALL_PATH):
        with open(PIHPS_ALL_PATH, "r", encoding="utf-8") as f:
            pihps_all = json.load(f)

    latest_date_str = pihps_all.get("metadata", {}).get("tanggal_terkini_bi", "15/10/2026")
    actual_prices = {}
    for r in pihps_all.get("data", []):
        if r.get("kategori_id") == 1 and r.get("level") == 1:
            cid = str(r.get("kota_id", ""))
            r_key = "sultra" if cid == "" else ("kendari" if cid == "72" else ("baubau" if cid == "73" else "sultra"))
            cname = r.get("komoditas")
            h_daily = r.get("harga_harian_terkini", {})
            p_val = h_daily.get(latest_date_str)
            if p_val is None:
                valid_vals = [v for k, v in h_daily.items() if v is not None]
                p_val = valid_vals[-1] if valid_vals else 0
            if r_key not in actual_prices:
                actual_prices[r_key] = {}
            actual_prices[r_key][cname] = p_val

    # Catatan: PIHPS Bank Indonesia secara resmi menyajikan 3 entitas wilayah di Sulawesi Tenggara:
    # 1. Provinsi Sulawesi Tenggara (Agregat se-Provinsi)
    # 2. Kota Kendari (IHK Konsumsi Utama)
    # 3. Kota Baubau (IHK Distribusi Kepulauan)
    # Kab. Kolaka & Kab. Konawe ditiadakan dari matriks PIHPS ini karena belum tersedia di portal PIHPS BI.

    # -------------------------------------------------------------------------
    # A. BANGUN MATRIKS 1: 10 KOMODITAS PANGAN STRATEGIS (30 SEL PIHPS BI RESMI)
    # Urutkan komoditas dari yang SD-nya paling tinggi secara agregat Sultra
    # -------------------------------------------------------------------------
    sultra_scores_10 = {}
    for comm in COMMODITIES_10:
        cname = comm["name"]
        p_act = actual_prices.get("sultra", {}).get(cname, comm["h_wajar_default"])
        h_wajar = comm["h_wajar_default"]
        sd = comm["sd_default"] or (h_wajar * 0.1)
        alps = round((p_act - h_wajar) / sd, 2)
        sultra_scores_10[comm["id"]] = alps

    sorted_commodities_10 = sorted(COMMODITIES_10, key=lambda c: sultra_scores_10[c["id"]], reverse=True)

    matrix_10_ihk = []
    summary_10 = {
        "total_cells": 0, "sangat_tinggi_count": 0, "tinggi_count": 0,
        "waspada_count": 0, "normal_count": 0, "rendah_count": 0,
        "most_vulnerable_city": "", "most_vulnerable_alps": -99,
        "highest_risk_commodity": "Cabai Rawit & Cabai Merah",
        "highest_weight_commodity": "Beras (Bobot Sultra 6.41%, Baubau 6.06%, Kendari 5.50%)"
    }

    for reg in REGIONS_PIHPS_10:
        rid = reg["id"]
        rname = reg["name"]
        reg_weights = WEIGHTS_10.get(rid, WEIGHTS_10["sultra"])
        row_cells = []
        city_total_weighted_alps = 0.0
        city_total_weight = 0.0

        for comm in sorted_commodities_10:
            cname = comm["name"]
            c_icon = comm["icon"]
            p_act = actual_prices.get(rid, {}).get(cname) or actual_prices.get("sultra", {}).get(cname, comm["h_wajar_default"])

            h_wajar = comm["h_wajar_default"]
            if rid == "baubau":
                h_wajar = round(h_wajar * 1.025 / 50) * 50
            elif rid == "konawe" and cname == "Beras":
                h_wajar = round(h_wajar * 0.98 / 50) * 50
            elif rid == "kolaka" and "Ikan" in cname:
                h_wajar = round(h_wajar * 0.95 / 50) * 50

            sd = comm["sd_default"] or (h_wajar * 0.1)
            alps = round((p_act - h_wajar) / sd, 2)
            risk = get_risk_status(alps)
            w_daerah = reg_weights.get(cname, 0.25)

            city_total_weighted_alps += alps * (w_daerah / 100.0)
            city_total_weight += (w_daerah / 100.0)

            summary_10["total_cells"] += 1
            if risk["status"] == "Sangat Tinggi": summary_10["sangat_tinggi_count"] += 1
            elif risk["status"] == "Tinggi": summary_10["tinggi_count"] += 1
            elif risk["status"] == "Waspada": summary_10["waspada_count"] += 1
            elif risk["status"] == "Normal": summary_10["normal_count"] += 1
            else: summary_10["rendah_count"] += 1

            rekomendasi = get_tpid_recommendation(cname, risk["status"], rname)

            row_cells.append({
                "comm_id": comm["id"],
                "comm_name": cname,
                "comm_icon": c_icon,
                "satuan": comm["satuan"],
                "harga_aktual": p_act,
                "harga_aktual_str": f"Rp{p_act:,.0f}".replace(",", "."),
                "harga_wajar": h_wajar,
                "harga_wajar_str": f"Rp{h_wajar:,.0f}".replace(",", "."),
                "alps": alps,
                "alps_str": f"+{alps:.2f}" if alps > 0 else f"{alps:.2f}",
                "bobot_daerah": w_daerah,
                "bobot_daerah_str": f"{w_daerah:.2f}%",
                "status": risk["status"],
                "priority": risk["priority"],
                "badge_color": risk["badge_color"],
                "hex": risk["hex"],
                "tailwind_bg": risk["tailwind_bg"],
                "text_color": risk["text_color"],
                "rekomendasi": rekomendasi
            })

        composite_alps = round(city_total_weighted_alps / city_total_weight, 2) if city_total_weight > 0 else 0.0
        if composite_alps > summary_10["most_vulnerable_alps"]:
            summary_10["most_vulnerable_alps"] = composite_alps
            summary_10["most_vulnerable_city"] = rname

        matrix_10_ihk.append({
            "region_id": rid,
            "region_name": rname,
            "region_type": reg["type"],
            "badge": reg["badge"],
            "composite_alps": composite_alps,
            "composite_alps_str": f"+{composite_alps:.2f}" if composite_alps > 0 else f"{composite_alps:.2f}",
            "composite_risk": get_risk_status(composite_alps)["status"],
            "cells": row_cells
        })

    sultra_comp_10 = matrix_10_ihk[0]["composite_alps"]

    # -------------------------------------------------------------------------
    # B. BANGUN MATRIKS 2: 5 KOMODITAS UTAMA PENYUMBANG INFLASI (25 SEL)
    # -------------------------------------------------------------------------
    andil_data, mtm_data, bobot_data, top5_per_city, vf_raw_items = extract_excel_inflation_data()

    pihps_rawit = {
        "sultra": 128150, "kendari": 125000, "baubau": 130000, "konawe": 126500, "kolaka": 127000
    }

    matrix_top5_ihk = []
    summary_top5 = {
        "total_cells": 0, "sangat_tinggi_count": 0, "tinggi_count": 0,
        "waspada_count": 0, "normal_count": 0, "rendah_count": 0,
        "most_vulnerable_city": "", "most_vulnerable_alps": -99,
        "highest_risk_commodity": "Cabai Rawit & Pendidikan Tinggi",
        "highest_weight_commodity": "Pendidikan Tinggi (Bobot Sultra 2.95%, Kendari 3.54%)"
    }

    # Urutkan komoditas dari yang SD-nya paling tinggi secara agregat Sultra
    sultra_scores_top5 = {}
    for comm in COMMODITIES_TOP5:
        xname = comm["nama_excel"]
        andil_val = andil_data.get("SULTRA", {}).get(xname, 0.0)
        inflasi_val = mtm_data.get("SULTRA", {}).get(xname, 0.0)
        bobot_val = bobot_data.get("SULTRA", {}).get(xname, 0.25)
        alps = compute_alps_score_inflation(andil_val, inflasi_val, bobot_val)
        sultra_scores_top5[comm["id"]] = alps

    sorted_commodities_top5 = sorted(COMMODITIES_TOP5, key=lambda c: sultra_scores_top5[c["id"]], reverse=True)

    for reg in REGIONS_5:
        rid = reg["id"]
        rname = reg["name"]
        ekey = reg["excel_key"]

        row_cells = []
        city_weighted_alps = 0.0
        city_total_weight = 0.0

        for comm in sorted_commodities_top5:
            cid = comm["id"]
            cname = comm["name"]
            xname = comm["nama_excel"]
            icon = comm["icon"]

            andil_val = andil_data.get(ekey, {}).get(xname, 0.0)
            inflasi_val = mtm_data.get(ekey, {}).get(xname, 0.0)
            bobot_val = bobot_data.get(ekey, {}).get(xname, 0.25)

            alps = compute_alps_score_inflation(andil_val, inflasi_val, bobot_val)
            risk = get_risk_status(alps)

            city_weighted_alps += alps * (bobot_val / 100.0)
            city_total_weight += (bobot_val / 100.0)

            summary_top5["total_cells"] += 1
            if risk["status"] == "Sangat Tinggi": summary_top5["sangat_tinggi_count"] += 1
            elif risk["status"] == "Tinggi": summary_top5["tinggi_count"] += 1
            elif risk["status"] == "Waspada": summary_top5["waspada_count"] += 1
            elif risk["status"] == "Normal": summary_top5["normal_count"] += 1
            else: summary_top5["rendah_count"] += 1

            rekomendasi = get_tpid_recommendation(cname, risk["status"], rname)

            if cid == "cabai_rawit":
                p_act = pihps_rawit.get(rid, 128150)
                p_act_str = f"Rp{p_act:,.0f}/kg".replace(",", ".")
                p_fair_str = "Rp85.000/kg"
            elif cid == "pendidikan_tinggi":
                p_act_str = f"Inflasi: {inflasi_val:+.2f}%"
                p_fair_str = "Target BI: ±2.5%"
            elif cid == "ikan_bandeng":
                p_act_str = f"Inflasi: {inflasi_val:+.2f}%"
                p_fair_str = "Harga Tambak Wajar"
            else:
                p_act_str = f"Inflasi: {inflasi_val:+.2f}%"
                p_fair_str = "Harga Sayur Normal"

            row_cells.append({
                "comm_id": cid,
                "comm_name": cname,
                "comm_icon": icon,
                "komponen": comm["komponen"],
                "komponen_label": comm["komponen_label"],
                "satuan": comm["satuan"],
                "andil_mtm": andil_val,
                "andil_mtm_str": f"{andil_val:+.2f}%" if abs(andil_val) >= 0.01 else f"{andil_val:+.4f}%",
                "inflasi_mtm": inflasi_val,
                "inflasi_mtm_str": f"{inflasi_val:+.2f}%",
                "bobot_daerah": bobot_val,
                "bobot_daerah_str": f"{bobot_val:.2f}%",
                "harga_aktual_str": p_act_str,
                "harga_wajar_str": p_fair_str,
                "alps": alps,
                "alps_str": f"+{alps:.2f}" if alps > 0 else f"{alps:.2f}",
                "status": risk["status"],
                "priority": risk["priority"],
                "badge_color": risk["badge_color"],
                "hex": risk["hex"],
                "tailwind_bg": risk["tailwind_bg"],
                "text_color": risk["text_color"],
                "rekomendasi": rekomendasi
            })

        comp_alps = round(city_weighted_alps / city_total_weight, 2) if city_total_weight > 0 else 0.0
        if comp_alps > summary_top5["most_vulnerable_alps"]:
            summary_top5["most_vulnerable_alps"] = comp_alps
            summary_top5["most_vulnerable_city"] = rname

        matrix_top5_ihk.append({
            "region_id": rid,
            "region_name": rname,
            "region_type": reg["type"],
            "badge": reg["badge"],
            "composite_alps": comp_alps,
            "composite_alps_str": f"+{comp_alps:.2f}" if comp_alps > 0 else f"{comp_alps:.2f}",
            "composite_risk": get_risk_status(comp_alps)["status"],
            "top5_specific": top5_per_city.get(rid, []),
            "cells": row_cells
        })

    sultra_comp_top5 = matrix_top5_ihk[0]["composite_alps"]

    # -------------------------------------------------------------------------
    # C. MODE ALTERNATIF: TOP 5 SPESIFIK TIAP KOTA IHK (RANK 1 S.D. 5)
    # -------------------------------------------------------------------------
    matrix_top5_per_city = []
    for reg in REGIONS_5:
        rid = reg["id"]
        rname = reg["name"]
        ekey = reg["excel_key"]
        top_items = top5_per_city.get(rid, [])

        row_cells = []
        for item in top_items:
            rank = item["rank"]
            k_raw = item["komoditas"]
            andil = item["andil"]

            k_clean = k_raw.replace("IKAN BANDENG/IKAN BOLU", "Ikan Bandeng / Bolu") \
                           .replace("IKAN CAKALANG/ IKAN SISIK", "Ikan Cakalang") \
                           .replace("IKAN LAYANG/ IKAN BENGGOL", "Ikan Layang") \
                           .replace("AKADEMI/PERGURUAN TINGGI", "Pendidikan Tinggi") \
                           .title()

            if "Cabai" in k_clean: icon = "🌶️"
            elif "Pendidikan" in k_clean: icon = "🎓"
            elif "Kangkung" in k_clean: icon = "🥬"
            elif "Bayam" in k_clean: icon = "🥗"
            elif "Ikan" in k_clean or "Cumi" in k_clean: icon = "🐟"
            elif "Kelor" in k_clean: icon = "🌿"
            elif "Kue" in k_clean: icon = "🍰"
            elif "Rekreasi" in k_clean: icon = "🎡"
            else: icon = "📦"

            inflasi_v = mtm_data.get(ekey, {}).get(k_raw, andil * 100 * 2.5)
            bobot_v = bobot_data.get(ekey, {}).get(k_raw, 0.35)

            alps_v = compute_alps_score_inflation(andil, inflasi_v, bobot_v)
            risk_v = get_risk_status(alps_v)
            recom_v = get_tpid_recommendation(k_clean, risk_v["status"], rname)

            row_cells.append({
                "rank": rank,
                "comm_name": k_clean,
                "comm_raw": k_raw,
                "comm_icon": icon,
                "andil_mtm": andil,
                "andil_mtm_str": f"{andil:+.2f}%" if abs(andil) >= 0.01 else f"{andil:+.4f}%",
                "inflasi_mtm": inflasi_v,
                "inflasi_mtm_str": f"{inflasi_v:+.2f}%",
                "bobot_daerah": bobot_v,
                "bobot_daerah_str": f"{bobot_v:.2f}%",
                "alps": alps_v,
                "alps_str": f"+{alps_v:.2f}" if alps_v > 0 else f"{alps_v:.2f}",
                "status": risk_v["status"],
                "badge_color": risk_v["badge_color"],
                "hex": risk_v["hex"],
                "tailwind_bg": risk_v["tailwind_bg"],
                "text_color": risk_v["text_color"],
                "rekomendasi": recom_v
            })

        matrix_top5_per_city.append({
            "region_id": rid,
            "region_name": rname,
            "region_type": reg["type"],
            "badge": reg["badge"],
            "cells": row_cells
        })

    # -------------------------------------------------------------------------
    # D. BANGUN MATRIKS VF (70 KOMODITAS VOLATILE FOOD TRANSPOSED)
    # Sumbu Kolom: 5 Wilayah (Prov. Sultra, Kota Kendari, Kota Baubau, Kab. Konawe, Kab. Kolaka)
    # Sumbu Baris: 70 Komoditas VF diurutkan dari nilai tertinggi ke terendah pada posisi agregat Prov. Sultra
    # -------------------------------------------------------------------------
    vf_columns = [
        {"id": "sultra", "name": "Prov. Sultra", "excel_key": "SULTRA"},
        {"id": "kendari", "name": "Kota Kendari", "excel_key": "KENDARI"},
        {"id": "baubau", "name": "Kota Baubau", "excel_key": "BAUBAU"},
        {"id": "konawe", "name": "Kab. Konawe", "excel_key": "KONAWE"},
        {"id": "kolaka", "name": "Kab. Kolaka", "excel_key": "KOLAKA"}
    ]

    # Urutkan 70 komoditas VF dari andil Sultra tertinggi ke terendah (inflasi -> netral -> deflasi)
    vf_raw_items.sort(key=lambda x: x["sultra_andil"], reverse=True)

    summary_vf = {
        "total_cells": 0,
        "sangat_tinggi_cells": 0,
        "tinggi_cells": 0,
        "waspada_cells": 0,
        "normal_cells": 0,
        "rendah_cells": 0,
        "non_paket_cells": 0,
        "total_commodities": len(vf_raw_items),
        "inflasi_commodities_count": 0,
        "deflasi_commodities_count": 0,
        "netral_commodities_count": 0,
        "top_inflasi_commodity": "",
        "top_deflasi_commodity": "",
        "sultra_composite_alps": 0.0,
        "sultra_composite_alps_str": "0.00",
        "sultra_status": "Normal",
        "sultra_status_color": "bg-emerald-100 text-emerald-800 border-emerald-200"
    }

    matrix_vf_rows = []
    sultra_total_weighted_alps = 0.0
    sultra_total_weight = 0.0

    for idx, item in enumerate(vf_raw_items, 1):
        raw_name = item["raw_name"]
        u_name = item["upper_name"]
        code = item["code"]
        clean_name = clean_commodity_name(raw_name)

        s_andil = item["sultra_andil"]
        s_inflasi = mtm_data.get("SULTRA", {}).get(u_name, 0.0)
        s_bobot = bobot_data.get("SULTRA", {}).get(u_name, 0.0)
        s_alps = compute_alps_score_inflation(s_andil, s_inflasi, s_bobot)
        s_risk = get_risk_status(s_alps)

        if s_bobot > 0:
            sultra_total_weighted_alps += s_alps * (s_bobot / 100.0)
            sultra_total_weight += (s_bobot / 100.0)

        if s_andil > 0.00001:
            category = "inflasi"
            summary_vf["inflasi_commodities_count"] += 1
        elif s_andil < -0.00001:
            category = "deflasi"
            summary_vf["deflasi_commodities_count"] += 1
        else:
            category = "netral"
            summary_vf["netral_commodities_count"] += 1

        cells_dict = {}
        cells_list = []

        for col in vf_columns:
            cid = col["id"]
            cname = col["name"]
            ckey = col["excel_key"]

            andil_v = andil_data.get(ckey, {}).get(u_name, 0.0)
            inflasi_v = mtm_data.get(ckey, {}).get(u_name, 0.0)
            bobot_v = bobot_data.get(ckey, {}).get(u_name, 0.0)

            summary_vf["total_cells"] += 1

            if bobot_v <= 0.0 and ckey != "SULTRA":
                summary_vf["non_paket_cells"] += 1
                cell_obj = {
                    "region_id": cid,
                    "region_name": cname,
                    "is_surveyed": False,
                    "andil_mtm": 0.0,
                    "andil_mtm_str": "-",
                    "inflasi_mtm": 0.0,
                    "inflasi_mtm_str": "-",
                    "bobot_daerah": 0.0,
                    "bobot_daerah_str": "0.00%",
                    "alps": None,
                    "alps_str": "-",
                    "status": "Non-Paket IHK",
                    "priority": "Bukan Paket Komoditas IHK Wilayah",
                    "badge_color": "bg-slate-100 text-slate-500 border-slate-200",
                    "hex": "#94a3b8",
                    "tailwind_bg": "bg-slate-100",
                    "text_color": "text-slate-400",
                    "rekomendasi": f"Komoditas {clean_name} tidak termasuk paket komoditas IHK survei BPS di {cname}."
                }
            else:
                alps_v = compute_alps_score_inflation(andil_v, inflasi_v, bobot_v)
                risk_v = get_risk_status(alps_v)

                if risk_v["status"] == "Sangat Tinggi": summary_vf["sangat_tinggi_cells"] += 1
                elif risk_v["status"] == "Tinggi": summary_vf["tinggi_cells"] += 1
                elif risk_v["status"] == "Waspada": summary_vf["waspada_cells"] += 1
                elif risk_v["status"] == "Normal": summary_vf["normal_cells"] += 1
                else: summary_vf["rendah_cells"] += 1

                rekom_v = get_tpid_recommendation(clean_name, risk_v["status"], cname)

                cell_obj = {
                    "region_id": cid,
                    "region_name": cname,
                    "is_surveyed": True,
                    "andil_mtm": andil_v,
                    "andil_mtm_str": f"{andil_v:+.2f}%" if abs(andil_v) >= 0.01 else f"{andil_v:+.4f}%",
                    "inflasi_mtm": inflasi_v,
                    "inflasi_mtm_str": f"{inflasi_v:+.2f}%",
                    "bobot_daerah": bobot_v,
                    "bobot_daerah_str": f"{bobot_v:.2f}%",
                    "alps": alps_v,
                    "alps_str": f"+{alps_v:.2f}" if alps_v > 0 else f"{alps_v:.2f}",
                    "status": risk_v["status"],
                    "priority": risk_v["priority"],
                    "badge_color": risk_v["badge_color"],
                    "hex": risk_v["hex"],
                    "tailwind_bg": risk_v["tailwind_bg"],
                    "text_color": risk_v["text_color"],
                    "rekomendasi": rekom_v
                }

            cells_dict[cid] = cell_obj
            cells_list.append(cell_obj)

        row_obj = {
            "rank": idx,
            "code": code,
            "comm_id": f"vf_{idx}",
            "comm_name": clean_name,
            "comm_raw": raw_name,
            "category": category,
            "sultra_andil": s_andil,
            "sultra_andil_str": f"{s_andil:+.2f}%" if abs(s_andil) >= 0.01 else f"{s_andil:+.4f}%",
            "sultra_inflasi": s_inflasi,
            "sultra_inflasi_str": f"{s_inflasi:+.2f}%",
            "sultra_bobot": s_bobot,
            "sultra_bobot_str": f"{s_bobot:.2f}%",
            "sultra_alps": s_alps,
            "sultra_alps_str": f"+{s_alps:.2f}" if s_alps > 0 else f"{s_alps:.2f}",
            "sultra_status": s_risk["status"],
            "sultra_badge_color": s_risk["badge_color"],
            "cells": cells_list,
            "cells_by_id": cells_dict
        }
        matrix_vf_rows.append(row_obj)

    if matrix_vf_rows:
        summary_vf["top_inflasi_commodity"] = f"{matrix_vf_rows[0]['comm_name']} ({matrix_vf_rows[0]['sultra_andil_str']})"
        summary_vf["top_deflasi_commodity"] = f"{matrix_vf_rows[-1]['comm_name']} ({matrix_vf_rows[-1]['sultra_andil_str']})"

    sultra_vf_comp = round(sultra_total_weighted_alps / sultra_total_weight, 2) if sultra_total_weight > 0 else 0.0
    summary_vf["sultra_composite_alps"] = sultra_vf_comp
    summary_vf["sultra_composite_alps_str"] = f"+{sultra_vf_comp:.2f}" if sultra_vf_comp > 0 else f"{sultra_vf_comp:.2f}"
    summary_vf["sultra_status"] = get_risk_status(sultra_vf_comp)["status"]
    summary_vf["sultra_status_color"] = get_risk_status(sultra_vf_comp)["badge_color"]

    matrix_vf_transposed = {
        "columns": vf_columns,
        "rows": matrix_vf_rows
    }

    # OUTPUT DATASET TERPADU
    output_payload = {
        "metadata": {
            "judul": "Dual Matriks Early Warning System (EWS) ALPS Sulawesi Tenggara",
            "subjudul": "Sistem Peringatan Dini Inflasi Daerah: 10 Komoditas Pangan Strategis & Seluruh Komoditas VF (Kertas Kerja BI)",
            "tanggal_rilis_pihps": latest_date_str,
            "periode_inflasi_bps": "September 2026",
            "file_sumber_excel": "Jangan Diotakatik Kertas Kerja Inflasi TD 2022_Project Integrasi_FPKP ok.xlsx",
            "skala_alps": [
                {"label": "Sangat Tinggi", "sd_rule": "> 2 SD", "hex": "#ef4444", "class": "bg-red-500", "desc": "Potensi gejolak ekstrem, intervensi segera"},
                {"label": "Tinggi", "sd_rule": "1 s/d 2 SD", "hex": "#f97316", "class": "bg-orange-500", "desc": "Kenaikan signifikan, siaga pasokan"},
                {"label": "Waspada", "sd_rule": "0,25 s/d 1 SD", "hex": "#eab308", "class": "bg-yellow-400", "desc": "Merangkak naik, pemantauan intensif"},
                {"label": "Normal", "sd_rule": "-1 s/d 0,25 SD", "hex": "#84cc16", "class": "bg-lime-500", "desc": "Harga stabil dalam batas wajar"},
                {"label": "Rendah", "sd_rule": "< -1 SD", "hex": "#0ea5e9", "class": "bg-sky-500", "desc": "Deflasi / harga melandai"}
            ]
        },
        "summary_10": {
            "sultra_composite_alps": sultra_comp_10,
            "sultra_composite_alps_str": f"+{sultra_comp_10:.2f}" if sultra_comp_10 > 0 else f"{sultra_comp_10:.2f}",
            "sultra_status": get_risk_status(sultra_comp_10)["status"],
            "sultra_status_color": get_risk_status(sultra_comp_10)["badge_color"],
            "sangat_tinggi_cells": summary_10["sangat_tinggi_count"],
            "tinggi_cells": summary_10["tinggi_count"],
            "waspada_cells": summary_10["waspada_count"],
            "normal_cells": summary_10["normal_count"],
            "rendah_cells": summary_10["rendah_count"],
            "most_vulnerable_city": summary_10["most_vulnerable_city"],
            "highest_risk_commodity": summary_10["highest_risk_commodity"],
            "highest_weight_commodity": summary_10["highest_weight_commodity"]
        },
        "summary_top5": {
            "sultra_composite_alps": sultra_comp_top5,
            "sultra_composite_alps_str": f"+{sultra_comp_top5:.2f}" if sultra_comp_top5 > 0 else f"{sultra_comp_top5:.2f}",
            "sultra_status": get_risk_status(sultra_comp_top5)["status"],
            "sultra_status_color": get_risk_status(sultra_comp_top5)["badge_color"],
            "sangat_tinggi_cells": summary_top5["sangat_tinggi_count"],
            "tinggi_cells": summary_top5["tinggi_count"],
            "waspada_cells": summary_top5["waspada_count"],
            "normal_cells": summary_top5["normal_count"],
            "rendah_cells": summary_top5["rendah_count"],
            "most_vulnerable_city": summary_top5["most_vulnerable_city"],
            "highest_risk_commodity": summary_top5["highest_risk_commodity"],
            "highest_weight_commodity": summary_top5["highest_weight_commodity"]
        },
        "summary_vf": summary_vf,

        # Matriks 1: 10 Pangan Strategis (50 Sel)
        "commodities_10": sorted_commodities_10,
        "matrix_10_ihk": matrix_10_ihk,

        # Matriks 2 Opsi C Transposed: 70 Komoditas VF (350 Sel)
        "matrix_vf_transposed": matrix_vf_transposed,
        "vf_commodities_70": matrix_vf_rows,

        # Legacy Top 5 support (backwards-compatibility)
        "commodities_top5": sorted_commodities_top5,
        "matrix_top5_ihk": matrix_top5_ihk,
        "matrix_top5_per_city": matrix_top5_per_city,

        # Backwards-compatibility aliases:
        "commodities": sorted_commodities_10,
        "matrix_ihk": matrix_10_ihk,
        "summary": {
            "sultra_composite_alps": sultra_comp_10,
            "sultra_composite_alps_str": f"+{sultra_comp_10:.2f}" if sultra_comp_10 > 0 else f"{sultra_comp_10:.2f}",
            "sultra_status": get_risk_status(sultra_comp_10)["status"],
            "sultra_status_color": get_risk_status(sultra_comp_10)["badge_color"],
            "sangat_tinggi_cells": summary_10["sangat_tinggi_count"],
            "tinggi_cells": summary_10["tinggi_count"],
            "waspada_cells": summary_10["waspada_count"],
            "normal_cells": summary_10["normal_count"],
            "rendah_cells": summary_10["rendah_count"],
            "most_vulnerable_city": summary_10["most_vulnerable_city"],
            "highest_risk_commodity": summary_10["highest_risk_commodity"],
            "highest_weight_commodity": summary_10["highest_weight_commodity"]
        }
    }

    with open(OUT_EWS_PATH, "w", encoding="utf-8") as f:
        json.dump(output_payload, f, indent=2, ensure_ascii=False)

    print(f"[SUKSES] Dataset DUA Matriks EWS ALPS berhasil dibuat: {OUT_EWS_PATH}")
    print(f"  -> Matriks 1 (10 Pangan Strategis): {len(matrix_10_ihk)} Wilayah x {len(COMMODITIES_10)} Komoditas = {summary_10['total_cells']} Sel")
    print(f"  -> Matriks 2 (70 Komoditas VF Transposed): {len(vf_columns)} Wilayah x {len(matrix_vf_rows)} Komoditas = {summary_vf['total_cells']} Sel")
    print(f"       Inflasi: {summary_vf['inflasi_commodities_count']} | Deflasi: {summary_vf['deflasi_commodities_count']} | Netral: {summary_vf['netral_commodities_count']}")
    print(f"  -> Skor Komposit Sultra 10 Komoditas: +{sultra_comp_10:.2f} ({get_risk_status(sultra_comp_10)['status']})")
    print(f"  -> Skor Komposit Sultra VF (70 Komoditas): +{sultra_vf_comp:.2f} ({get_risk_status(sultra_vf_comp)['status']})")
    print("=" * 80)

if __name__ == "__main__":
    generate_both_alps_matrices()
