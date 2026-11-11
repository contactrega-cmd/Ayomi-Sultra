#!/usr/bin/env python3
"""
Ekstraksi Data Lengkap 5 Komoditas Penyumbang & Penahan Inflasi (MtM & YoY)
Per Bulan untuk Seluruh Wilayah IHK (Sultra, Kendari, Baubau, Kolaka, Konawe)
dari Kertas Kerja Excel FPKP BI Sulawesi Tenggara (2024-2026).
Sumber: Sheet 'andil mtm' dan 'andil yoy' dari Jangan Diotakatik Kertas Kerja Inflasi TD 2022_Project Integrasi_FPKP ok.xlsx
"""

import os
import json
import zipfile
import xml.etree.ElementTree as ET

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DATA_DIR = os.path.join(BASE_DIR, "data")
SRC_EXCEL = os.path.join(BASE_DIR, "Jangan Diotakatik Kertas Kerja Inflasi TD 2022_Project Integrasi_FPKP ok.xlsx")
OUT_JSON = os.path.join(DATA_DIR, "andil_komoditas_bulanan_sultra.json")
ARTIFACT_DIR = "/Users/regaprasetyo/.gemini/antigravity/brain/45b29b5e-87d9-439a-b46b-f9c22bf36c3e"

MONTH_NAMES_ID = [
    "", "Januari", "Februari", "Maret", "April", "Mei", "Juni",
    "Juli", "Agustus", "September", "Oktober", "November", "Desember"
]

CITIES_MAP = {
    "sultra": {"excel_key": "SULTRA", "nama": "Provinsi Sulawesi Tenggara"},
    "kendari": {"excel_key": "KENDARI", "nama": "Kota Kendari"},
    "baubau": {"excel_key": "BAUBAU", "nama": "Kota Baubau"},
    "kolaka": {"excel_key": "KOLAKA", "nama": "Kabupaten Kolaka"},
    "konawe": {"excel_key": "KONAWE", "nama": "Kabupaten Konawe"}
}

def clean_komoditas_name(name):
    if not name:
        return ""
    aliases = {
        "AKADEMI/PERGURUAN TINGGI": "PENDIDIKAN TINGGI",
        "IKAN BANDENG/IKAN BOLU": "IKAN BANDENG / IKAN BOLU",
        "IKAN CAKALANG/ IKAN SISIK": "IKAN CAKALANG",
        "IKAN SELAR/ IKAN TUDE": "IKAN SELAR",
        "IKAN KEMBUNG/IKAN GEMBUNG/ IKAN BANYAR/IKAN GEMBOLO/ IKAN ASO-ASO": "IKAN KEMBUNG",
        "IKAN LAYANG/ IKAN BENGGOL": "IKAN LAYANG",
        "POPOK BAYI SEKALI PAKAI/ DIAPERS": "POPOK BAYI",
        "BAWANG MERAH": "BAWANG MERAH",
        "BAWANG PUTIH": "BAWANG PUTIH",
        "CABAI MERAH": "CABAI MERAH",
        "CABAI RAWIT": "CABAI RAWIT",
        "MINYAK GORENG": "MINYAK GORENG",
        "BERAS": "BERAS",
        "TELUR AYAM RAS": "TELUR AYAM RAS",
        "DAGING AYAM RAS": "DAGING AYAM RAS",
        "DAGING SAPI": "DAGING SAPI",
        "GULA PASIR": "GULA PASIR",
        "TOMAT": "TOMAT"
    }
    return aliases.get(name.strip(), name.strip())

def main():
    if not os.path.exists(SRC_EXCEL):
        print(f"File {SRC_EXCEL} tidak ditemukan!")
        return

    print("Mengekstrak data bulanan komoditas penyumbang/penahan inflasi per kota IHK dari Excel...")
    with zipfile.ZipFile(SRC_EXCEL, "r") as z:
        wb_xml = z.read("xl/workbook.xml")
        root = ET.fromstring(wb_xml)
        
        rels_xml = z.read("xl/_rels/workbook.xml.rels")
        root_rels = ET.fromstring(rels_xml)
        rel_map = {}
        for r in root_rels:
            r_id = r.attrib.get("Id")
            r_target = r.attrib.get("Target")
            if r_id and r_target:
                rel_map[r_id] = r_target

        shared_strings = []
        if "xl/sharedStrings.xml" in z.namelist():
            ss_root = ET.fromstring(z.read("xl/sharedStrings.xml"))
            for si in ss_root.findall(".//{http://schemas.openxmlformats.org/spreadsheetml/2006/main}si"):
                t = si.find(".//{http://schemas.openxmlformats.org/spreadsheetml/2006/main}t")
                shared_strings.append(t.text if t is not None else "")

        def get_val(c):
            t = c.attrib.get("t")
            v = c.find("{http://schemas.openxmlformats.org/spreadsheetml/2006/main}v")
            val = v.text if v is not None else ""
            if t == "s" and val.isdigit() and int(val) < len(shared_strings):
                return shared_strings[int(val)]
            return val

        def parse_sheet_data(sheet_name):
            s_el = None
            for s in root.iter("{http://schemas.openxmlformats.org/spreadsheetml/2006/main}sheet"):
                if s.attrib.get("name") == sheet_name:
                    s_el = s
                    break
            if s_el is None:
                print(f"Sheet {sheet_name} tidak ditemukan!")
                return [], {}

            r_id = s_el.attrib.get("{http://schemas.openxmlformats.org/officeDocument/2006/relationships}id")
            target = rel_map.get(r_id, "")
            zip_target = target if target.startswith("xl/") else "xl/" + target
            s_data = ET.fromstring(z.read(zip_target))

            rows = s_data.findall(".//{http://schemas.openxmlformats.org/spreadsheetml/2006/main}row")
            if len(rows) < 3:
                return [], {}

            r1 = {c.attrib.get("r"): get_val(c) for c in rows[0].findall("{http://schemas.openxmlformats.org/spreadsheetml/2006/main}c")}
            r2 = {c.attrib.get("r"): get_val(c) for c in rows[1].findall("{http://schemas.openxmlformats.org/spreadsheetml/2006/main}c")}

            col_map = []
            for cell_ref, val in r1.items():
                col = "".join(filter(str.isalpha, cell_ref))
                m_val = r2.get(f"{col}2", "")
                if str(val) in ["2024", "2025", "2026"] and str(m_val).isdigit():
                    col_map.append((col, int(val), int(m_val)))
            col_map.sort(key=lambda x: (x[1], x[2]))

            # commodity_rows grouped by city
            commodity_rows_by_city = {k: [] for k in CITIES_MAP.keys()}
            for r in rows[2:]:
                cells = {c.attrib.get("r"): get_val(c) for c in r.findall("{http://schemas.openxmlformats.org/spreadsheetml/2006/main}c")}
                r_num = r.attrib.get("r")
                raw_kota = cells.get(f"B{r_num}", "").strip().upper()
                
                # Match city key
                city_key = None
                for ckey, cmeta in CITIES_MAP.items():
                    if cmeta["excel_key"] == raw_kota:
                        city_key = ckey
                        break
                if not city_key:
                    continue

                kode = cells.get(f"E{r_num}", "").strip()
                if kode and len(kode) == 7 and not kode.endswith("0000") and not kode.endswith("000"):
                    nama = cells.get(f"H{r_num}", "").strip()
                    komp = cells.get(f"G{r_num}", "").strip()
                    vals_per_col = {}
                    for col, y, m in col_map:
                        v_str = cells.get(f"{col}{r_num}", "")
                        try:
                            vals_per_col[(y, m)] = float(v_str)
                        except:
                            vals_per_col[(y, m)] = None
                    commodity_rows_by_city[city_key].append({
                        "kode": kode,
                        "nama": nama,
                        "komponen": komp,
                        "vals": vals_per_col
                    })

            return col_map, commodity_rows_by_city

        cols_mtm, rows_by_city_mtm = parse_sheet_data("andil mtm")
        cols_yoy, rows_by_city_yoy = parse_sheet_data("andil yoy")
        print(f"Kolom ditemukan: {len(cols_mtm)} periode bulanan.")

        # Master classification lookup from SULTRA (andil mtm)
        master_komp_map = {}
        for r in rows_by_city_mtm.get("sultra", []):
            if r["komponen"] in ["CI", "AP", "VF"]:
                master_komp_map[r["kode"]] = r["komponen"]

        timeline = sorted(list(set([(c[1], c[2]) for c in cols_mtm])))

        wilayah_payload = {}

        for ckey, cmeta in CITIES_MAP.items():
            rows_mtm = rows_by_city_mtm.get(ckey, [])
            rows_yoy = rows_by_city_yoy.get(ckey, [])

            monthly_records = []
            for y, m in timeline:
                p_str = f"{MONTH_NAMES_ID[m]} {y}"

                # 1. MTM Top 5 & Bottom 5
                items_mtm = []
                for r in rows_mtm:
                    v = r["vals"].get((y, m))
                    if v is not None:
                        komp = master_komp_map.get(r["kode"], r["komponen"])
                        if komp not in ["CI", "AP", "VF"]:
                            komp = r["komponen"]
                        items_mtm.append({
                            "kode": r["kode"],
                            "komoditas": clean_komoditas_name(r["nama"]),
                            "nama_asli": r["nama"],
                            "komponen": komp,
                            "andil": round(v, 2),
                            "andil_raw": v
                        })
                items_mtm.sort(key=lambda x: x["andil_raw"], reverse=True)
                top5_mtm = items_mtm[:5]
                bot5_mtm = sorted(items_mtm[-5:], key=lambda x: x["andil_raw"])

                # 2. YOY Top 5 & Bottom 5
                items_yoy = []
                for r in rows_yoy:
                    v = r["vals"].get((y, m))
                    if v is not None:
                        komp = master_komp_map.get(r["kode"], r["komponen"])
                        if komp not in ["CI", "AP", "VF"]:
                            komp = r["komponen"]
                        items_yoy.append({
                            "kode": r["kode"],
                            "komoditas": clean_komoditas_name(r["nama"]),
                            "nama_asli": r["nama"],
                            "komponen": komp,
                            "andil": round(v, 2),
                            "andil_raw": v
                        })
                items_yoy.sort(key=lambda x: x["andil_raw"], reverse=True)
                top5_yoy = items_yoy[:5]
                bot5_yoy = sorted(items_yoy[-5:], key=lambda x: x["andil_raw"])

                monthly_records.append({
                    "periode_str": p_str,
                    "tahun": y,
                    "bulan": m,
                    "penyumbang_mtm": top5_mtm,
                    "penahan_mtm": bot5_mtm,
                    "penyumbang_yoy": top5_yoy,
                    "penahan_yoy": bot5_yoy
                })

            wilayah_payload[ckey] = {
                "nama": cmeta["nama"],
                "total_bulan": len(monthly_records),
                "data_bulanan": monthly_records
            }
            print(f"  {ckey.upper()}: {len(rows_mtm)} komoditas, {len(monthly_records)} periode bulanan berhasil diproses.")

    payload = {
        "updated_period": "September 2026",
        "total_bulan": len(timeline),
        "data_bulanan": wilayah_payload["sultra"]["data_bulanan"], # Backward compatibility
        "wilayah": wilayah_payload
    }

    with open(OUT_JSON, "w", encoding="utf-8") as f:
        json.dump(payload, f, ensure_ascii=False, indent=2)

    # Copy to brain artifact
    artifact_json = os.path.join(ARTIFACT_DIR, "andil_komoditas_bulanan_sultra.json")
    with open(artifact_json, "w", encoding="utf-8") as f:
        json.dump(payload, f, ensure_ascii=False, indent=2)

    print(f"Berhasil menyimpan andil komoditas seluruh kota ke {OUT_JSON} dan {artifact_json}!")

if __name__ == "__main__":
    main()
