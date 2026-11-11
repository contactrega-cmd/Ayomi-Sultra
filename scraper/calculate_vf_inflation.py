#!/usr/bin/env python3
"""
Analisis dan Perhitungan Perkembangan Inflasi Volatile Food (VF) Sultra 2024 - 2026
Mengacu pada Kertas Kerja Inflasi TD 2022_Project Integrasi_FPKP ok.xlsx

Menghitung:
1. Bobot masing-masing dari 70 komoditas penyumbang inflasi VF di Sultra (Tahun Dasar 2022).
2. Inflasi MtM dan YoY Volatile Food secara tertimbang (weighted average).
3. Andil inflasi VF terhadap inflasi umum Sultra.
4. Komparasi dengan angka disagregasi resmi FPKP BI di sheet Disagregasi.
"""

import os
import zipfile
import xml.etree.ElementTree as ET

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
EXCEL_PATH = os.path.join(BASE_DIR, "Jangan Diotakatik Kertas Kerja Inflasi TD 2022_Project Integrasi_FPKP ok.xlsx")

def main():
    if not os.path.exists(EXCEL_PATH):
        print(f"Error: File tidak ditemukan di {EXCEL_PATH}")
        return

    print("Memproses Kertas Kerja Inflasi FPKP BI...")
    with zipfile.ZipFile(EXCEL_PATH, "r") as z:
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

        # 1. Ambil daftar komoditas VF dari Klasifikasi
        sheet_klas_id = next(s.attrib["{http://schemas.openxmlformats.org/officeDocument/2006/relationships}id"] for s in root.findall(".//m:sheet", ns) if s.attrib["name"] == "Klasifikasi")
        s_klas = ET.fromstring(z.read("xl/" + rel_map[sheet_klas_id]))
        vf_codes = set()
        for r in s_klas.findall(".//m:row", ns)[2:]:
            cells = {}
            for c in r.findall("m:c", ns):
                ref = "".join(filter(str.isalpha, c.attrib.get("r")))
                cells[ref] = get_val(c)
            if cells.get("H", "") == "1" and cells.get("E", ""):
                vf_codes.add(cells.get("E", ""))

        # 2. Ambil Bobot Sultra per komoditas dari sheet Bobot
        sheet_bobot_id = next(s.attrib["{http://schemas.openxmlformats.org/officeDocument/2006/relationships}id"] for s in root.findall(".//m:sheet", ns) if s.attrib["name"] == "Bobot")
        s_bobot = ET.fromstring(z.read("xl/" + rel_map[sheet_bobot_id]))
        weights = {}
        for r in s_bobot.findall(".//m:row", ns)[4:]:
            cells = {}
            for c in r.findall("m:c", ns):
                ref = "".join(filter(str.isalpha, c.attrib.get("r")))
                cells[ref] = get_val(c)
            city = cells.get("B", "")
            code = cells.get("E", "")
            name = cells.get("F", "")
            if city == "SULTRA" and code in vf_codes:
                try:
                    w_val = float(cells.get("AF", "0")) # Bobot Jan 2024
                except:
                    w_val = 0.0
                weights[code] = {
                    "nama": name,
                    "bobot_ihk": w_val
                }

        total_w_vf = sum(x["bobot_ihk"] for x in weights.values())
        for cd in weights:
            weights[cd]["porsi_vf"] = (weights[cd]["bobot_ihk"] / total_w_vf * 100) if total_w_vf else 0

        # 3. Baca Timeline & Data sheet mtm
        sheet_mtm_id = next(s.attrib["{http://schemas.openxmlformats.org/officeDocument/2006/relationships}id"] for s in root.findall(".//m:sheet", ns) if s.attrib["name"] == "mtm")
        s_mtm = ET.fromstring(z.read("xl/" + rel_map[sheet_mtm_id]))
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
                ref = "".join(filter(str.isalpha, c.attrib.get("r")))
                cells[ref] = get_val(c)
            city = cells.get("B", "")
            code = cells.get("E", "")
            if city == "SULTRA" and code in weights:
                for col_ref, ym in timeline_mtm.items():
                    val_str = cells.get(col_ref, "")
                    try:
                        mtm_data[code][ym] = float(val_str)
                    except:
                        pass

        # 4. Baca Timeline & Data sheet yoy
        sheet_yoy_id = next(s.attrib["{http://schemas.openxmlformats.org/officeDocument/2006/relationships}id"] for s in root.findall(".//m:sheet", ns) if s.attrib["name"] == "yoy")
        s_yoy = ET.fromstring(z.read("xl/" + rel_map[sheet_yoy_id]))
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
                ref = "".join(filter(str.isalpha, c.attrib.get("r")))
                cells[ref] = get_val(c)
            city = cells.get("B", "")
            code = cells.get("E", "")
            if city == "SULTRA" and code in weights:
                for col_ref, ym in timeline_yoy.items():
                    val_str = cells.get(col_ref, "")
                    try:
                        yoy_data[code][ym] = float(val_str)
                    except:
                        pass

        # 5. Baca sheet Disagregasi
        sheet_dis_id = next(s.attrib["{http://schemas.openxmlformats.org/officeDocument/2006/relationships}id"] for s in root.findall(".//m:sheet", ns) if s.attrib["name"] == "Disagregasi")
        s_dis = ET.fromstring(z.read("xl/" + rel_map[sheet_dis_id]))
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

        # Gabungkan timeline
        all_periods = sorted(list(set(list(timeline_mtm.values()) + list(timeline_yoy.values()) + list(timeline_dis.keys()))))

        print(f"\n=========================================================================================")
        print(f"ANALISIS INFLASI VOLATILE FOOD (VF) SULTRA 2024 - 2026 (70 KOMODITAS)")
        print(f"Total Bobot VF di Sultra: {total_w_vf*100:.3f}% dari IHK Total Sultra")
        print(f"=========================================================================================\n")

        print("RINGKASAN TABEL PER BULAN (2024 - 2026):")
        print(f"{'Periode':9s} | {'MtM Terhitung':14s} | {'MtM Disagregasi':16s} | {'YoY Terhitung':14s} | {'YoY Disagregasi':16s} | {'Andil YoY ke IHK':16s}")
        print("-" * 95)

        results = []
        for (y, m) in all_periods:
            # MtM Weighted
            w_sum_mtm = 0.0
            val_sum_mtm = 0.0
            for cd, info in weights.items():
                if (y, m) in mtm_data[cd]:
                    w_sum_mtm += info["bobot_ihk"]
                    val_sum_mtm += info["bobot_ihk"] * mtm_data[cd][(y, m)]
            calc_mtm = (val_sum_mtm / w_sum_mtm) if w_sum_mtm > 0 else None

            # YoY Weighted
            w_sum_yoy = 0.0
            val_sum_yoy = 0.0
            for cd, info in weights.items():
                if (y, m) in yoy_data[cd]:
                    w_sum_yoy += info["bobot_ihk"]
                    val_sum_yoy += info["bobot_ihk"] * yoy_data[cd][(y, m)]
            calc_yoy = (val_sum_yoy / w_sum_yoy) if w_sum_yoy > 0 else None

            dis_col = timeline_dis.get((y, m), "")
            dis_ihk = dis_cells.get((10, dis_col), "") if dis_col else ""
            dis_mtm = dis_cells.get((16, dis_col), "") if dis_col else ""
            dis_yoy = dis_cells.get((28, dis_col), "") if dis_col else ""
            dis_andil = dis_cells.get((34, dis_col), "") if dis_col else ""

            # Formatting
            s_cmtm = f"{calc_mtm:6.2f}%" if calc_mtm is not None else "  -  "
            s_cyoy = f"{calc_yoy:6.2f}%" if calc_yoy is not None else "  -  "
            try: s_dmtm = f"{float(dis_mtm):6.2f}%"
            except: s_dmtm = f"{dis_mtm:7s}"
            try: s_dyoy = f"{float(dis_yoy):6.2f}%"
            except: s_dyoy = f"{dis_yoy:7s}"
            try: s_dandil = f"{float(dis_andil):6.2f}%"
            except: s_dandil = f"{dis_andil:7s}"

            print(f"{y}-{m:02d}    | {s_cmtm:14s} | {s_dmtm:16s} | {s_cyoy:14s} | {s_dyoy:16s} | {s_dandil:16s}")
            results.append({
                "tahun": y,
                "bulan": m,
                "calc_mtm": calc_mtm,
                "dis_mtm": dis_mtm,
                "calc_yoy": calc_yoy,
                "dis_yoy": dis_yoy,
                "dis_ihk": dis_ihk,
                "andil_yoy": dis_andil
            })

if __name__ == "__main__":
    main()
