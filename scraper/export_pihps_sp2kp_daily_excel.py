#!/usr/bin/env python3
"""
EXPORT DATA HARIAN PIHPS BANK INDONESIA & SP2KP KEMENDAG RI (2024 - 2026) KE EXCEL (.XLSX)
Menghasilkan dokumen Excel multi-sheet terstruktur dengan gaya profesional OpenXML
lengkap dengan metadata, tabel 10 komoditas utama, 31 seri rinci PIHPS, dan 17 Kab/Kota SP2KP.
"""

import os
import sys
import json
import zipfile
import io
import csv
import xml.sax.saxutils as saxutils
from datetime import datetime

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DATA_DIR = os.path.join(BASE_DIR, "data")
ARTIFACT_DIR = "/Users/regaprasetyo/.gemini/antigravity/brain/45b29b5e-87d9-439a-b46b-f9c22bf36c3e"

BI_DAILY_PATH = os.path.join(DATA_DIR, "bi_daily_2024_2026.json")
SP2KP_DAILY_PATH = os.path.join(DATA_DIR, "sp2kp_daily_sultra.json")

OUT_EXCEL_ROOT = os.path.join(BASE_DIR, "Data_Harian_PIHPS_dan_SP2KP_Sultra_2024_2026.xlsx")
OUT_EXCEL_DATA = os.path.join(DATA_DIR, "Data_Harian_PIHPS_dan_SP2KP_Sultra_2024_2026.xlsx")
OUT_EXCEL_ARTIFACT = os.path.join(ARTIFACT_DIR, "Data_Harian_PIHPS_dan_SP2KP_Sultra_2024_2026.xlsx")

OUT_CSV_PIHPS = os.path.join(BASE_DIR, "PIHPS_Harian_10_Komoditas_2024_2026.csv")
OUT_CSV_SP2KP = os.path.join(BASE_DIR, "SP2KP_Harian_17_KabKota_2024_2026.csv")

HARI_ID = ["Senin", "Selasa", "Rabu", "Kamis", "Jumat", "Sabtu", "Minggu"]
BULAN_ID = ["Januari", "Februari", "Maret", "April", "Mei", "Juni", "Juli", "Agustus", "September", "Oktober", "November", "Desember"]

KOMODITAS_10_ORDER = [
    "Beras",
    "Daging Ayam",
    "Daging Sapi",
    "Telur Ayam",
    "Bawang Merah",
    "Bawang Putih",
    "Cabai Merah",
    "Cabai Rawit",
    "Minyak Goreng",
    "Gula Pasir"
]

def col_letter(col_idx):
    """Konversi indeks kolom 1-based ke huruf Excel (1 -> A, 27 -> AA, 703 -> AAA)."""
    result = ""
    while col_idx > 0:
        col_idx, remainder = divmod(col_idx - 1, 26)
        result = chr(65 + remainder) + result
    return result

def escape_xml(s):
    if s is None:
        return ""
    return saxutils.escape(str(s))

def clean_num(val):
    """Konversi nilai harga ke integer, jika kosong return None."""
    if val is None or val == "" or val == "-":
        return None
    if isinstance(val, (int, float)):
        return int(round(val))
    s = str(val).replace(",", "").replace(".", "").strip()
    try:
        return int(s)
    except:
        return None

def parse_date_meta(d_str):
    try:
        p = d_str.split("/")
        d, m, y = int(p[0]), int(p[1]), int(p[2])
        dt = datetime(y, m, d)
        return {
            "hari": HARI_ID[dt.weekday()],
            "tahun": y,
            "bulan": BULAN_ID[m - 1],
            "sort_key": (y, m, d)
        }
    except Exception:
        return {"hari": "-", "tahun": 0, "bulan": "-", "sort_key": (0, 0, 0)}

def build_sheet_xml(sheet_data_rows, col_widths=None):
    """
    Membangun dokumen XML lembar kerja Excel (worksheet).
    sheet_data_rows: list of rows, di mana setiap row adalah list of cell tuples:
      (cell_value, cell_type, style_id)
      cell_type: 'inlineStr' | 'number' | 'formula'
    """
    xml = ['<?xml version="1.0" encoding="UTF-8" standalone="yes"?>']
    xml.append('<worksheet xmlns="http://schemas.openxmlformats.org/spreadsheetml/2006/main" xmlns:r="http://schemas.openxmlformats.org/officeDocument/2006/relationships">')
    
    xml.append('  <sheetViews>')
    xml.append('    <sheetView tabSelected="0" workbookViewId="0" showGridLines="1"/>')
    xml.append('  </sheetViews>')

    if col_widths:
        xml.append('  <cols>')
        for idx, width in enumerate(col_widths, 1):
            xml.append(f'    <col min="{idx}" max="{idx}" width="{width}" customWidth="1"/>')
        xml.append('  </cols>')
    
    xml.append('  <sheetData>')
    for row_idx, row in enumerate(sheet_data_rows, 1):
        if not row:
            xml.append(f'    <row r="{row_idx}"/>')
            continue
        xml.append(f'    <row r="{row_idx}">')
        for col_idx, cell in enumerate(row, 1):
            if cell is None:
                continue
            val, c_type, style_id = cell
            if val is None or val == "":
                continue
            cell_ref = f"{col_letter(col_idx)}{row_idx}"
            s_attr = f' s="{style_id}"' if style_id is not None else ''
            
            if c_type == 'inlineStr':
                xml.append(f'      <c r="{cell_ref}" t="inlineStr"{s_attr}><is><t>{escape_xml(val)}</t></is></c>')
            elif c_type == 'number':
                xml.append(f'      <c r="{cell_ref}"{s_attr}><v>{val}</v></c>')
            elif c_type == 'formula':
                xml.append(f'      <c r="{cell_ref}"{s_attr}><f>{escape_xml(val)}</f></c>')
        xml.append('    </row>')
    xml.append('  </sheetData>')
    xml.append('</worksheet>')
    return '\n'.join(xml)

def build_styles_xml():
    """Definisi gaya Excel (fonts, fills, borders, cell formats)."""
    return '''<?xml version="1.0" encoding="UTF-8" standalone="yes"?>
<styleSheet xmlns="http://schemas.openxmlformats.org/spreadsheetml/2006/main">
  <numFmts count="3">
    <numFmt numFmtId="164" formatCode="#,##0"/>
    <numFmt numFmtId="165" formatCode="0.00%"/>
    <numFmt numFmtId="166" formatCode="+0.00%;-0.00%;0.00%"/>
  </numFmts>
  <fonts count="6">
    <font><sz val="10"/><name val="Segoe UI"/><color rgb="FF1E293B"/></font>
    <font><b/><sz val="10"/><name val="Segoe UI"/><color rgb="FFFFFFFF"/></font>
    <font><b/><sz val="13"/><name val="Segoe UI"/><color rgb="FF0F172A"/></font>
    <font><i/><sz val="9.5"/><name val="Segoe UI"/><color rgb="FF64748B"/></font>
    <font><b/><sz val="10"/><name val="Segoe UI"/><color rgb="FF1E293B"/></font>
    <font><b/><sz val="10.5"/><name val="Segoe UI"/><color rgb="FF1E3A8A"/></font>
  </fonts>
  <fills count="5">
    <fill><patternFill patternType="none"/></fill>
    <fill><patternFill patternType="gray125"/></fill>
    <fill><patternFill patternType="solid"><fgColor rgb="FF1E3A8A"/></patternFill></fill>
    <fill><patternFill patternType="solid"><fgColor rgb="FFF1F5F9"/></patternFill></fill>
    <fill><patternFill patternType="solid"><fgColor rgb="FFE2E8F0"/></patternFill></fill>
  </fills>
  <borders count="2">
    <border><left/><right/><top/><bottom/><diagonal/></border>
    <border>
      <left style="thin"><color rgb="FFE2E8F0"/></left>
      <right style="thin"><color rgb="FFE2E8F0"/></right>
      <top style="thin"><color rgb="FFE2E8F0"/></top>
      <bottom style="thin"><color rgb="FFE2E8F0"/></bottom>
    </border>
  </borders>
  <cellStyleXfs count="1"><xf numFmtId="0" fontId="0" fillId="0" borderId="0"/></cellStyleXfs>
  <cellXfs count="11">
    <!-- 0: Standard left text, no border -->
    <xf numFmtId="0" fontId="0" fillId="0" borderId="0" xfId="0"/>
    <!-- 1: Header table: Navy blue, bold white, centered, bordered -->
    <xf numFmtId="0" fontId="1" fillId="2" borderId="1" xfId="0" applyFont="1" applyFill="1" applyBorder="1" applyAlignment="1"><alignment horizontal="center" vertical="center" wrapText="1"/></xf>
    <!-- 2: Integer currency number: #,##0, right aligned, bordered -->
    <xf numFmtId="164" fontId="0" fillId="0" borderId="1" xfId="0" applyNumberFormat="1" applyBorder="1" applyAlignment="1"><alignment horizontal="right" vertical="center"/></xf>
    <!-- 3: Percent 0.00%, right aligned, bordered -->
    <xf numFmtId="165" fontId="0" fillId="0" borderId="1" xfId="0" applyNumberFormat="1" applyBorder="1" applyAlignment="1"><alignment horizontal="right" vertical="center"/></xf>
    <!-- 4: Text left, thin border -->
    <xf numFmtId="0" fontId="0" fillId="0" borderId="1" xfId="0" applyBorder="1" applyAlignment="1"><alignment horizontal="left" vertical="center"/></xf>
    <!-- 5: Text center, thin border -->
    <xf numFmtId="0" fontId="0" fillId="0" borderId="1" xfId="0" applyBorder="1" applyAlignment="1"><alignment horizontal="center" vertical="center"/></xf>
    <!-- 6: Title: Bold 13pt Dark Slate -->
    <xf numFmtId="0" fontId="2" fillId="0" borderId="0" xfId="0" applyFont="1"/>
    <!-- 7: Subtitle: Italic 9.5pt Slate -->
    <xf numFmtId="0" fontId="3" fillId="0" borderId="0" xfId="0" applyFont="1"/>
    <!-- 8: Subheader / Category: Slate 100 fill, bold text, left, bordered -->
    <xf numFmtId="0" fontId="4" fillId="3" borderId="1" xfId="0" applyFont="1" applyFill="1" applyBorder="1" applyAlignment="1"><alignment horizontal="left" vertical="center"/></xf>
    <!-- 9: Section Header Title (Navy 10.5pt Bold) -->
    <xf numFmtId="0" fontId="5" fillId="0" borderId="0" xfId="0" applyFont="1"/>
    <!-- 10: Center Bold, bordered -->
    <xf numFmtId="0" fontId="4" fillId="0" borderId="1" xfId="0" applyFont="1" applyBorder="1" applyAlignment="1"><alignment horizontal="center" vertical="center"/></xf>
  </cellXfs>
</styleSheet>'''

def generate_excel():
    print("=" * 85)
    print("MEMBANGUN BUKU KERJA EXCEL RESMI HARGA PANGAN SULTRA (PIHPS BI & SP2KP KEMENDAG)")
    print(f"Waktu Eksekusi: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print("=" * 85)

    # 1. Muat Dataset PIHPS & SP2KP
    if not os.path.exists(BI_DAILY_PATH):
        raise FileNotFoundError(f"File tidak ditemukan: {BI_DAILY_PATH}")
    if not os.path.exists(SP2KP_DAILY_PATH):
        raise FileNotFoundError(f"File tidak ditemukan: {SP2KP_DAILY_PATH}")

    with open(BI_DAILY_PATH, "r", encoding="utf-8") as f:
        bi_json = json.load(f)

    with open(SP2KP_DAILY_PATH, "r", encoding="utf-8") as f:
        sp2kp_json = json.load(f)

    # Ekstraksi Tanggal & Komoditas PIHPS
    bi_rows = bi_json.get("data", [])
    bi_date_keys = [k for k in bi_rows[0].keys() if "/" in k]
    # Urutkan tanggal secara kronologis
    bi_date_keys.sort(key=lambda d: parse_date_meta(d)["sort_key"])

    # Map PIHPS Level 1 Komoditas
    bi_comm_map = {}
    for r in bi_rows:
        bi_comm_map[r["name"]] = r

    # Ekstraksi SP2KP
    sp2kp_harian = sp2kp_json.get("data_harian", {})
    sp2kp_kabs = sp2kp_json.get("kab_kota_list", [])
    sp2kp_prov = sp2kp_harian.get("Provinsi Sulawesi Tenggara (SP2KP)", {})
    
    # Ambil seluruh tanggal SP2KP dari provinsi atau kab pertama
    sp2kp_dates = set()
    for kab_name, comm_data in sp2kp_harian.items():
        for cn, date_dict in comm_data.items():
            sp2kp_dates.update(date_dict.keys())
    sp2kp_date_keys = sorted(list(sp2kp_dates), key=lambda d: parse_date_meta(d)["sort_key"])

    # -------------------------------------------------------------------------
    # SHEET 1: Ringkasan & Metadata
    # -------------------------------------------------------------------------
    s1_rows = []
    s1_rows.append([("DATA HARIAN HARGA PANGAN STRATEGIS SULAWESI TENGGARA (2024 - 2026)", "inlineStr", 6)])
    s1_rows.append([("Rekaman Deret Waktu Harian Hasil Scraping Portal Resmi PIHPS Bank Indonesia & SP2KP Kementerian Perdagangan RI", "inlineStr", 7)])
    s1_rows.append([])

    bi_last_meta = parse_date_meta(bi_date_keys[-1])
    bi_last_label = f"{int(bi_date_keys[-1].split('/')[0])} {bi_last_meta['bulan']} {bi_last_meta['tahun']}"
    sp2kp_last_meta = parse_date_meta(sp2kp_date_keys[-1])
    sp2kp_last_label = f"{int(sp2kp_date_keys[-1].split('/')[0])} {sp2kp_last_meta['bulan']} {sp2kp_last_meta['tahun']}"

    s1_rows.append([("I. METADATA & CAKUPAN PENGUMPULAN DATA", "inlineStr", 9)])
    meta_table = [
        ("Parameter", "Informasi Portal PIHPS Bank Indonesia", "Informasi Portal SP2KP Kemendag RI"),
        ("Tautan Portal Resmi", "https://www.bi.go.id/hargapangan", "https://sp2kp.kemendag.go.id"),
        ("Cakupan Wilayah", "Provinsi Sulawesi Tenggara (Pasar Tradisional Kendari & Baubau)", "17 Kabupaten/Kota Lengkap Se-Sulawesi Tenggara"),
        ("Periode Observasi", f"{bi_date_keys[0]} s.d. {bi_date_keys[-1]}", f"{sp2kp_date_keys[0]} s.d. {sp2kp_date_keys[-1]}"),
        ("Jumlah Titik Observasi", f"{len(bi_date_keys)} Hari Kerja Resmi", f"{len(sp2kp_date_keys)} Hari Pemantauan Pasar"),
        ("Jumlah Komoditas Utama", "10 Komoditas Strategis Nasional (Level 1)", "10 Komoditas Pangan Pokok Diselaraskan"),
        ("Rincian Varian Kualitas", "21 Varian Rinci Kualitas (Level 2) - Total 31 Seri", "18 Varian Komoditas SP2KP Terkonsolidasi"),
        ("Waktu Pemutakhiran", f"Rilis Harian Terkini: {bi_last_label}", f"Rilis Harian Terkini: {sp2kp_last_label}"),
        ("Metodologi Sampling", "Survei Harian Pasar Tradisional Terpilih Bank Indonesia", "Sistem Pemantauan Harga Pasar Kemendag RI di 17 Daerah")
    ]
    for idx, row in enumerate(meta_table):
        st = 1 if idx == 0 else 4
        s1_rows.append([(row[0], "inlineStr", 8 if idx > 0 else 1), (row[1], "inlineStr", st), (row[2], "inlineStr", st)])
    
    s1_rows.append([])
    s1_rows.append([(f"II. KOMPARASI HARGA TERKINI ({bi_last_label.upper()})", "inlineStr", 9)])
    comp_header = ["No", "Komoditas", "Satuan", "Harga PIHPS Sultra (Rp)", "Harga Rata-rata SP2KP Sultra (Rp)", "Selisih Nominal (Rp)", "Disparitas (%)"]
    s1_rows.append([(h, "inlineStr", 1) for h in comp_header])

    target_date = bi_date_keys[-1] # 04/11/2026
    for no, cn in enumerate(KOMODITAS_10_ORDER, 1):
        p_row = bi_comm_map.get(cn, {})
        p_val = clean_num(p_row.get(target_date))
        sp_val = sp2kp_prov.get(cn, {}).get(target_date)
        if sp_val is None:
            # fallback ke tanggal terdekat jika kosong
            for rev_d in reversed(sp2kp_date_keys):
                if rev_d in sp2kp_prov.get(cn, {}):
                    sp_val = sp2kp_prov[cn][rev_d]
                    break
        satuan = "liter" if cn == "Minyak Goreng" else "kg"
        diff_val = (p_val - sp_val) if (p_val is not None and sp_val is not None) else 0
        disp_pct = (diff_val / sp_val) if (sp_val and sp_val > 0) else 0.0

        s1_rows.append([
            (no, "number", 5),
            (cn, "inlineStr", 4),
            (satuan, "inlineStr", 5),
            (p_val, "number", 2),
            (sp_val, "number", 2),
            (diff_val, "number", 2),
            (disp_pct, "number", 3)
        ])

    s1_col_widths = [26, 42, 42, 22, 22, 20, 16]
    sheet1_xml = build_sheet_xml(s1_rows, s1_col_widths)

    # -------------------------------------------------------------------------
    # SHEET 2: PIHPS - 10 Komoditas Harian
    # -------------------------------------------------------------------------
    s2_rows = []
    s2_rows.append([("DERET WAKTU HARIAN HARGA PANGAN PIHPS BANK INDONESIA (2024 - 2026)", "inlineStr", 6)])
    s2_rows.append([(f"Wilayah: Provinsi Sulawesi Tenggara (Pasar Tradisional) | Periode: {bi_date_keys[0]} s.d. {bi_date_keys[-1]} ({len(bi_date_keys)} Hari Kerja)", "inlineStr", 7)])
    s2_rows.append([])

    s2_headers = ["No", "Tanggal", "Hari", "Tahun", "Bulan"] + [f"{c} (Rp)" for c in KOMODITAS_10_ORDER]
    s2_rows.append([(h, "inlineStr", 1) for h in s2_headers])

    csv_pihps_rows = [["Tanggal", "Hari", "Tahun", "Bulan"] + KOMODITAS_10_ORDER]

    for no, d_str in enumerate(bi_date_keys, 1):
        d_meta = parse_date_meta(d_str)
        row_vals = [
            (no, "number", 5),
            (d_str, "inlineStr", 5),
            (d_meta["hari"], "inlineStr", 5),
            (d_meta["tahun"], "number", 5),
            (d_meta["bulan"], "inlineStr", 5)
        ]
        csv_row = [d_str, d_meta["hari"], d_meta["tahun"], d_meta["bulan"]]
        for cn in KOMODITAS_10_ORDER:
            c_data = bi_comm_map.get(cn, {})
            num = clean_num(c_data.get(d_str))
            row_vals.append((num, "number", 2) if num is not None else ("", "inlineStr", 5))
            csv_row.append(num if num is not None else "")
        s2_rows.append(row_vals)
        csv_pihps_rows.append(csv_row)

    s2_col_widths = [6, 13, 11, 8, 14] + [16 for _ in KOMODITAS_10_ORDER]
    sheet2_xml = build_sheet_xml(s2_rows, s2_col_widths)

    # -------------------------------------------------------------------------
    # SHEET 3: PIHPS - Matriks 31 Seri Rinci
    # -------------------------------------------------------------------------
    s3_rows = []
    s3_rows.append([("MATRIKS HARIAN 31 KOMODITAS & VARIAN RINCI PIHPS SULTRA (2024 - 2026)", "inlineStr", 6)])
    s3_rows.append([(f"Mencakup 10 Komoditas Utama (Level 1) dan 21 Varian Rinci Kualitas (Level 2) - {len(bi_date_keys)} Kolom Tanggal", "inlineStr", 7)])
    s3_rows.append([])

    s3_headers = ["No", "Komoditas / Varian", "Level"] + bi_date_keys
    s3_rows.append([(h, "inlineStr", 1) for h in s3_headers])

    for no, r in enumerate(bi_rows, 1):
        lvl = r.get("level", 1)
        name = r.get("name", "")
        style_title = 8 if lvl == 1 else 4
        row_vals = [
            (no, "number", 5),
            (name, "inlineStr", style_title),
            (f"Level {lvl}", "inlineStr", 5)
        ]
        for d_str in bi_date_keys:
            num = clean_num(r.get(d_str))
            row_vals.append((num, "number", 2) if num is not None else ("", "inlineStr", 5))
        s3_rows.append(row_vals)

    s3_col_widths = [6, 32, 10] + [12 for _ in bi_date_keys]
    sheet3_xml = build_sheet_xml(s3_rows, s3_col_widths)

    # -------------------------------------------------------------------------
    # SHEET 4: SP2KP - Rata-rata Provinsi Harian
    # -------------------------------------------------------------------------
    s4_rows = []
    s4_rows.append([("DERET WAKTU HARIAN HARGA PANGAN SP2KP KEMENDAG RI - PROVINSI SULTRA (2024 - 2026)", "inlineStr", 6)])
    s4_rows.append([(f"Rata-rata 17 Kabupaten/Kota Se-Sulawesi Tenggara | Periode: {sp2kp_date_keys[0]} s.d. {sp2kp_date_keys[-1]} ({len(sp2kp_date_keys)} Hari Observasi)", "inlineStr", 7)])
    s4_rows.append([])

    s4_headers = ["No", "Tanggal", "Hari", "Tahun", "Bulan"] + [f"{c} (Rp)" for c in KOMODITAS_10_ORDER]
    s4_rows.append([(h, "inlineStr", 1) for h in s4_headers])

    for no, d_str in enumerate(sp2kp_date_keys, 1):
        d_meta = parse_date_meta(d_str)
        row_vals = [
            (no, "number", 5),
            (d_str, "inlineStr", 5),
            (d_meta["hari"], "inlineStr", 5),
            (d_meta["tahun"], "number", 5),
            (d_meta["bulan"], "inlineStr", 5)
        ]
        for cn in KOMODITAS_10_ORDER:
            num = sp2kp_prov.get(cn, {}).get(d_str)
            row_vals.append((num, "number", 2) if num is not None else ("", "inlineStr", 5))
        s4_rows.append(row_vals)

    s4_col_widths = [6, 13, 11, 8, 14] + [16 for _ in KOMODITAS_10_ORDER]
    sheet4_xml = build_sheet_xml(s4_rows, s4_col_widths)

    # -------------------------------------------------------------------------
    # SHEET 5: SP2KP - 17 Kab-Kota (Database Tabular)
    # -------------------------------------------------------------------------
    s5_rows = []
    s5_rows.append([("DATABASE HARIAN HARGA PANGAN SP2KP 17 KABUPATEN/KOTA SULTRA (2024 - 2026)", "inlineStr", 6)])
    s5_rows.append([("Data Siap Analisis Pivot: Tanggal x Kabupaten/Kota x 10 Komoditas Strategis Nasional", "inlineStr", 7)])
    s5_rows.append([])

    s5_headers = ["Tanggal", "Hari", "Tahun", "Bulan", "Kabupaten/Kota"] + [f"{c} (Rp)" for c in KOMODITAS_10_ORDER]
    s5_rows.append([(h, "inlineStr", 1) for h in s5_headers])

    csv_sp2kp_rows = [["Tanggal", "Hari", "Tahun", "Bulan", "Kabupaten_Kota"] + KOMODITAS_10_ORDER]

    # Hanya 17 kab/kota murni (tanpa rata-rata provinsi untuk menjaga data atomic)
    for d_str in sp2kp_date_keys:
        d_meta = parse_date_meta(d_str)
        for kab in sp2kp_kabs:
            kab_data = sp2kp_harian.get(kab, {})
            # Cek apakah tanggal ini ada setidaknya 1 komoditas
            has_price = any(kab_data.get(cn, {}).get(d_str) for cn in KOMODITAS_10_ORDER)
            if not has_price:
                continue

            row_vals = [
                (d_str, "inlineStr", 5),
                (d_meta["hari"], "inlineStr", 5),
                (d_meta["tahun"], "number", 5),
                (d_meta["bulan"], "inlineStr", 5),
                (kab, "inlineStr", 4)
            ]
            csv_row = [d_str, d_meta["hari"], d_meta["tahun"], d_meta["bulan"], kab]
            for cn in KOMODITAS_10_ORDER:
                num = kab_data.get(cn, {}).get(d_str)
                row_vals.append((num, "number", 2) if num is not None else ("", "inlineStr", 5))
                csv_row.append(num if num is not None else "")
            s5_rows.append(row_vals)
            csv_sp2kp_rows.append(csv_row)

    s5_col_widths = [13, 11, 8, 14, 25] + [15 for _ in KOMODITAS_10_ORDER]
    sheet5_xml = build_sheet_xml(s5_rows, s5_col_widths)

    # -------------------------------------------------------------------------
    # PAKET ZIP WORKBOOK (.XLSX)
    # -------------------------------------------------------------------------
    content_types_xml = '''<?xml version="1.0" encoding="UTF-8" standalone="yes"?>
<Types xmlns="http://schemas.openxmlformats.org/package/2006/content-types">
  <Default Extension="rels" ContentType="application/vnd.openxmlformats-package.relationships+xml"/>
  <Default Extension="xml" ContentType="application/xml"/>
  <Override PartName="/xl/workbook.xml" ContentType="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet.main+xml"/>
  <Override PartName="/xl/worksheets/sheet1.xml" ContentType="application/vnd.openxmlformats-officedocument.spreadsheetml.worksheet+xml"/>
  <Override PartName="/xl/worksheets/sheet2.xml" ContentType="application/vnd.openxmlformats-officedocument.spreadsheetml.worksheet+xml"/>
  <Override PartName="/xl/worksheets/sheet3.xml" ContentType="application/vnd.openxmlformats-officedocument.spreadsheetml.worksheet+xml"/>
  <Override PartName="/xl/worksheets/sheet4.xml" ContentType="application/vnd.openxmlformats-officedocument.spreadsheetml.worksheet+xml"/>
  <Override PartName="/xl/worksheets/sheet5.xml" ContentType="application/vnd.openxmlformats-officedocument.spreadsheetml.worksheet+xml"/>
  <Override PartName="/xl/styles.xml" ContentType="application/vnd.openxmlformats-officedocument.spreadsheetml.styles+xml"/>
</Types>'''

    rels_xml = '''<?xml version="1.0" encoding="UTF-8" standalone="yes"?>
<Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships">
  <Relationship Id="rId1" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/officeDocument" Target="xl/workbook.xml"/>
</Relationships>'''

    wb_rels_xml = '''<?xml version="1.0" encoding="UTF-8" standalone="yes"?>
<Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships">
  <Relationship Id="rId1" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/worksheet" Target="worksheets/sheet1.xml"/>
  <Relationship Id="rId2" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/worksheet" Target="worksheets/sheet2.xml"/>
  <Relationship Id="rId3" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/worksheet" Target="worksheets/sheet3.xml"/>
  <Relationship Id="rId4" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/worksheet" Target="worksheets/sheet4.xml"/>
  <Relationship Id="rId5" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/worksheet" Target="worksheets/sheet5.xml"/>
  <Relationship Id="rId6" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/styles" Target="styles.xml"/>
</Relationships>'''

    workbook_xml = '''<?xml version="1.0" encoding="UTF-8" standalone="yes"?>
<workbook xmlns="http://schemas.openxmlformats.org/spreadsheetml/2006/main" xmlns:r="http://schemas.openxmlformats.org/officeDocument/2006/relationships">
  <sheets>
    <sheet name="Ringkasan &amp; Metadata" sheetId="1" r:id="rId1"/>
    <sheet name="PIHPS - 10 Komoditas Utama" sheetId="2" r:id="rId2"/>
    <sheet name="PIHPS - 31 Seri Rinci" sheetId="3" r:id="rId3"/>
    <sheet name="SP2KP - Rata-rata Sultra" sheetId="4" r:id="rId4"/>
    <sheet name="SP2KP - 17 Kab-Kota" sheetId="5" r:id="rId5"/>
  </sheets>
</workbook>'''

    buf = io.BytesIO()
    with zipfile.ZipFile(buf, "w", zipfile.ZIP_DEFLATED) as z:
        z.writestr("[Content_Types].xml", content_types_xml)
        z.writestr("_rels/.rels", rels_xml)
        z.writestr("xl/_rels/workbook.xml.rels", wb_rels_xml)
        z.writestr("xl/workbook.xml", workbook_xml)
        z.writestr("xl/styles.xml", build_styles_xml())
        z.writestr("xl/worksheets/sheet1.xml", sheet1_xml)
        z.writestr("xl/worksheets/sheet2.xml", sheet2_xml)
        z.writestr("xl/worksheets/sheet3.xml", sheet3_xml)
        z.writestr("xl/worksheets/sheet4.xml", sheet4_xml)
        z.writestr("xl/worksheets/sheet5.xml", sheet5_xml)

    excel_bytes = buf.getvalue()

    # Simpan ke target lokasi
    targets = [OUT_EXCEL_ROOT, OUT_EXCEL_DATA, OUT_EXCEL_ARTIFACT]
    for target in targets:
        os.makedirs(os.path.dirname(target), exist_ok=True)
        with open(target, "wb") as f:
            f.write(excel_bytes)
        print(f"✓ Berkas Excel tersimpan di: {target} ({len(excel_bytes)/1024:.1f} KB)")

    # Simpan CSV Companion
    with open(OUT_CSV_PIHPS, "w", encoding="utf-8", newline="") as f:
        writer = csv.writer(f)
        writer.writerows(csv_pihps_rows)
    print(f"✓ Berkas CSV PIHPS tersimpan di: {OUT_CSV_PIHPS} ({len(csv_pihps_rows)-1} baris)")

    with open(OUT_CSV_SP2KP, "w", encoding="utf-8", newline="") as f:
        writer = csv.writer(f)
        writer.writerows(csv_sp2kp_rows)
    print(f"✓ Berkas CSV SP2KP tersimpan di: {OUT_CSV_SP2KP} ({len(csv_sp2kp_rows)-1} baris)")

    print("\n[SUKSES] Seluruh berkas ekspor harian PIHPS & SP2KP berhasil dibangun!")
    return True

if __name__ == "__main__":
    generate_excel()
