#!/usr/bin/env python3
"""
Ekspor Laporan Perkembangan Inflasi Volatile Food (VF) Sultra 2024-2026
ke format Excel (.xlsx) murni Python (ZIP + XML)
"""

import os
import sys
import zipfile
import xml.etree.ElementTree as ET

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SRC_EXCEL = os.path.join(BASE_DIR, "Jangan Diotakatik Kertas Kerja Inflasi TD 2022_Project Integrasi_FPKP ok.xlsx")
OUT_EXCEL = os.path.join(BASE_DIR, "laporan_inflasi_volatile_food_sultra_2024_2026.xlsx")
ARTIFACT_DIR = "/Users/regaprasetyo/.gemini/antigravity/brain/45b29b5e-87d9-439a-b46b-f9c22bf36c3e"

def create_excel(sheets_data, out_path):
    sheet_xmls = {}
    content_types = [
        '<?xml version="1.0" encoding="UTF-8" standalone="yes"?>',
        '<Types xmlns="http://schemas.openxmlformats.org/package/2006/content-types">',
        '  <Default Extension="rels" ContentType="application/vnd.openxmlformats-package.relationships+xml"/>',
        '  <Default Extension="xml" ContentType="application/xml"/>',
        '  <Override PartName="/xl/workbook.xml" ContentType="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet.main+xml"/>',
        '  <Override PartName="/xl/styles.xml" ContentType="application/vnd.openxmlformats-officedocument.spreadsheetml.styles+xml"/>'
    ]
    wb_sheets = []
    wb_rels = [
        '<?xml version="1.0" encoding="UTF-8" standalone="yes"?>',
        '<Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships">',
        '  <Relationship Id="rIdStyles" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/styles" Target="styles.xml"/>'
    ]

    for idx, (s_name, rows) in enumerate(sheets_data.items(), 1):
        content_types.append(f'  <Override PartName="/xl/worksheets/sheet{idx}.xml" ContentType="application/vnd.openxmlformats-officedocument.spreadsheetml.worksheet+xml"/>')
        wb_sheets.append(f'    <sheet name="{s_name}" sheetId="{idx}" r:id="rIdSheet{idx}"/>')
        wb_rels.append(f'  <Relationship Id="rIdSheet{idx}" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/worksheet" Target="worksheets/sheet{idx}.xml"/>')

        xml_lines = [
            '<?xml version="1.0" encoding="UTF-8" standalone="yes"?>',
            '<worksheet xmlns="http://schemas.openxmlformats.org/spreadsheetml/2006/main">',
            '  <sheetData>'
        ]
        for r_i, r_data in enumerate(rows, 1):
            xml_lines.append(f'    <row r="{r_i}">')
            for c_i, val in enumerate(r_data, 1):
                col_letter = ""
                n = c_i
                while n > 0:
                    n, rem = divmod(n - 1, 26)
                    col_letter = chr(65 + rem) + col_letter
                cell_ref = f"{col_letter}{r_i}"

                if isinstance(val, (int, float)):
                    xml_lines.append(f'      <c r="{cell_ref}"><v>{val}</v></c>')
                else:
                    v_str = str(val or "").replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")
                    xml_lines.append(f'      <c r="{cell_ref}" t="inlineStr"><is><t>{v_str}</t></is></c>')
            xml_lines.append('    </row>')
        xml_lines.append('  </sheetData>')
        xml_lines.append('</worksheet>')
        sheet_xmls[f"xl/worksheets/sheet{idx}.xml"] = "\n".join(xml_lines)

    content_types.append('</Types>')
    wb_rels.append('</Relationships>')

    workbook_xml = '\n'.join([
        '<?xml version="1.0" encoding="UTF-8" standalone="yes"?>',
        '<workbook xmlns="http://schemas.openxmlformats.org/spreadsheetml/2006/main" xmlns:r="http://schemas.openxmlformats.org/officeDocument/2006/relationships">',
        '  <sheets>',
        *wb_sheets,
        '  </sheets>',
        '</workbook>'
    ])

    styles_xml = """<?xml version="1.0" encoding="UTF-8" standalone="yes"?>
<styleSheet xmlns="http://schemas.openxmlformats.org/spreadsheetml/2006/main">
  <fonts count="1"><font><sz val="11"/><name val="Calibri"/></font></fonts>
  <fills count="2"><fill><patternFill patternType="none"/></fill><fill><patternFill patternType="gray125"/></fill></fills>
  <borders count="1"><border><left/><right/><top/><bottom/></border></borders>
  <cellStyleXfs count="1"><xf numFmtId="0" fontId="0" fillId="0" borderId="0"/></cellStyleXfs>
  <cellXfs count="1"><xf numFmtId="0" fontId="0" fillId="0" borderId="0" xfId="0"/></cellXfs>
</styleSheet>"""

    root_rels = """<?xml version="1.0" encoding="UTF-8" standalone="yes"?>
<Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships">
  <Relationship Id="rId1" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/officeDocument" Target="xl/workbook.xml"/>
</Relationships>"""

    with zipfile.ZipFile(out_path, "w", zipfile.ZIP_DEFLATED) as z:
        z.writestr("[Content_Types].xml", "\n".join(content_types))
        z.writestr("_rels/.rels", root_rels)
        z.writestr("xl/workbook.xml", workbook_xml)
        z.writestr("xl/_rels/workbook.xml.rels", "\n".join(wb_rels))
        z.writestr("xl/styles.xml", styles_xml)
        for p, sxml in sheet_xmls.items():
            z.writestr(p, sxml)

def main():
    print("Mengekstrak data dari Kertas Kerja FPKP BI...")
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

        # 1. Klasifikasi VF
        s_klas = ET.fromstring(z.read("xl/" + rel_map[next(s.attrib["{http://schemas.openxmlformats.org/officeDocument/2006/relationships}id"] for s in root.findall(".//m:sheet", ns) if s.attrib["name"] == "Klasifikasi")]))
        vf_codes = set()
        for r in s_klas.findall(".//m:row", ns)[2:]:
            cells = {}
            for c in r.findall("m:c", ns):
                cells["".join(filter(str.isalpha, c.attrib.get("r")))] = get_val(c)
            if cells.get("H", "") == "1" and cells.get("E", ""):
                vf_codes.add(cells.get("E", ""))

        # 2. Bobot
        s_bobot = ET.fromstring(z.read("xl/" + rel_map[next(s.attrib["{http://schemas.openxmlformats.org/officeDocument/2006/relationships}id"] for s in root.findall(".//m:sheet", ns) if s.attrib["name"] == "Bobot")]))
        weights = {}
        for r in s_bobot.findall(".//m:row", ns)[4:]:
            cells = {}
            for c in r.findall("m:c", ns):
                cells["".join(filter(str.isalpha, c.attrib.get("r")))] = get_val(c)
            if cells.get("B", "") == "SULTRA" and cells.get("E", "") in vf_codes:
                code = cells.get("E", "")
                name = cells.get("F", "")
                try: w_val = float(cells.get("AF", "0"))
                except: w_val = 0.0
                weights[code] = {"nama": name, "bobot_ihk": w_val}

        total_w_vf = sum(x["bobot_ihk"] for x in weights.values())
        for cd in weights:
            weights[cd]["porsi_vf"] = (weights[cd]["bobot_ihk"] / total_w_vf * 100) if total_w_vf else 0

        # 3. Sheet mtm
        s_mtm = ET.fromstring(z.read("xl/" + rel_map[next(s.attrib["{http://schemas.openxmlformats.org/officeDocument/2006/relationships}id"] for s in root.findall(".//m:sheet", ns) if s.attrib["name"] == "mtm")]))
        r1_mtm, r2_mtm = {}, {}
        for r in s_mtm.findall(".//m:row", ns)[:2]:
            r_num = int(r.attrib.get("r"))
            for c in r.findall("m:c", ns):
                ref = "".join(filter(str.isalpha, c.attrib.get("r")))
                v = get_val(c)
                if r_num == 1: r1_mtm[ref] = v
                elif r_num == 2: r2_mtm[ref] = v

        timeline_mtm = {}
        for ref, m in r2_mtm.items():
            y = r1_mtm.get(ref, "")
            if y in ["2024", "2025", "2026"] and m.isdigit():
                timeline_mtm[ref] = (y, int(m))

        mtm_data = {cd: {} for cd in weights}
        for r in s_mtm.findall(".//m:row", ns)[2:]:
            cells = {}
            for c in r.findall("m:c", ns):
                cells["".join(filter(str.isalpha, c.attrib.get("r")))] = get_val(c)
            if cells.get("B", "") == "SULTRA" and cells.get("E", "") in weights:
                cd = cells.get("E", "")
                for col_ref, ym in timeline_mtm.items():
                    try: mtm_data[cd][ym] = float(cells.get(col_ref, ""))
                    except: pass

        # 4. Sheet yoy
        s_yoy = ET.fromstring(z.read("xl/" + rel_map[next(s.attrib["{http://schemas.openxmlformats.org/officeDocument/2006/relationships}id"] for s in root.findall(".//m:sheet", ns) if s.attrib["name"] == "yoy")]))
        r1_yoy, r2_yoy = {}, {}
        for r in s_yoy.findall(".//m:row", ns)[:2]:
            r_num = int(r.attrib.get("r"))
            for c in r.findall("m:c", ns):
                ref = "".join(filter(str.isalpha, c.attrib.get("r")))
                v = get_val(c)
                if r_num == 1: r1_yoy[ref] = v
                elif r_num == 2: r2_yoy[ref] = v

        timeline_yoy = {}
        for ref, m in r2_yoy.items():
            y = r1_yoy.get(ref, "")
            if y in ["2024", "2025", "2026"] and m.isdigit():
                timeline_yoy[ref] = (y, int(m))

        yoy_data = {cd: {} for cd in weights}
        for r in s_yoy.findall(".//m:row", ns)[2:]:
            cells = {}
            for c in r.findall("m:c", ns):
                cells["".join(filter(str.isalpha, c.attrib.get("r")))] = get_val(c)
            if cells.get("B", "") == "SULTRA" and cells.get("E", "") in weights:
                cd = cells.get("E", "")
                for col_ref, ym in timeline_yoy.items():
                    try: yoy_data[cd][ym] = float(cells.get(col_ref, ""))
                    except: pass

        # 5. Sheet Disagregasi
        s_dis = ET.fromstring(z.read("xl/" + rel_map[next(s.attrib["{http://schemas.openxmlformats.org/officeDocument/2006/relationships}id"] for s in root.findall(".//m:sheet", ns) if s.attrib["name"] == "Disagregasi")]))
        dis_cells = {}
        for r in s_dis.findall(".//m:row", ns):
            r_num = int(r.attrib.get("r"))
            for c in r.findall("m:c", ns):
                ref = "".join(filter(str.isalpha, c.attrib.get("r")))
                dis_cells[(r_num, ref)] = get_val(c)

        timeline_dis = {}
        for (r, col) in dis_cells:
            if r == 2:
                y = dis_cells.get((1, col), "")
                m = dis_cells.get((2, col), "")
                if y in ["2024", "2025", "2026"] and m.isdigit():
                    timeline_dis[(y, int(m))] = col

    # BANGUN LEMBAR KERJA EXCEL
    # Sheet 1: Perkembangan Inflasi VF 2024-2026
    sheet1_rows = [
        ["PERKEMBANGAN INFLASI VOLATILE FOOD (VF) PROVINSI SULAWESI TENGGARA (2024 - 2026)"],
        ["Sumber Data: Kertas Kerja Inflasi TD 2022_Project Integrasi_FPKP KPw BI Sultra"],
        ["Total Bobot Kelompok VF di Sultra:", f"{total_w_vf*100:.3f}% dari IHK Total Sultra (Tahun Dasar 2022=100)"],
        [],
        ["Tahun", "Bulan", "IHK VF Sultra", "Inflasi MtM (Bobot Komoditas)", "Inflasi MtM (Sheet Disagregasi)", "Inflasi YoY (Bobot Komoditas)", "Inflasi YoY (Sheet Disagregasi)", "Andil YoY VF ke IHK Umum (%)", "Catatan Dinamika / Musiman"]
    ]

    all_periods = sorted(list(set(list(timeline_mtm.values()) + list(timeline_yoy.values()) + list(timeline_dis.keys()))))
    for (y, m) in all_periods:
        # MtM
        w_sum_m, val_sum_m = 0.0, 0.0
        for cd, info in weights.items():
            if (y, m) in mtm_data[cd]:
                w_sum_m += info["bobot_ihk"]
                val_sum_m += info["bobot_ihk"] * mtm_data[cd][(y, m)]
        calc_mtm = round(val_sum_m / w_sum_m, 2) if w_sum_m > 0 else "-"

        # YoY
        w_sum_y, val_sum_y = 0.0, 0.0
        for cd, info in weights.items():
            if (y, m) in yoy_data[cd]:
                w_sum_y += info["bobot_ihk"]
                val_sum_y += info["bobot_ihk"] * yoy_data[cd][(y, m)]
        calc_yoy = round(val_sum_y / w_sum_y, 2) if w_sum_y > 0 else "-"

        dis_col = timeline_dis.get((y, m), "")
        dis_ihk_str = dis_cells.get((10, dis_col), "-") if dis_col else "-"
        try: dis_ihk = round(float(dis_ihk_str), 2)
        except: dis_ihk = dis_ihk_str

        dis_mtm_str = dis_cells.get((16, dis_col), "-") if dis_col else "-"
        try: dis_mtm = round(float(dis_mtm_str), 2)
        except: dis_mtm = dis_mtm_str

        dis_yoy_str = dis_cells.get((28, dis_col), "-") if dis_col else "-"
        try: dis_yoy = round(float(dis_yoy_str), 2)
        except: dis_yoy = dis_yoy_str

        dis_andil_str = dis_cells.get((34, dis_col), "-") if dis_col else "-"
        try: dis_andil = round(float(dis_andil_str), 2)
        except: dis_andil = dis_andil_str

        note = ""
        if m in [3, 4]: note = "Periode Ramadan & Idul Fitri (Lonjakan Permintaan Pangan)"
        elif m in [6, 7]: note = "Musim Angin Timur / Gelombang Tinggi (Tekanan Pasokan Ikan Tangkap)"
        elif m in [8, 9]: note = "Masa Panen Gadu / Deflasi Musiman Sayuran & Bawang"
        elif m == 12: note = "Persiapan HBKN Nataru"

        sheet1_rows.append([int(y), m, dis_ihk, calc_mtm, dis_mtm, calc_yoy, dis_yoy, dis_andil, note])

    # Sheet 2: Bobot 70 Komoditas VF
    sheet2_rows = [
        ["TABEL BOBOT 70 KOMODITAS VOLATILE FOOD (VF) PROVINSI SULAWESI TENGGARA"],
        ["Tahun Dasar 2022 = 100 (BPS & KPw Bank Indonesia Provinsi Sultra)"],
        [],
        ["Peringkat", "Kode BPS", "Nama Komoditas VF", "Bobot dalam IHK Total Sultra (%)", "Pangsa dalam Keranjang VF (%)", "Kelompok Utama"]
    ]
    sorted_comms = sorted(weights.items(), key=lambda x: x[1]["bobot_ihk"], reverse=True)
    for rank, (cd, info) in enumerate(sorted_comms, 1):
        grp = "Beras" if "BERAS" in info["nama"] else ("Perikanan" if "IKAN" in info["nama"] or "UDANG" in info["nama"] or "CUMI" in info["nama"] else ("Hortikultura" if any(h in info["nama"] for h in ["CABAI", "BAWANG", "TOMAT", "KANGKUNG", "BAYAM"]) else "Peternakan/Lainnya"))
        sheet2_rows.append([
            rank,
            cd,
            info["nama"],
            round(info["bobot_ihk"] * 100, 3),
            round(info["porsi_vf"], 2),
            grp
        ])

    sheets_payload = {
        "Inflasi VF 2024-2026": sheet1_rows,
        "Bobot 70 Komoditas VF": sheet2_rows
    }

    create_excel(sheets_payload, OUT_EXCEL)
    print(f"[OK] Berhasil membuat file Excel: {OUT_EXCEL}")

    if os.path.exists(ARTIFACT_DIR):
        import shutil
        shutil.copy2(OUT_EXCEL, os.path.join(ARTIFACT_DIR, "laporan_inflasi_volatile_food_sultra_2024_2026.xlsx"))
        print("[OK] Disalin ke Brain Artifact")

if __name__ == "__main__":
    main()
