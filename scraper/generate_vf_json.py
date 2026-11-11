#!/usr/bin/env python3
"""
Ekstraksi Data Volatile Food (VF) Sultra 2024-2026 ke format JSON
untuk visualisasi di Dashboard EWS Inflasi (Tab Perkembangan Inflasi).
"""

import os
import json
import zipfile
import xml.etree.ElementTree as ET

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DATA_DIR = os.path.join(BASE_DIR, "data")
SRC_EXCEL = os.path.join(BASE_DIR, "Jangan Diotakatik Kertas Kerja Inflasi TD 2022_Project Integrasi_FPKP ok.xlsx")
OUT_JSON = os.path.join(DATA_DIR, "volatile_food_sultra_2024_2026.json")
ARTIFACT_DIR = "/Users/regaprasetyo/.gemini/antigravity/brain/45b29b5e-87d9-439a-b46b-f9c22bf36c3e"

MONTH_NAMES_ID = [
    "", "Januari", "Februari", "Maret", "April", "Mei", "Juni",
    "Juli", "Agustus", "September", "Oktober", "November", "Desember"
]

def main():
    if not os.path.exists(SRC_EXCEL):
        print(f"Error: {SRC_EXCEL} tidak ditemukan!")
        return

    print("Mengekstrak data VF dari Kertas Kerja FPKP BI...")
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

        # 1. Klasifikasi VF (H == 1)
        s_klas = ET.fromstring(z.read("xl/" + rel_map[next(s.attrib["{http://schemas.openxmlformats.org/officeDocument/2006/relationships}id"] for s in root.findall(".//m:sheet", ns) if s.attrib["name"] == "Klasifikasi")]))
        vf_codes = set()
        for r in s_klas.findall(".//m:row", ns)[2:]:
            cells = {}
            for c in r.findall("m:c", ns):
                cells["".join(filter(str.isalpha, c.attrib.get("r")))] = get_val(c)
            if cells.get("H", "") == "1" and cells.get("E", ""):
                vf_codes.add(cells.get("E", ""))

        # 2. Bobot Sultra
        s_bobot = ET.fromstring(z.read("xl/" + rel_map[next(s.attrib["{http://schemas.openxmlformats.org/officeDocument/2006/relationships}id"] for s in root.findall(".//m:sheet", ns) if s.attrib["name"] == "Bobot")]))
        weights = {}
        for r in s_bobot.findall(".//m:row", ns)[4:]:
            cells = {}
            for c in r.findall("m:c", ns):
                cells["".join(filter(str.isalpha, c.attrib.get("r")))] = get_val(c)
            if cells.get("B", "") == "SULTRA" and cells.get("E", "") in vf_codes:
                code = cells.get("E", "")
                name = cells.get("F", "").strip()
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

    # BANGUN SERI BULANAN
    all_periods = sorted(list(set(list(timeline_mtm.values()) + list(timeline_yoy.values()) + list(timeline_dis.keys()))))
    monthly_series = []

    for (y, m) in all_periods:
        # MtM
        w_sum_m, val_sum_m = 0.0, 0.0
        for cd, info in weights.items():
            if (y, m) in mtm_data[cd]:
                w_sum_m += info["bobot_ihk"]
                val_sum_m += info["bobot_ihk"] * mtm_data[cd][(y, m)]
        calc_mtm = round(val_sum_m / w_sum_m, 2) if w_sum_m > 0 else None

        # YoY
        w_sum_y, val_sum_y = 0.0, 0.0
        for cd, info in weights.items():
            if (y, m) in yoy_data[cd]:
                w_sum_y += info["bobot_ihk"]
                val_sum_y += info["bobot_ihk"] * yoy_data[cd][(y, m)]
        calc_yoy = round(val_sum_y / w_sum_y, 2) if w_sum_y > 0 else None

        dis_col = timeline_dis.get((y, m), "")
        dis_ihk_str = dis_cells.get((10, dis_col), "") if dis_col else ""
        try: dis_ihk = round(float(dis_ihk_str), 2)
        except: dis_ihk = None

        dis_mtm_str = dis_cells.get((16, dis_col), "") if dis_col else ""
        try: dis_mtm = round(float(dis_mtm_str), 2)
        except: dis_mtm = None

        dis_yoy_str = dis_cells.get((28, dis_col), "") if dis_col else ""
        try: dis_yoy = round(float(dis_yoy_str), 2)
        except: dis_yoy = None

        dis_andil_str = dis_cells.get((34, dis_col), "") if dis_col else ""
        try: dis_andil = round(float(dis_andil_str), 2)
        except: dis_andil = None

        # Resolusi angka resmi vs kalkulasi
        final_mtm = dis_mtm if dis_mtm is not None else calc_mtm
        final_yoy = dis_yoy if dis_yoy is not None else calc_yoy

        # Dinamika musiman & catatan
        catatan = ""
        faktor_kunci = ""
        if y == "2024" and m == 1:
            catatan = "Transisi pembaharuan Tahun Dasar BPS dari 2018=100 ke 2022=100 (lonjakan nominal IHK)"
            faktor_kunci = "Perubahan Metodologi BPS"
        elif m in [3, 4]:
            catatan = "Lonjakan musiman HBKN Ramadan & Idul Fitri (Daging Ayam, Telur, Aneka Cabai)"
            faktor_kunci = "HBKN Ramadan & Idul Fitri"
        elif m in [6, 7]:
            catatan = "Puncak Musim Angin Timur & Gelombang Laut Tinggi Banda/Wakatobi (Kelangkaan Ikan Laut Segar)"
            faktor_kunci = "Musim Angin Timur / Gelombang Laut"
        elif m in [8, 9]:
            catatan = "Musim Panen Gadu & Pasokan Sayuran Melimpah (Normalisasi harga hortikultura)"
            faktor_kunci = "Panen Padi & Sayuran"
        elif m == 12:
            catatan = "Persiapan Hari Raya Natal & Tahun Baru (Nataru)"
            faktor_kunci = "HBKN Nataru"
        else:
            catatan = "Pergerakan stabil didukung kecukupan pasokan pangan strategis"
            faktor_kunci = "Pasokan Normal"

        monthly_series.append({
            "tahun": int(y),
            "bulan": m,
            "periode_str": f"{MONTH_NAMES_ID[m]} {y}",
            "periode_singkat": f"{MONTH_NAMES_ID[m][:3]} {y}",
            "ihk": dis_ihk,
            "mtm": final_mtm,
            "mtm_kalkulasi": calc_mtm,
            "mtm_disagregasi": dis_mtm,
            "yoy": final_yoy,
            "yoy_kalkulasi": calc_yoy,
            "yoy_disagregasi": dis_yoy,
            "andil_yoy": dis_andil,
            "catatan": catatan,
            "faktor_kunci": faktor_kunci
        })

    # KOMODITAS PENYUMBANG TERBESAR (70 Komoditas)
    commodities_list = []
    sorted_comms = sorted(weights.items(), key=lambda x: x[1]["bobot_ihk"], reverse=True)
    
    for rank, (cd, info) in enumerate(sorted_comms, 1):
        cname = info["nama"]
        # Kategori
        if "BERAS" in cname:
            kategori = "Beras & Padi-padian"
            sensitivitas = "Sensitif terhadap El Nino/La Nina, musim tanam, & ketersediaan stok SPHP Bulog"
        elif any(k in cname for k in ["IKAN", "UDANG", "CUMI", "KEPITING"]):
            kategori = "Perikanan Tangkap Laut"
            sensitivitas = "Sangat tinggi terhadap tinggi gelombang laut & kecepatan angin timur di Laut Banda/Flores"
        elif any(k in cname for k in ["CABAI", "BAWANG", "TOMAT", "KANGKUNG", "BAYAM", "KACANG PANJANG", "SAWI", "TERUNG"]):
            kategori = "Hortikultura & Sayuran"
            sensitivitas = "Sensitif terhadap curah hujan ekstrem, hama penyakit, & kelancaran logistik antar-pulau"
        elif any(k in cname for k in ["AYAM", "TELUR", "SAPI"]):
            kategori = "Peternakan"
            sensitivitas = "Dipengaruhi harga jagung pakan ternak & lonjakan permintaan HBKN keagamaan"
        else:
            kategori = "Pangan Lainnya"
            sensitivitas = "Dinamika musiman lokal"

        commodities_list.append({
            "peringkat": rank,
            "kode": cd,
            "nama": cname,
            "bobot_ihk_persen": round(info["bobot_ihk"] * 100, 3),
            "porsi_vf_persen": round(info["porsi_vf"], 2),
            "kategori": kategori,
            "sensitivitas": sensitivitas
        })

    # RINGKASAN TAHUNAN
    # 2024
    s24 = [x for x in monthly_series if x["tahun"] == 2024]
    # 2025
    s25 = [x for x in monthly_series if x["tahun"] == 2025]
    # 2026
    s26 = [x for x in monthly_series if x["tahun"] == 2026]

    def avg(lst):
        vals = [v for v in lst if v is not None]
        return round(sum(vals)/len(vals), 2) if vals else 0.0

    y24_summary = {
        "tahun": 2024,
        "rata_rata_mtm": avg([x["mtm"] for x in s24 if x["bulan"] > 1]), # exclude Jan base year leap
        "rata_rata_yoy": avg([x["yoy"] for x in s24]),
        "yoy_tertinggi": max([x["yoy"] for x in s24 if x["yoy"] is not None] or [0]),
        "yoy_terendah": min([x["yoy"] for x in s24 if x["yoy"] is not None] or [0]),
        "posisi_akhir_tahun_yoy": next((x["yoy"] for x in reversed(s24) if x["yoy"] is not None), None),
        "catatan_tahunan": "Tahun transisi Tahun Dasar BPS 2022=100. Inflasi MtM stabil pasca-Februari, dengan lonjakan musiman saat HBKN Maret dan tekanan musiman Juni."
    }

    y25_summary = {
        "tahun": 2025,
        "rata_rata_mtm": avg([x["mtm"] for x in s25]),
        "rata_rata_yoy": avg([x["yoy"] for x in s25]),
        "yoy_tertinggi": max([x["yoy"] for x in s25 if x["yoy"] is not None] or [0]), # 11.66% Juli
        "bulan_puncak": "Juli (11.66%) & Agustus (11.59%)",
        "yoy_terendah": min([x["yoy"] for x in s25 if x["yoy"] is not None] or [0]), # 0.94% Jan
        "posisi_akhir_tahun_yoy": next((x["yoy"] for x in reversed(s25) if x["yoy"] is not None), None), # 4.61% Des
        "catatan_tahunan": "Ditandai gelombang inflasi ekstrem kelompok perikanan laut akibat cuaca buruk dan angin timur pada Juni - Agustus 2025, sebelum mereda menuju 4.61% di akhir tahun."
    }

    y26_summary = {
        "tahun": 2026,
        "rata_rata_mtm": avg([x["mtm"] for x in s26]),
        "rata_rata_yoy": avg([x["yoy"] for x in s26]),
        "yoy_tertinggi": max([x["yoy"] for x in s26 if x["yoy"] is not None] or [0]), # 7.12% Juni
        "bulan_puncak": "Juni (7.12%) & Mei (6.59%)",
        "yoy_terendah": min([x["yoy"] for x in s26 if x["yoy"] is not None] or [0]), # 0.39% Juli
        "posisi_terkini_yoy": next((x["yoy"] for x in reversed(s26) if x["yoy"] is not None), None), # 4.91% Sep
        "posisi_terkini_mtm": next((x["mtm"] for x in reversed(s26) if x["mtm"] is not None), None), # 2.21% Sep
        "catatan_tahunan": "Tahun berjalan 2026: Terjadi lonjakan di paruh pertama (Mei-Juni 2026), sempat deflasi tajam di Juli-Agustus, dan kembali naik ke 4.91% di September 2026."
    }

    # Kategori Ringkasan Pangsa Bobot
    kategori_weights = {}
    for c in commodities_list:
        cat = c["kategori"]
        kategori_weights[cat] = kategori_weights.get(cat, 0.0) + c["bobot_ihk_persen"]
    kategori_summary = [{"kategori": k, "bobot_ihk": round(v, 3), "porsi_vf": round(v / (total_w_vf*100) * 100, 1)} for k, v in kategori_weights.items()]
    kategori_summary.sort(key=lambda x: x["bobot_ihk"], reverse=True)

    output_payload = {
        "metadata": {
            "judul": "Analisis Disagregasi Inflasi Volatile Food (VF) Provinsi Sulawesi Tenggara",
            "periode": "2024 - 2026",
            "tahun_dasar": "2022 = 100",
            "sumber": "Kertas Kerja Inflasi TD 2022_Project Integrasi_FPKP KPw BI Provinsi Sulawesi Tenggara & BPS",
            "total_komoditas": len(commodities_list),
            "total_bobot_vf_ihk_persen": round(total_w_vf * 100, 3),
            "file_excel": "laporan_inflasi_volatile_food_sultra_2024_2026.xlsx"
        },
        "ringkasan_tahunan": {
            "2024": y24_summary,
            "2025": y25_summary,
            "2026": y26_summary
        },
        "komposisi_kategori": kategori_summary,
        "deret_bulanan": monthly_series,
        "daftar_komoditas_teratas": commodities_list[:20],
        "seluruh_komoditas": commodities_list
    }

    with open(OUT_JSON, "w", encoding="utf-8") as f:
        json.dump(output_payload, f, ensure_ascii=False, indent=2)

    print(f"[OK] Berhasil membuat dataset VF: {OUT_JSON}")

    # Copy ke Artifact directory jika ada
    if os.path.exists(ARTIFACT_DIR):
        artifact_out = os.path.join(ARTIFACT_DIR, "volatile_food_sultra_2024_2026.json")
        with open(artifact_out, "w", encoding="utf-8") as f:
            json.dump(output_payload, f, ensure_ascii=False, indent=2)
        print(f"[OK] Disalin ke Brain Artifact: {artifact_out}")

if __name__ == "__main__":
    main()
