#!/usr/bin/env python3
"""
Ekstraksi Data Disagregasi Inflasi (CI, AP, VF, and IHK UMUM) Sultra 2024-2026
ke format JSON untuk visualisasi di Dashboard EWS Inflasi (Tab Perkembangan Inflasi).
Sumber: Sheet 'Disagregasi' dan 'Bobot' pada Jangan Diotakatik Kertas Kerja Inflasi TD 2022_Project Integrasi_FPKP ok.xlsx
"""

import os
import json
import zipfile
import xml.etree.ElementTree as ET

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DATA_DIR = os.path.join(BASE_DIR, "data")
SRC_EXCEL = os.path.join(BASE_DIR, "Jangan Diotakatik Kertas Kerja Inflasi TD 2022_Project Integrasi_FPKP ok.xlsx")
OUT_JSON = os.path.join(DATA_DIR, "disagregasi_sultra_2024_2026.json")
BPS_YOY_FILE = os.path.join(DATA_DIR, "bps_inflation_2024_2026.json")
BPS_MTM_FILE = os.path.join(DATA_DIR, "bps_inflation_11_groups_mtm_2024_2026.json")
ARTIFACT_DIR = "/Users/regaprasetyo/.gemini/antigravity/brain/45b29b5e-87d9-439a-b46b-f9c22bf36c3e"

MONTH_NAMES_ID = [
    "", "Januari", "Februari", "Maret", "April", "Mei", "Juni",
    "Juli", "Agustus", "September", "Oktober", "November", "Desember"
]

def parse_num(val_str, default=None):
    if val_str is None or val_str == "" or val_str == "#N/A" or val_str == "#DIV/0!":
        return default
    try:
        return float(val_str)
    except:
        return default

def main():
    if not os.path.exists(SRC_EXCEL):
        print(f"Error: {SRC_EXCEL} tidak ditemukan!")
        return

    print("Mengekstrak data Disagregasi (CI, AP, VF, UMUM) dari Kertas Kerja FPKP BI...")
    with zipfile.ZipFile(SRC_EXCEL, "r") as z:
        wb_xml = z.read("xl/workbook.xml")
        root = ET.fromstring(wb_xml)
        ns = {
            "m": "http://schemas.openxmlformats.org/spreadsheetml/2006/main",
            "r": "http://schemas.openxmlformats.org/officeDocument/2006/relationships"
        }
        rels_xml = z.read("xl/_rels/workbook.xml.rels")
        root_rels = ET.fromstring(rels_xml)
        rel_map = {r.attrib["Id"]: r.attrib["Target"] for r in root_rels}

        shared_strings = []
        if "xl/sharedStrings.xml" in z.namelist():
            ss_root = ET.fromstring(z.read("xl/sharedStrings.xml"))
            for si in ss_root.findall(".//{http://schemas.openxmlformats.org/spreadsheetml/2006/main}si"):
                t = si.find(".//{http://schemas.openxmlformats.org/spreadsheetml/2006/main}t")
                shared_strings.append(t.text if t is not None else "")

        def get_val(c):
            t = c.attrib.get("t")
            v = c.find("m:v", ns)
            val = v.text if v is not None else ""
            if t == "s" and val.isdigit() and int(val) < len(shared_strings):
                return shared_strings[int(val)]
            return val

        # Baca sheet Disagregasi
        sheet_id = next(s.attrib["{http://schemas.openxmlformats.org/officeDocument/2006/relationships}id"] for s in root.findall(".//m:sheet", ns) if s.attrib["name"] == "Disagregasi")
        s_dis = ET.fromstring(z.read("xl/" + rel_map[sheet_id]))

        cells = {}
        for r in s_dis.findall(".//m:row", ns):
            r_num = int(r.attrib.get("r"))
            for c in r.findall("m:c", ns):
                ref = "".join(filter(str.isalpha, c.attrib.get("r")))
                cells[(r_num, ref)] = get_val(c)

        r1, r2 = {}, {}
        for (r, col), val in cells.items():
            if r == 1: r1[col] = val
            elif r == 2: r2[col] = val

        cols_timeline = []
        for col, m in r2.items():
            y = r1.get(col, "")
            if y in ["2024", "2025", "2026"] and m.isdigit():
                cols_timeline.append((col, int(y), int(m)))
        cols_timeline.sort(key=lambda x: (x[1], x[2]))

    # Row mappings in sheet Disagregasi:
    # 9: IHK UMUM, 10: IHK VF, 11: IHK AP, 12: IHK CI, 13: IHK Ikan Segar
    # 15: mtm UMUM, 16: mtm VF, 17: mtm AP, 18: mtm CI, 19: mtm Ikan Segar
    # 21: andil mtm UMUM, 22: andil mtm VF, 23: andil mtm AP, 24: andil mtm CI, 25: andil mtm Ikan Segar
    # 27: yoy UMUM, 28: yoy VF, 29: yoy AP, 30: yoy CI, 31: yoy Ikan Segar
    # 33: andil yoy UMUM, 34: andil yoy VF, 35: andil yoy AP, 36: andil yoy CI, 37: andil yoy Ikan Segar
    # 39: ytd UMUM, 40: ytd VF, 41: ytd AP, 42: ytd CI, 43: ytd Ikan Segar
    # 45: andil ytd UMUM, 46: andil ytd VF, 47: andil ytd AP, 48: andil ytd CI, 49: andil ytd Ikan Segar

    comp_rows = {
        "umum": {"ihk": 9, "mtm": 15, "andil_mtm": 21, "yoy": 27, "andil_yoy": 33, "ytd": 39, "andil_ytd": 45},
        "vf":   {"ihk": 10, "mtm": 16, "andil_mtm": 22, "yoy": 28, "andil_yoy": 34, "ytd": 40, "andil_ytd": 46},
        "ap":   {"ihk": 11, "mtm": 17, "andil_mtm": 23, "yoy": 29, "andil_yoy": 35, "ytd": 41, "andil_ytd": 47},
        "ci":   {"ihk": 12, "mtm": 18, "andil_mtm": 24, "yoy": 30, "andil_yoy": 36, "ytd": 42, "andil_ytd": 48},
        "ikan": {"ihk": 13, "mtm": 19, "andil_mtm": 25, "yoy": 31, "andil_yoy": 37, "ytd": 43, "andil_ytd": 49}
    }

    # Load data resmi BPS Sultra (Headline YoY dan MtM) untuk sinkronisasi 100% presisi
    bps_yoy_lookup = {}
    if os.path.exists(BPS_YOY_FILE):
        with open(BPS_YOY_FILE, "r", encoding="utf-8") as f:
            yoy_json = json.load(f)
            sultra_y = yoy_json.get("sultra", {}).get("data_tahunan", {})
            for yr, ydata in sultra_y.items():
                for m_item in ydata.get("bulanan", []):
                    m_num = m_item.get("bulan_angka")
                    v = m_item.get("inflasi_yoy")
                    if v is not None:
                        bps_yoy_lookup[(int(yr), int(m_num))] = float(v)

    bps_mtm_lookup = {}
    if os.path.exists(BPS_MTM_FILE):
        with open(BPS_MTM_FILE, "r", encoding="utf-8") as f:
            mtm_json = json.load(f)
            sultra_m = mtm_json.get("wilayah", {}).get("sultra", {}).get("data_tahunan", {})
            for yr, ydata in sultra_m.items():
                general_item = ydata.get("komoditas", {}).get("1", {})
                for m_str, v in general_item.get("bulanan", {}).items():
                    if v is not None:
                        bps_mtm_lookup[(int(yr), int(m_str))] = float(v)

    monthly_series = []
    for col, y, m in cols_timeline:
        row_obj = {
            "periode": f"{y}-{m:02d}",
            "tahun": y,
            "bulan": m,
            "periode_str": f"{MONTH_NAMES_ID[m]} {y}",
            "periode_singkat": f"{MONTH_NAMES_ID[m][:3]} '{str(y)[2:]}",
            "bulan_singkat": MONTH_NAMES_ID[m][:3]
        }

        for comp, r_dict in comp_rows.items():
            ihk_val = parse_num(cells.get((r_dict["ihk"], col)))
            mtm_val = parse_num(cells.get((r_dict["mtm"], col)))
            amtm_val = parse_num(cells.get((r_dict["andil_mtm"], col)))
            yoy_val = parse_num(cells.get((r_dict["yoy"], col)))
            ayoy_val = parse_num(cells.get((r_dict["andil_yoy"], col)))
            ytd_val = parse_num(cells.get((r_dict["ytd"], col)))
            aytd_val = parse_num(cells.get((r_dict["andil_ytd"], col)))

            # Harmonisasi Headline IHK Sultra dengan publikasi resmi BPS Sultra
            if comp == "umum":
                if (y, m) in bps_yoy_lookup:
                    yoy_val = bps_yoy_lookup[(y, m)]
                if (y, m) in bps_mtm_lookup:
                    mtm_val = bps_mtm_lookup[(y, m)]

            row_obj[comp] = {
                "ihk": round(ihk_val, 2) if ihk_val is not None else None,
                "mtm": round(mtm_val, 2) if mtm_val is not None else None,
                "andil_mtm": round(amtm_val, 2) if amtm_val is not None else None,
                "yoy": round(yoy_val, 2) if yoy_val is not None else None,
                "andil_yoy": round(ayoy_val, 2) if ayoy_val is not None else None,
                "ytd": round(ytd_val, 2) if ytd_val is not None else None,
                "andil_ytd": round(aytd_val, 2) if aytd_val is not None else None
            }

        monthly_series.append(row_obj)

    # Ringkasan per komponen untuk kartu ringkasan
    # Ambil periode terkini (September 2026) dan historis 2025/2026
    latest_row = monthly_series[-1]
    
    # 2025 and 2026 series for stats (exclude 2024 transition leaps for yoy ranges)
    s25_26 = [x for x in monthly_series if x["tahun"] >= 2025]

    def get_comp_summary(comp_key, name, full_name, bobot, deskripsi, color_theme):
        yoy_vals_2526 = [x[comp_key]["yoy"] for x in s25_26 if x[comp_key]["yoy"] is not None]
        mtm_vals = [x[comp_key]["mtm"] for x in monthly_series if x[comp_key]["mtm"] is not None and abs(x[comp_key]["mtm"]) < 20]
        
        min_yoy = min(yoy_vals_2526) if yoy_vals_2526 else 0.0
        max_yoy = max(yoy_vals_2526) if yoy_vals_2526 else 0.0
        min_mtm = min(mtm_vals) if mtm_vals else 0.0
        max_mtm = max(mtm_vals) if mtm_vals else 0.0

        latest_comp = latest_row[comp_key]
        
        # Status
        yoy_now = latest_comp["yoy"] or 0.0
        if comp_key == "umum":
            status = "✅ Sasaran BI" if 1.5 <= yoy_now <= 3.5 else ("Di Atas Target" if yoy_now > 3.5 else "Di Bawah Target")
            status_cls = "bg-emerald-100 text-emerald-800 border-emerald-200" if 1.5 <= yoy_now <= 3.5 else "bg-rose-100 text-rose-800 border-rose-200"
        elif comp_key == "ci":
            status = f"Bobot: {bobot:.2f}%"
            status_cls = "bg-sky-100 text-sky-800 border-sky-200"
        elif comp_key == "ap":
            status = f"Bobot: {bobot:.2f}%"
            status_cls = "bg-amber-100 text-amber-800 border-amber-200"
        elif comp_key == "vf":
            status = f"Bobot: {bobot:.2f}%"
            status_cls = "bg-rose-100 text-rose-800 border-rose-200"
        else:
            status = f"Bobot: {bobot:.2f}%"
            status_cls = "bg-indigo-100 text-indigo-800 border-indigo-200"

        # Trend note
        if comp_key == "umum":
            trend_note = "▲ Tren Naik" if (latest_comp["mtm"] or 0) > 0 else "▼ Terkendali"
            trend_cls = "text-rose-600" if (latest_comp["mtm"] or 0) > 0 else "text-emerald-700"
        elif comp_key == "ci":
            trend_note = "Pilar Utama (60.25%)"
            trend_cls = "text-sky-700 font-bold"
        elif comp_key == "ap":
            trend_note = "Tarif & Transportasi"
            trend_cls = "text-amber-700 font-bold"
        elif comp_key == "vf":
            trend_note = "Komponen Paling Bergejolak"
            trend_cls = "text-rose-700 font-bold"
        else:
            trend_note = "Faktor Angin Timur"
            trend_cls = "text-indigo-700 font-bold"

        return {
            "key": comp_key,
            "nama_singkat": name,
            "nama_lengkap": full_name,
            "bobot": bobot,
            "deskripsi": deskripsi,
            "color_theme": color_theme,
            "status": status,
            "status_cls": status_cls,
            "yoy_terkini": latest_comp["yoy"],
            "mtm_terkini": latest_comp["mtm"],
            "andil_yoy_terkini": latest_comp["andil_yoy"],
            "andil_mtm_terkini": latest_comp["andil_mtm"],
            "ihk_terkini": latest_comp["ihk"],
            "rentang_yoy": f"{min_yoy:.2f}% - {max_yoy:.2f}%",
            "rentang_mtm": f"{min_mtm:.2f}% - {max_mtm:.2f}%",
            "trend_note": trend_note,
            "trend_cls": trend_cls
        }

    summary_cards = [
        get_comp_summary(
            "umum", "IHK SULTRA", "IHK Umum Sulawesi Tenggara (Headline)", 100.000,
            "Agregat seluruh keranjang konsumsi 458 komoditas di 4 wilayah IHK (Kendari, Baubau, Konawe, Kolaka).",
            "indigo"
        ),
        get_comp_summary(
            "ci", "INFLASI INTI (CI)", "Core Inflation (Inflasi Inti)", 60.253,
            "Komponen persisten jangka panjang yang dipengaruhi fundamental penawaran-permintaan & ekspektasi inflasi.",
            "sky"
        ),
        get_comp_summary(
            "ap", "HARGA DIATUR PEMERINTAH (AP)", "Administered Prices (Harga Pemerintah)", 20.915,
            "Komponen tarif yang dikendalikan regulasi kebijakan pemerintah (BBM, tarif listrik, angkutan udara/laut, rokok).",
            "amber"
        ),
        get_comp_summary(
            "vf", "GEJOLAK PANGAN (VF)", "Volatile Food (Pangan Bergejolak)", 18.832,
            "Komponen pangan rentan terhadap cuaca buruk maritim, musiman tanam/panen, dan hari besar keagamaan (HBKN).",
            "rose"
        )
    ]

    output_payload = {
        "metadata": {
            "judul": "Disagregasi Inflasi IHK Sulawesi Tenggara: CI, AP, dan VF",
            "sumber": "Kertas Kerja Inflasi TD 2022_Project Integrasi_FPKP KPw BI Provinsi Sulawesi Tenggara & BPS",
            "periode": "Januari 2024 - September 2026",
            "tahun_dasar": "2022 = 100",
            "bobot_komponen": {
                "umum": 100.000,
                "ci": 60.253,
                "ap": 20.915,
                "vf": 18.832,
                "ikan_segar": 5.607
            }
        },
        "kartu_ringkasan": summary_cards,
        "deret_bulanan": monthly_series
    }

    with open(OUT_JSON, "w", encoding="utf-8") as f:
        json.dump(output_payload, f, ensure_ascii=False, indent=2)

    print(f"[OK] Berhasil membuat dataset Disagregasi: {OUT_JSON}")

    if os.path.exists(ARTIFACT_DIR):
        artifact_out = os.path.join(ARTIFACT_DIR, "disagregasi_sultra_2024_2026.json")
        with open(artifact_out, "w", encoding="utf-8") as f:
            json.dump(output_payload, f, ensure_ascii=False, indent=2)
        print(f"[OK] Disalin ke Brain Artifact: {artifact_out}")

if __name__ == "__main__":
    main()
