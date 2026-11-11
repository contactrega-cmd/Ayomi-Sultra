#!/usr/bin/env python3
"""
Ekstraksi Data Disagregasi Inflasi (CI, AP, VF, and IHK UMUM)
untuk Sultra dan 4 Kota IHK (Kendari, Baubau, Kolaka, Konawe) 2024-2026.
Sumber: Kertas Kerja Inflasi TD 2022 FPKP BI & BPS Sultra (Sheet Klasifikasi, NK Olah, Bobot).
"""

import os
import json
import zipfile
import xml.etree.ElementTree as ET

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DATA_DIR = os.path.join(BASE_DIR, "data")
SRC_EXCEL = os.path.join(BASE_DIR, "Jangan Diotakatik Kertas Kerja Inflasi TD 2022_Project Integrasi_FPKP ok.xlsx")
OUT_JSON = os.path.join(DATA_DIR, "disagregasi_sultra_2024_2026.json")
BPS_MTM_FILE = os.path.join(DATA_DIR, "bps_inflation_11_groups_mtm_2024_2026.json")
BPS_YOY_FILE = os.path.join(DATA_DIR, "bps_inflation_2024_2026.json")
ARTIFACT_DIR = "/Users/regaprasetyo/.gemini/antigravity/brain/45b29b5e-87d9-439a-b46b-f9c22bf36c3e"

MONTH_NAMES_ID = [
    "", "Januari", "Februari", "Maret", "April", "Mei", "Juni",
    "Juli", "Agustus", "September", "Oktober", "November", "Desember"
]
MONTH_SHORT_ID = [
    "", "Jan", "Feb", "Mar", "Apr", "Mei", "Jun",
    "Jul", "Agu", "Sep", "Okt", "Nov", "Des"
]

CITY_META = {
    "sultra": {
        "excel_name": "SULTRA",
        "nama": "Provinsi Sulawesi Tenggara",
        "nama_singkat": "IHK SULTRA",
        "tipe": "Provinsi",
        "deskripsi": "Agregat seluruh keranjang konsumsi di 4 wilayah IHK (Kendari, Baubau, Konawe, Kolaka)."
    },
    "kendari": {
        "excel_name": "KENDARI",
        "nama": "Kota Kendari",
        "nama_singkat": "IHK KOTA KENDARI",
        "tipe": "Kota",
        "deskripsi": "Ibukota Provinsi Sultra dengan bobot konsumsi terbesar, pusat jasa dan perdagangan."
    },
    "baubau": {
        "excel_name": "BAUBAU",
        "nama": "Kota Baubau",
        "nama_singkat": "IHK KOTA BAUBAU",
        "tipe": "Kota",
        "deskripsi": "Pusat logistik dan pelabuhan maritim Kepulauan Buton dan sekitarnya."
    },
    "kolaka": {
        "excel_name": "KOLAKA",
        "nama": "Kabupaten Kolaka",
        "nama_singkat": "IHK KAB. KOLAKA",
        "tipe": "Kabupaten",
        "deskripsi": "Wilayah IHK pesisir barat daratan Sultra dengan aktivitas industri dan perkebunan."
    },
    "konawe": {
        "excel_name": "KONAWE",
        "nama": "Kabupaten Konawe",
        "nama_singkat": "IHK KAB. KONAWE",
        "tipe": "Kabupaten",
        "deskripsi": "Lumbung padi utama dan sentra industri pengolahan strategis Sultra."
    }
}

def safe_float(v):
    if not v or v in ['#N/A', '#DIV/0!', '#VALUE!', '-']:
        return 0.0
    try:
        return float(v)
    except:
        return 0.0

def main():
    if not os.path.exists(SRC_EXCEL):
        print(f"Error: {SRC_EXCEL} tidak ditemukan!")
        return

    print("Mengekstrak data Disagregasi seluruh Kota IHK dari Kertas Kerja FPKP BI & BPS...")
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

        # 1. Klasifikasi rows 3 to 2292
        s_klas_id = next(s.attrib["{http://schemas.openxmlformats.org/officeDocument/2006/relationships}id"] for s in root.findall(".//m:sheet", ns) if s.attrib["name"] == "Klasifikasi")
        tree_klas = ET.fromstring(z.read("xl/" + rel_map[s_klas_id]))
        klas_data = {}
        for r in tree_klas.findall(".//m:row", ns):
            r_num = int(r.attrib.get("r"))
            if 3 <= r_num <= 2292:
                cells = {c.attrib.get("r"): get_val(c) for c in r.findall("m:c", ns)}
                klas_data[r_num] = {
                    "G": 1 if cells.get(f"G{r_num}") == "1" else 0, # UMUM
                    "H": 1 if cells.get(f"H{r_num}") == "1" else 0, # VF
                    "I": 1 if cells.get(f"I{r_num}") == "1" else 0, # AP
                    "J": 1 if cells.get(f"J{r_num}") == "1" else 0, # CI
                    "K": 1 if cells.get(f"K{r_num}") == "1" else 0, # Ikan Segar
                }

        # 2. NK Olah rows 5 to 2294
        s_nk_id = next(s.attrib["{http://schemas.openxmlformats.org/officeDocument/2006/relationships}id"] for s in root.findall(".//m:sheet", ns) if s.attrib["name"] == "NK Olah")
        tree_nk = ET.fromstring(z.read("xl/" + rel_map[s_nk_id]))

        r1, r2 = {}, {}
        for r in tree_nk.findall(".//m:row", ns):
            r_num = int(r.attrib.get("r"))
            if r_num == 1:
                for c in r.findall("m:c", ns):
                    col = "".join(filter(str.isalpha, c.attrib.get("r")))
                    val = get_val(c)
                    if val in ["2022", "2023", "2024", "2025", "2026"]:
                        r1[col] = int(val)
            elif r_num == 2:
                for c in r.findall("m:c", ns):
                    col = "".join(filter(str.isalpha, c.attrib.get("r")))
                    val = get_val(c)
                    if col in r1:
                        r2[col] = 0 if val == "TD" else (int(val) if val.isdigit() else -1)
            elif r_num > 4:
                break

        timeline = []
        for col, y in r1.items():
            m = r2.get(col, -1)
            if m >= 0:
                timeline.append((col, y, m))
        timeline.sort(key=lambda x: (x[1], x[2]))

        nk_rows = []
        for r in tree_nk.findall(".//m:row", ns):
            r_num = int(r.attrib.get("r"))
            if 5 <= r_num <= 2294:
                cells = {c.attrib.get("r"): get_val(c) for c in r.findall("m:c", ns)}
                city = cells.get(f"B{r_num}")
                r_klas = r_num - 2
                klas = klas_data.get(r_klas, {"G":0, "H":0, "I":0, "J":0, "K":0})
                nk_rows.append({"city": city, "klas": klas, "cells": cells, "r_nk": r_num})

    base_col = "H" # 2022 TD
    wilayah_dict = {}

    # Load official BPS headline MTM data to harmonize Umum headline across all tabs
    bps_official_mtm = {}
    if os.path.exists(BPS_MTM_FILE):
        try:
            with open(BPS_MTM_FILE, "r", encoding="utf-8") as f_bps:
                d_mtm = json.load(f_bps)
            for w, w_d in d_mtm.get("wilayah", {}).items():
                bps_official_mtm[w] = {}
                for yr_s, yr_d in w_d.get("data_tahunan", {}).items():
                    komods = yr_d.get("komoditas", {})
                    item_u = komods.get("1") or next((it for it in komods.values() if "0. UMUM" in it.get("label", "")), None)
                    if item_u:
                        for mn, val in item_u.get("bulanan", {}).items():
                            if val is not None:
                                bps_official_mtm[w][(int(yr_s), int(mn))] = float(val)
        except Exception as e:
            print("Notice loading BPS MTM:", e)

    # Load official BPS headline YoY data to harmonize Umum headline across all tabs
    bps_official_yoy = {}
    if os.path.exists(BPS_YOY_FILE):
        try:
            with open(BPS_YOY_FILE, "r", encoding="utf-8") as f_yoy:
                d_yoy = json.load(f_yoy)
            for w, w_d in d_yoy.items():
                bps_official_yoy[w] = {}
                for yr_s, yr_d in w_d.get("data_tahunan", {}).items():
                    for m_obj in yr_d.get("bulanan", []):
                        mn = m_obj.get("bulan_angka")
                        val = m_obj.get("inflasi_yoy")
                        if val is not None:
                            bps_official_yoy[w][(int(yr_s), int(mn))] = float(val)
        except Exception as e:
            print("Notice loading BPS YOY:", e)

    for w_key, meta in CITY_META.items():
        ex_city = meta["excel_name"]
        
        # Base sums for this city
        base_sums = {"G": 0.0, "H": 0.0, "I": 0.0, "J": 0.0, "K": 0.0}
        for row in nk_rows:
            if row["city"] == ex_city:
                b_val = safe_float(row["cells"].get(f"{base_col}{row['r_nk']}"))
                for k in ["G", "H", "I", "J", "K"]:
                    if row["klas"][k] == 1:
                        base_sums[k] += b_val

        tot_base = base_sums["G"]
        bobot_ci = round((base_sums["J"] / tot_base) * 100, 2)
        bobot_ap = round((base_sums["I"] / tot_base) * 100, 2)
        bobot_vf = round((base_sums["H"] / tot_base) * 100, 2)
        bobot_ikan = round((base_sums["K"] / tot_base) * 100, 2)

        # Monthly sums
        ihk_series = {}
        for col, y, m in timeline:
            if m == 0: continue
            c_sums = {"G": 0.0, "H": 0.0, "I": 0.0, "J": 0.0, "K": 0.0}
            for row in nk_rows:
                if row["city"] == ex_city:
                    c_val = safe_float(row["cells"].get(f"{col}{row['r_nk']}"))
                    for k in ["G", "H", "I", "J", "K"]:
                        if row["klas"][k] == 1:
                            c_sums[k] += c_val

            ihk_series[(y, m)] = {
                "G": (c_sums["G"] / base_sums["G"]) * 100,
                "H": round((c_sums["H"] / base_sums["H"]) * 100, 2),
                "I": round((c_sums["I"] / base_sums["I"]) * 100, 2),
                "J": round((c_sums["J"] / base_sums["J"]) * 100, 2),
                "K": round((c_sums["K"] / base_sums["K"]) * 100, 2),
            }

        # Build deret_bulanan (filter for 2024 - 2026)
        monthly_series = []
        for (y, m), curr in sorted(ihk_series.items()):
            if y < 2024: continue

            prev_m = 12 if m == 1 else m - 1
            prev_y = y - 1 if m == 1 else y
            prev = ihk_series.get((prev_y, prev_m))

            y_prev = ihk_series.get((y - 1, m))

            comp_stats = {}
            for k, tag in [("G", "umum"), ("J", "ci"), ("I", "ap"), ("H", "vf"), ("K", "ikan")]:
                c_val = curr[k]
                p_val = prev[k] if prev else c_val
                yp_val = y_prev[k] if y_prev else c_val

                mtm = round(((c_val - p_val) / p_val) * 100, 2) if p_val else 0.0
                yoy = round(((c_val - yp_val) / yp_val) * 100, 2) if yp_val else 0.0

                # Harmonize Headline UMUM with official BPS published YoY & MtM
                if tag == "umum" and (w_key in bps_official_yoy) and ((y, m) in bps_official_yoy[w_key]):
                    yoy = bps_official_yoy[w_key][(y, m)]
                if tag == "umum" and (w_key in bps_official_mtm) and ((y, m) in bps_official_mtm[w_key]):
                    mtm = bps_official_mtm[w_key][(y, m)]

                # Andil
                w_frac = (base_sums[k] / tot_base)
                andil_mtm = round(mtm * w_frac, 2)
                andil_yoy = round(yoy * w_frac, 2)

                comp_stats[tag] = {
                    "ihk": round(c_val, 2),
                    "mtm": mtm,
                    "andil_mtm": andil_mtm,
                    "yoy": yoy,
                    "andil_yoy": andil_yoy
                }

            monthly_series.append({
                "periode": f"{y}-{m:02d}",
                "tahun": y,
                "bulan": m,
                "periode_str": f"{MONTH_NAMES_ID[m]} {y}",
                "periode_singkat": f"{MONTH_SHORT_ID[m]} '{str(y)[2:]}",
                "bulan_singkat": MONTH_SHORT_ID[m],
                "umum": comp_stats["umum"],
                "ci": comp_stats["ci"],
                "ap": comp_stats["ap"],
                "vf": comp_stats["vf"],
                "ikan": comp_stats["ikan"]
            })

        latest_row = monthly_series[-1]

        # Ringkasan 4 Kartu Eksekutif
        def make_summary(comp_key, name, full_name, bobot, color):
            c_data = latest_row[comp_key]
            yoy_now = c_data["yoy"]
            mtm_now = c_data["mtm"]

            if comp_key == "umum":
                is_target = 1.5 <= yoy_now <= 3.5
                is_above = yoy_now > 3.5
                status = "✅ Sasaran BI" if is_target else ("Di Atas Target" if is_above else "Di Bawah Target")
                status_cls = "bg-emerald-100 text-emerald-800 border-emerald-200" if is_target else ("bg-rose-100 text-rose-800 border-rose-200" if is_above else "bg-blue-100 text-blue-800 border-blue-200")
                trend_note = "▲ Tren Naik" if mtm_now > 0 else "▼ Terkendali"
                trend_cls = "text-rose-600" if mtm_now > 0 else "text-emerald-700"
            else:
                status = f"Bobot: {bobot:.2f}%"
                if comp_key == "ci":
                    status_cls = "bg-sky-100 text-sky-800 border-sky-200"
                    trend_note = f"Pilar Utama ({bobot:.1f}%)"
                    trend_cls = "text-sky-700 font-bold"
                elif comp_key == "ap":
                    status_cls = "bg-amber-100 text-amber-800 border-amber-200"
                    trend_note = "Tarif & Transportasi"
                    trend_cls = "text-amber-700 font-bold"
                else:
                    status_cls = "bg-rose-100 text-rose-800 border-rose-200"
                    trend_note = "Komponen Paling Bergejolak"
                    trend_cls = "text-rose-700 font-bold"

            return {
                "key": comp_key,
                "nama_singkat": name,
                "nama_lengkap": full_name,
                "bobot": bobot,
                "color_theme": color,
                "status": status,
                "status_cls": status_cls,
                "yoy_terkini": yoy_now,
                "mtm_terkini": mtm_now,
                "andil_yoy_terkini": c_data["andil_yoy"],
                "andil_mtm_terkini": c_data["andil_mtm"],
                "ihk_terkini": c_data["ihk"],
                "trend_note": trend_note,
                "trend_cls": trend_cls
            }

        kartu_ringkasan = [
            make_summary("umum", meta["nama_singkat"], f"IHK Umum {meta['nama']} (Headline)", 100.0, "indigo"),
            make_summary("ci", "INFLASI INTI (CI)", "Core Inflation (Inflasi Inti)", bobot_ci, "sky"),
            make_summary("ap", "HARGA PEMERINTAH (AP)", "Administered Prices (Harga Pemerintah)", bobot_ap, "amber"),
            make_summary("vf", "GEJOLAK PANGAN (VF)", "Volatile Food (Pangan Bergejolak)", bobot_vf, "rose")
        ]

        wilayah_dict[w_key] = {
            "id": w_key,
            "nama": meta["nama"],
            "nama_singkat": meta["nama_singkat"],
            "tipe": meta["tipe"],
            "deskripsi": meta["deskripsi"],
            "bobot_komponen": {
                "umum": 100.0,
                "ci": bobot_ci,
                "ap": bobot_ap,
                "vf": bobot_vf,
                "ikan_segar": bobot_ikan
            },
            "kartu_ringkasan": kartu_ringkasan,
            "deret_bulanan": monthly_series
        }

    # Root payload maintaining backward compatibility
    output_payload = {
        "metadata": {
            "judul": "Disagregasi Inflasi IHK Sulawesi Tenggara & 4 Kota IHK: CI, AP, dan VF",
            "sumber": "Badan Pusat Statistik (BPS) & Kertas Kerja Inflasi TD 2022_Project Integrasi_FPKP KPw BI Provinsi Sulawesi Tenggara",
            "periode": f"Januari 2024 - {latest_row['periode_str']}",
            "periode_terkini": f"{latest_row['bulan_singkat']} '{str(latest_row['tahun'])[2:]}",
            "periode_lengkap": latest_row['periode_str'],
            "bulan_angka_terkini": latest_row['bulan'],
            "tahun_terkini": latest_row['tahun'],
            "tahun_dasar": "2022 = 100",
            "daftar_wilayah": list(CITY_META.keys())
        },
        "wilayah": wilayah_dict,
        # Default backward compatible accessors (Sultra)
        "kartu_ringkasan": wilayah_dict["sultra"]["kartu_ringkasan"],
        "deret_bulanan": wilayah_dict["sultra"]["deret_bulanan"],
        "bobot_komponen": wilayah_dict["sultra"]["bobot_komponen"]
    }

    with open(OUT_JSON, "w", encoding="utf-8") as f:
        json.dump(output_payload, f, ensure_ascii=False, indent=2)

    print(f"[OK] Berhasil membuat dataset Disagregasi seluruh Kota IHK: {OUT_JSON}")

    if os.path.exists(ARTIFACT_DIR):
        artifact_out = os.path.join(ARTIFACT_DIR, "disagregasi_sultra_2024_2026.json")
        with open(artifact_out, "w", encoding="utf-8") as f:
            json.dump(output_payload, f, ensure_ascii=False, indent=2)
        print(f"[OK] Disalin ke Brain Artifact: {artifact_out}")

if __name__ == "__main__":
    main()
