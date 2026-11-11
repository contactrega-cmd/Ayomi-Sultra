#!/usr/bin/env python3
"""
KOMPILASI MATRIKS DETEKSI LONJAKAN HARGA 17 KABUPATEN/KOTA SE-SULAWESI TENGGARA
Model: Multi-Horizon Weighted Moving Average (MH-WMA) dengan Horizon-Based Power Weights
Rumus:
- MA_t(n) = (1 / n) * sum_{i=0}^{n-1} P_{t-i}   untuk n in {5, 20, 60, 120}
- w_i = (n_i^alpha) / sum_j (n_j^alpha)         dengan alpha = 0.5 (Berimbang)
  -> Bobot: MA 5 = 8,8%, MA 20 = 17,6%, MA 60 = 30,5%, MA 120 = 43,1%
- Status Biner:
  * Deviasi Positif : Harga Aktual > Harga Acuan MH-WMA
  * Deviasi Negatif : Harga Aktual <= Harga Acuan MH-WMA
Sumber Data Harian Empiris (2024 - 2026):
- PIHPS Bank Indonesia Pasar Tradisional (Kota Kendari & Kota Baubau)
- SP2KP Kementerian Perdagangan RI (15 Kabupaten Lainnya)
"""

import os
import sys
import json
from datetime import datetime

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DATA_DIR = os.path.join(BASE_DIR, "data")
PIHPS_DAILY_CITIES_PATH = os.path.join(DATA_DIR, "pihps_daily_cities_2024_2026.json")
PIHPS_PATH = os.path.join(DATA_DIR, "pihps_sultra_all.json")
SP2KP_PATH = os.path.join(DATA_DIR, "sp2kp_daily_sultra.json")
OUT_PATH = os.path.join(DATA_DIR, "alps_17_kabkota.json")

# Bobot terkunci Model MH-WMA (alpha = 0,5 / Berimbang)
WEIGHT_MA5 = 0.088
WEIGHT_MA20 = 0.176
WEIGHT_MA60 = 0.305
WEIGHT_MA120 = 0.431
MHWMA_ALPHA = 0.5
MHWMA_EPS = 1e-6

KUADRAN_META = {
    "K1": {
        "id": "K1",
        "code": "K I",
        "roman": "K I",
        "color_name": "Merah",
        "title": "Harga Tinggi Persisten",
        "short": "Tinggi Persisten",
        "rule": "Deviasi > 0%, Durasi ≥ d̄",
    },
    "K2": {
        "id": "K2",
        "code": "K II",
        "roman": "K II",
        "color_name": "Kuning",
        "title": "Harga Tinggi Sementara",
        "short": "Tinggi Sementara",
        "rule": "Deviasi > 0%, Durasi < d̄",
    },
    "K3": {
        "id": "K3",
        "code": "K III",
        "roman": "K III",
        "color_name": "Biru",
        "title": "Harga Rendah Persisten",
        "short": "Rendah Persisten",
        "rule": "Deviasi ≤ 0%, Durasi ≥ d̄",
    },
    "K4": {
        "id": "K4",
        "code": "K IV",
        "roman": "K IV",
        "color_name": "Hijau",
        "title": "Harga Rendah Sementara",
        "short": "Rendah Sementara",
        "rule": "Deviasi ≤ 0%, Durasi < d̄",
    },
}

COMMODITIES_10 = [
    {"id": "beras", "name": "Beras", "icon": "🌾", "satuan": "kg"},
    {"id": "daging_ayam", "name": "Daging Ayam", "icon": "🍗", "satuan": "kg"},
    {"id": "daging_sapi", "name": "Daging Sapi", "icon": "🥩", "satuan": "kg"},
    {"id": "telur_ayam", "name": "Telur Ayam", "icon": "🥚", "satuan": "kg"},
    {"id": "bawang_merah", "name": "Bawang Merah", "icon": "🧅", "satuan": "kg"},
    {"id": "bawang_putih", "name": "Bawang Putih", "icon": "🧄", "satuan": "kg"},
    {"id": "cabai_merah", "name": "Cabai Merah", "icon": "🌶️", "satuan": "kg"},
    {"id": "cabai_rawit", "name": "Cabai Rawit", "icon": "🔥", "satuan": "kg"},
    {"id": "minyak_goreng", "name": "Minyak Goreng", "icon": "🍾", "satuan": "liter"},
    {"id": "gula_pasir", "name": "Gula Pasir", "icon": "🍬", "satuan": "kg"},
]

REGIONS_17 = [
    {"id": "kendari", "name": "Kota Kendari", "pihps_key": "Kota Kendari", "type": "Kota", "group": "ihk", "is_island": False, "source": "PIHPS BI"},
    {"id": "baubau", "name": "Kota Baubau", "pihps_key": "Kota Bau-Bau", "type": "Kota", "group": "ihk", "is_island": True, "source": "PIHPS BI"},
    {"id": "kolaka", "name": "Kab. Kolaka", "type": "Kabupaten", "group": "ihk", "is_island": False, "source": "SP2KP Kemendag"},
    {"id": "konawe", "name": "Kab. Konawe", "type": "Kabupaten", "group": "ihk", "is_island": False, "source": "SP2KP Kemendag"},
    {"id": "korsel", "name": "Kab. Konawe Selatan", "type": "Kabupaten", "group": "daratan", "is_island": False, "source": "SP2KP Kemendag"},
    {"id": "bombana", "name": "Kab. Bombana", "type": "Kabupaten", "group": "daratan", "is_island": False, "source": "SP2KP Kemendag"},
    {"id": "kolut", "name": "Kab. Kolaka Utara", "type": "Kabupaten", "group": "daratan", "is_island": False, "source": "SP2KP Kemendag"},
    {"id": "konut", "name": "Kab. Konawe Utara", "type": "Kabupaten", "group": "daratan", "is_island": False, "source": "SP2KP Kemendag"},
    {"id": "koltim", "name": "Kab. Kolaka Timur", "type": "Kabupaten", "group": "daratan", "is_island": False, "source": "SP2KP Kemendag"},
    {"id": "muna", "name": "Kab. Muna", "type": "Kabupaten", "group": "kepulauan", "is_island": True, "source": "SP2KP Kemendag"},
    {"id": "buton", "name": "Kab. Buton", "type": "Kabupaten", "group": "kepulauan", "is_island": True, "source": "SP2KP Kemendag"},
    {"id": "wakatobi", "name": "Kab. Wakatobi", "type": "Kabupaten", "group": "kepulauan", "is_island": True, "source": "SP2KP Kemendag"},
    {"id": "butur", "name": "Kab. Buton Utara", "type": "Kabupaten", "group": "kepulauan", "is_island": True, "source": "SP2KP Kemendag"},
    {"id": "konkep", "name": "Kab. Konawe Kepulauan", "type": "Kabupaten", "group": "kepulauan", "is_island": True, "source": "SP2KP Kemendag"},
    {"id": "mubar", "name": "Kab. Muna Barat", "type": "Kabupaten", "group": "kepulauan", "is_island": True, "source": "SP2KP Kemendag"},
    {"id": "buteng", "name": "Kab. Buton Tengah", "type": "Kabupaten", "group": "kepulauan", "is_island": True, "source": "SP2KP Kemendag"},
    {"id": "busel", "name": "Kab. Buton Selatan", "type": "Kabupaten", "group": "kepulauan", "is_island": True, "source": "SP2KP Kemendag"},
]


def parse_date_str(d_str):
    parts = d_str.split("/")
    return datetime(int(parts[2]), int(parts[1]), int(parts[0]))


def fmt_rp(val):
    if val is None:
        return "N/A"
    return f"Rp{round(val):,}".replace(",", ".")


def fmt_diff_rp(val):
    if val is None:
        return "-"
    iv = round(val)
    if iv == 0:
        return "Rp0"
    sign = "+" if iv > 0 else "-"
    return f"{sign}Rp{abs(iv):,}".replace(",", ".")


def fmt_pct(val):
    if val is None:
        return "N/A"
    return f"{val:+.1f}%".replace(".", ",")


def compute_mhwma_metrics(sorted_pairs):
    """
    Menghitung MA 5, MA 20, MA 60, MA 120, dan Harga Acuan MH-WMA (alpha=0.5)
    pada deret kronologis [(dt, price), ...].
    """
    n = len(sorted_pairs)
    if n == 0:
        return {"tersedia": False, "model_ready": False, "n_obs": 0}

    prices = [p for _, p in sorted_pairs]
    dates = [dt.strftime("%d/%m/%Y") for dt, _ in sorted_pairs]

    latest_p = prices[-1]
    latest_date = dates[-1]
    first_date = dates[0]

    # Rolling prefix sums untuk SMA O(N)
    prefix = [0.0] * (n + 1)
    for idx, p in enumerate(prices):
        prefix[idx + 1] = prefix[idx] + p

    def sma_at(i, window):
        if i < window - 1:
            return None
        return (prefix[i + 1] - prefix[i + 1 - window]) / float(window)

    ma5_last = sma_at(n - 1, 5)
    ma20_last = sma_at(n - 1, 20)
    ma60_last = sma_at(n - 1, 60)
    ma120_last = sma_at(n - 1, 120)

    if n < 120:
        return {
            "tersedia": True,
            "model_ready": False,
            "n_obs": n,
            "n_mhwma_obs": 0,
            "first_date": first_date,
            "latest_date": latest_date,
            "harga_aktual": latest_p,
            "ma_5": round(ma5_last, 2) if ma5_last is not None else None,
            "ma_20": round(ma20_last, 2) if ma20_last is not None else None,
            "ma_60": round(ma60_last, 2) if ma60_last is not None else None,
            "ma_120": None,
        }

    # Hitung seluruh kurva aktif MH-WMA sejak i = 119 (titik ke-120)
    pos_days = 0
    neg_days = 0
    peak_dev_pct = None
    peak_dev_date = None
    mhwma_series = []
    state_flags = []

    for i in range(119, n):
        m5 = sma_at(i, 5)
        m20 = sma_at(i, 20)
        m60 = sma_at(i, 60)
        m120 = sma_at(i, 120)
        mw = (
            WEIGHT_MA5 * m5
            + WEIGHT_MA20 * m20
            + WEIGHT_MA60 * m60
            + WEIGHT_MA120 * m120
        )
        mhwma_series.append(mw)
        p_cur = prices[i]
        diff_i = p_cur - mw
        is_pos_i = diff_i > MHWMA_EPS
        state_flags.append(is_pos_i)
        if is_pos_i:
            pos_days += 1
        else:
            neg_days += 1
        dev_i = (diff_i / mw) * 100.0 if (mw > 0 and abs(diff_i) > MHWMA_EPS) else 0.0
        if peak_dev_pct is None or dev_i > peak_dev_pct:
            peak_dev_pct = dev_i
            peak_dev_date = dates[i]

    # Hitung run-length episode pergerakan harga antar pembalikan arah terhadap MH-WMA
    runs = []
    cur_state = state_flags[0]
    run_len = 0
    run_start_idx = 0
    for idx_s, st in enumerate(state_flags):
        if st == cur_state:
            run_len += 1
        else:
            runs.append((cur_state, run_len, dates[119 + run_start_idx]))
            cur_state = st
            run_len = 1
            run_start_idx = idx_s
    runs.append((cur_state, run_len, dates[119 + run_start_idx]))

    spell_lengths = [r[1] for r in runs]
    durasi_hari = runs[-1][1]
    durasi_sejak_tgl = runs[-1][2]
    n_spells = len(runs)
    dpm_mean_region = round(sum(spell_lengths) / float(n_spells), 1) if n_spells > 0 else 0.0

    latest_mhwma = mhwma_series[-1]
    raw_dev_rp = latest_p - latest_mhwma
    if abs(raw_dev_rp) <= MHWMA_EPS:
        dev_rp = 0.0
        dev_pct = 0.0
        latest_is_pos = False
    else:
        dev_rp = raw_dev_rp
        dev_pct = (dev_rp / latest_mhwma) * 100.0 if latest_mhwma > 0 else 0.0
        latest_is_pos = bool(raw_dev_rp > MHWMA_EPS)

    n_active = len(mhwma_series)
    pct_pos = (pos_days / float(n_active)) * 100.0 if n_active > 0 else 0.0

    return {
        "tersedia": True,
        "model_ready": True,
        "n_obs": n,
        "n_mhwma_obs": n_active,
        "first_date": first_date,
        "mhwma_start_date": dates[119],
        "latest_date": latest_date,
        "harga_aktual": latest_p,
        "ma_5": round(ma5_last, 2),
        "ma_20": round(ma20_last, 2),
        "ma_60": round(ma60_last, 2),
        "ma_120": round(ma120_last, 2),
        "harga_wajar": round(latest_mhwma, 2),
        "deviasi_rp": round(dev_rp, 2),
        "deviasi_pct": round(dev_pct, 2),
        "is_positif": latest_is_pos,
        "pos_days": pos_days,
        "neg_days": neg_days,
        "pct_hari_positif": round(pct_pos, 1),
        "peak_dev_pct": round(peak_dev_pct, 2) if peak_dev_pct is not None else None,
        "peak_dev_date": peak_dev_date,
        "durasi_hari": durasi_hari,
        "durasi_sejak_tgl": durasi_sejak_tgl,
        "n_spells": n_spells,
        "dpm_mean_region": dpm_mean_region,
        "spell_lengths": spell_lengths,
    }


def generate_alps_17_matrix():
    print("=" * 85)
    print("MEMBANGUN MATRIKS DETEKSI LONJAKAN HARGA MH-WMA (17 KAB/KOTA x 10 KOMODITAS)")
    print("Bobot Terkunci (alpha=0.5 / Berimbang): MA5=8.8% | MA20=17.6% | MA60=30.5% | MA120=43.1%")
    print("=" * 85)

    # 1. Muat SP2KP (15 Kabupaten)
    sp2kp_daily = {}
    if os.path.exists(SP2KP_PATH):
        with open(SP2KP_PATH, "r", encoding="utf-8") as f:
            sp2kp_daily = json.load(f).get("data_harian", {})

    # 2. Muat PIHPS BI Harian Empiris 2024-2026 (Kota Kendari & Kota Bau-Bau)
    pihps_cities_daily = {}
    if os.path.exists(PIHPS_DAILY_CITIES_PATH):
        with open(PIHPS_DAILY_CITIES_PATH, "r", encoding="utf-8") as f:
            pihps_cities_daily = json.load(f).get("data_harian", {})

    # 3. Muat pihps_sultra_all.json untuk overlay rilis harian terbaru bila ada sync baru
    pihps_raw = []
    if os.path.exists(PIHPS_PATH):
        with open(PIHPS_PATH, "r", encoding="utf-8") as f:
            p_obj = json.load(f)
            pihps_raw = p_obj.get("data", [])

    matrix_rows = []
    all_global_latest_dates = []
    all_global_first_dates = []
    count_positif = 0
    count_negatif = 0
    count_na = 0
    tersedia_count = 0

    all_active_items = []
    comm_spells = {c["id"]: [] for c in COMMODITIES_10}

    for reg in REGIONS_17:
        rid = reg["id"]
        rname = reg["name"]
        row_cells = {}
        r_pos = 0
        r_neg = 0
        r_na = 0
        r_devs = []

        for comm in COMMODITIES_10:
            cname = comm["name"]
            cid = comm["id"]

            unique_dict = {}
            if reg["source"] == "PIHPS BI":
                city_key = reg.get("pihps_key", rname)
                # Harian empiris 2024-2026
                c_hist = pihps_cities_daily.get(city_key, {}).get(cname, {})
                for k, v in c_hist.items():
                    if v and float(v) > 0:
                        unique_dict[parse_date_str(k)] = float(v)
                # Overlay harga_harian_terkini dari pihps_sultra_all (kategori Pasar Tradisional)
                for r in pihps_raw:
                    if r.get("kota") == city_key and r.get("kategori_id") == 1 and r.get("level") == 1 and r.get("komoditas") == cname:
                        for k, v in r.get("harga_harian_terkini", {}).items():
                            p = v.get("harga_rp") if isinstance(v, dict) else v
                            if p and float(p) > 0:
                                unique_dict[parse_date_str(k)] = float(p)
            else:
                reg_data = sp2kp_daily.get(rname, {}).get(cname, {})
                for k, v in reg_data.items():
                    if v and float(v) > 0:
                        unique_dict[parse_date_str(k)] = float(v)

            sorted_pairs = sorted(unique_dict.items(), key=lambda x: x[0])
            metrics = compute_mhwma_metrics(sorted_pairs)

            if not metrics.get("tersedia"):
                count_na += 1
                r_na += 1
                cell_obj = {
                    "comm_id": cid,
                    "comm_name": cname,
                    "comm_icon": comm["icon"],
                    "satuan": comm["satuan"],
                    "tersedia": False,
                    "model_ready": False,
                    "n_obs": 0,
                    "harga_aktual": None,
                    "harga_aktual_str": "N/A",
                    "harga_wajar": None,
                    "harga_wajar_str": "-",
                    "ma_5": None,
                    "ma_20": None,
                    "ma_60": None,
                    "ma_120": None,
                    "deviasi_rp": None,
                    "deviasi_rp_str": "-",
                    "deviasi_pct": None,
                    "deviasi_pct_str": "N/A",
                    "status_key": "na",
                    "status": "Tidak Tersedia",
                    "status_short": "N/A",
                    "status_desc": "Survei N/A",
                    "alps": 0.0,
                    "alps_str": "N/A",
                    "badge_color": "bg-slate-100 text-slate-500 border-slate-200",
                    "tailwind_bg": "bg-slate-100",
                    "text_color": "text-slate-400",
                    "hex": "#f1f5f9",
                    "rekomendasi": f"Data harga {cname} untuk {rname} belum tersedia pada survei harian resmi {reg['source']}."
                }
            elif not metrics.get("model_ready"):
                tersedia_count += 1
                count_na += 1
                r_na += 1
                act = metrics["harga_aktual"]
                all_global_latest_dates.append(parse_date_str(metrics["latest_date"]))
                all_global_first_dates.append(parse_date_str(metrics["first_date"]))
                cell_obj = {
                    "comm_id": cid,
                    "comm_name": cname,
                    "comm_icon": comm["icon"],
                    "satuan": comm["satuan"],
                    "tersedia": True,
                    "model_ready": False,
                    "n_obs": metrics["n_obs"],
                    "first_date": metrics["first_date"],
                    "latest_date": metrics["latest_date"],
                    "harga_aktual": round(act),
                    "harga_aktual_str": fmt_rp(act),
                    "harga_wajar": None,
                    "harga_wajar_str": "-",
                    "ma_5": metrics.get("ma_5"),
                    "ma_20": metrics.get("ma_20"),
                    "ma_60": metrics.get("ma_60"),
                    "ma_120": None,
                    "deviasi_rp": None,
                    "deviasi_rp_str": "-",
                    "deviasi_pct": None,
                    "deviasi_pct_str": "<120 hr",
                    "status_key": "na",
                    "status": "Observasi < 120 Hari",
                    "status_short": "<120 hr",
                    "status_desc": "Belum cukup untuk MA 120",
                    "alps": 0.0,
                    "alps_str": "-",
                    "badge_color": "bg-slate-100 text-slate-600 border-slate-200",
                    "tailwind_bg": "bg-slate-100",
                    "text_color": "text-slate-600",
                    "hex": "#f1f5f9",
                    "rekomendasi": f"Baru tersedia {metrics['n_obs']} hari survei (dibutuhkan min. 120 hari untuk MA 120)."
                }
            else:
                tersedia_count += 1
                act = metrics["harga_aktual"]
                mh = metrics["harga_wajar"]
                dev_rp = metrics["deviasi_rp"]
                dev_pct = metrics["deviasi_pct"]
                is_pos = metrics["is_positif"]

                all_global_latest_dates.append(parse_date_str(metrics["latest_date"]))
                all_global_first_dates.append(parse_date_str(metrics["first_date"]))
                r_devs.append(dev_pct)
                comm_spells[cid].extend(metrics.get("spell_lengths", []))

                if is_pos:
                    count_positif += 1
                    r_pos += 1
                    status_key = "positif"
                    status_label = "Deviasi Positif"
                    status_short = "Positif"
                    status_desc = "Aktual > MH-WMA"
                    badge_color = "bg-rose-100 text-rose-800 border-rose-300"
                    tw_bg = "bg-rose-50"
                    txt_col = "text-rose-900"
                    hex_col = "#ffe4e6"
                    rek_text = (
                        f"Harga aktual {cname} di {rname} ({fmt_rp(act)}/{comm['satuan']}) berada DI ATAS "
                        f"Harga Acuan MH-WMA ({fmt_rp(mh)}) sebesar {fmt_pct(dev_pct)} ({fmt_diff_rp(dev_rp)}). "
                        f"Sinyal deviasi positif — perlu pemantauan kelancaran pasokan & kesiapan stabilisasi."
                    )
                else:
                    count_negatif += 1
                    r_neg += 1
                    status_key = "negatif"
                    status_label = "Deviasi Negatif"
                    status_short = "Negatif"
                    status_desc = "Aktual ≤ MH-WMA"
                    badge_color = "bg-sky-100 text-sky-800 border-sky-300"
                    tw_bg = "bg-sky-50"
                    txt_col = "text-sky-900"
                    hex_col = "#e0f2fe"
                    rek_text = (
                        f"Harga aktual {cname} di {rname} ({fmt_rp(act)}/{comm['satuan']}) berada PADA/DI BAWAH "
                        f"Harga Acuan MH-WMA ({fmt_rp(mh)}) sebesar {fmt_pct(dev_pct)} ({fmt_diff_rp(dev_rp)}). "
                        f"Tren harga berada di bawah acuan historis tertimbang (terkendali)."
                    )

                cell_obj = {
                    "comm_id": cid,
                    "comm_name": cname,
                    "comm_icon": comm["icon"],
                    "satuan": comm["satuan"],
                    "tersedia": True,
                    "model_ready": True,
                    "n_obs": metrics["n_obs"],
                    "n_mhwma_obs": metrics["n_mhwma_obs"],
                    "first_date": metrics["first_date"],
                    "mhwma_start_date": metrics["mhwma_start_date"],
                    "latest_date": metrics["latest_date"],
                    "harga_aktual": round(act),
                    "harga_aktual_str": fmt_rp(act),
                    "harga_wajar": round(mh),
                    "harga_wajar_str": fmt_rp(mh),
                    "ma_5": metrics["ma_5"],
                    "ma_5_str": fmt_rp(metrics["ma_5"]),
                    "ma_20": metrics["ma_20"],
                    "ma_20_str": fmt_rp(metrics["ma_20"]),
                    "ma_60": metrics["ma_60"],
                    "ma_60_str": fmt_rp(metrics["ma_60"]),
                    "ma_120": metrics["ma_120"],
                    "ma_120_str": fmt_rp(metrics["ma_120"]),
                    "deviasi_rp": round(dev_rp),
                    "deviasi_rp_str": fmt_diff_rp(dev_rp),
                    "deviasi_pct": dev_pct,
                    "deviasi_pct_str": fmt_pct(dev_pct),
                    "pct_hari_positif": metrics["pct_hari_positif"],
                    "peak_dev_pct": metrics["peak_dev_pct"],
                    "peak_dev_date": metrics["peak_dev_date"],
                    "durasi_hari": metrics["durasi_hari"],
                    "durasi_sejak_tgl": metrics["durasi_sejak_tgl"],
                    "n_spells": metrics["n_spells"],
                    "dpm_mean_region": metrics["dpm_mean_region"],
                    "status_key": status_key,
                    "status": status_label,
                    "status_short": status_short,
                    "status_desc": status_desc,
                    "alps": dev_pct,
                    "alps_str": fmt_pct(dev_pct),
                    "badge_color": badge_color,
                    "tailwind_bg": tw_bg,
                    "text_color": txt_col,
                    "hex": hex_col,
                    "rekomendasi": rek_text,
                }

                all_active_items.append({
                    "region_id": rid,
                    "region_name": rname,
                    "source": reg["source"],
                    "comm_id": cid,
                    "comm_name": cname,
                    "comm_icon": comm["icon"],
                    "satuan": comm["satuan"],
                    "harga_aktual": round(act),
                    "harga_aktual_str": fmt_rp(act),
                    "harga_wajar": round(mh),
                    "harga_wajar_str": fmt_rp(mh),
                    "deviasi_rp_str": fmt_diff_rp(dev_rp),
                    "deviasi_pct": dev_pct,
                    "deviasi_pct_str": fmt_pct(dev_pct),
                    "status_key": status_key,
                    "latest_date": metrics["latest_date"],
                })

            row_cells[cid] = cell_obj

        avg_dev = round(sum(r_devs) / len(r_devs), 2) if r_devs else 0.0
        matrix_rows.append({
            "region_id": rid,
            "region_name": rname,
            "pihps_key": reg.get("pihps_key", rname),
            "region_type": reg["type"],
            "group": reg["group"],
            "is_island": reg["is_island"],
            "source": reg["source"],
            "count_positif": r_pos,
            "count_negatif": r_neg,
            "count_na": r_na,
            "avg_deviasi_pct": avg_dev,
            "cells_by_comm": row_cells,
            "cells": [row_cells[c["id"]] for c in COMMODITIES_10],
        })

        print(
            f"-> {rname:<22} [{reg['source']:<13}] | Positif: {r_pos:>2} | Negatif: {r_neg:>2} | N/A: {r_na:>1} | Rerata Deviasi: {avg_dev:+.1f}%"
        )

    latest_date_str = max(all_global_latest_dates).strftime("%d/%m/%Y") if all_global_latest_dates else "09/11/2026"
    first_date_str = min(all_global_first_dates).strftime("%d/%m/%Y") if all_global_first_dates else "01/02/2024"

    sorted_pos = sorted(all_active_items, key=lambda x: x["deviasi_pct"], reverse=True)
    sorted_neg = sorted(all_active_items, key=lambda x: x["deviasi_pct"])
    model_active_total = count_positif + count_negatif
    pct_pos_global = round((count_positif / model_active_total) * 100.0, 1) if model_active_total > 0 else 0.0

    top_positif = [x for x in sorted_pos if x["status_key"] == "positif"][:6]
    top_negatif = [x for x in sorted_neg if x["status_key"] == "negatif"][:6]
    top_spike = top_positif[0] if top_positif else (sorted_pos[0] if sorted_pos else None)

    summary = {
        "tanggal_mulai": first_date_str,
        "tanggal_pantauan": latest_date_str,
        "total_wilayah": len(REGIONS_17),
        "total_komoditas": len(COMMODITIES_10),
        "total_sel": len(REGIONS_17) * len(COMMODITIES_10),
        "tersedia_count": tersedia_count,
        "model_active_count": model_active_total,
        "count_positif": count_positif,
        "count_negatif": count_negatif,
        "count_na": count_na,
        "pct_positif": pct_pos_global,
        "pct_negatif": round(100.0 - pct_pos_global, 1) if model_active_total > 0 else 0.0,
        "top_spike": top_spike,
        "top_positif": top_positif,
        "top_negatif": top_negatif,
        "model_params": {
            "alpha": MHWMA_ALPHA,
            "label_alpha": "Berimbang",
            "horizons": [5, 20, 60, 120],
            "weights_pct": {"ma5": 8.8, "ma20": 17.6, "ma60": 30.5, "ma120": 43.1},
        },
    }

    # ================= PEMETAAN KUADRAN PANGAN (DEVIASI vs DURASI PERGERAKAN) =================
    comm_d_bar = {}
    for comm in COMMODITIES_10:
        cid = comm["id"]
        sp_list = comm_spells.get(cid, [])
        comm_d_bar[cid] = round(sum(sp_list) / float(len(sp_list)), 1) if sp_list else 0.0

    global_k_counts = {"K1": 0, "K2": 0, "K3": 0, "K4": 0}
    by_commodity_map = {}
    for comm in COMMODITIES_10:
        cid = comm["id"]
        by_commodity_map[cid] = {
            "comm_id": cid,
            "comm_name": comm["name"],
            "comm_icon": comm["icon"],
            "satuan": comm["satuan"],
            "d_bar": comm_d_bar[cid],
            "total_spells": len(comm_spells.get(cid, [])),
            "k1": 0,
            "k2": 0,
            "k3": 0,
            "k4": 0,
            "na": 0,
            "active_count": 0,
            "points": [],
            "na_regions": [],
        }

    distribution_rows = []
    for row in matrix_rows:
        rid = row["region_id"]
        rname = row["region_name"]
        rk = {"K1": 0, "K2": 0, "K3": 0, "K4": 0}
        rna = 0
        items_by_k = {"K1": [], "K2": [], "K3": [], "K4": []}
        na_comms = []
        r_durs = []

        for comm in COMMODITIES_10:
            cid = comm["id"]
            c_bucket = by_commodity_map[cid]
            cell = row["cells_by_comm"][cid]
            d_bar_c = comm_d_bar[cid]

            if not cell.get("model_ready"):
                cell["kuadran_id"] = "na"
                cell["kuadran_label"] = "N/A"
                cell["kuadran_short"] = "N/A"
                cell["d_bar_komoditas"] = d_bar_c
                rna += 1
                c_bucket["na"] += 1
                c_bucket["na_regions"].append(rname)
                na_comms.append(comm["name"])
                continue

            is_pos = cell["status_key"] == "positif"
            dur_h = int(cell.get("durasi_hari", 0))
            is_pers = dur_h >= d_bar_c
            qid = ("K1" if is_pers else "K2") if is_pos else ("K3" if is_pers else "K4")
            qmeta = KUADRAN_META[qid]

            cell["kuadran_id"] = qid
            cell["kuadran_label"] = qmeta["title"]
            cell["kuadran_short"] = qmeta["short"]
            cell["d_bar_komoditas"] = d_bar_c

            global_k_counts[qid] += 1
            rk[qid] += 1
            r_durs.append(dur_h)

            short_reg = rname.replace("Kab. ", "").replace("Kota ", "")
            pt_obj = {
                "region_id": rid,
                "region_name": rname,
                "short_name": short_reg,
                "source": row["source"],
                "latest_date": cell["latest_date"],
                "harga_aktual": cell["harga_aktual"],
                "harga_aktual_str": cell["harga_aktual_str"],
                "harga_wajar": cell["harga_wajar"],
                "harga_wajar_str": cell["harga_wajar_str"],
                "deviasi_rp_str": cell["deviasi_rp_str"],
                "deviasi_pct": cell["deviasi_pct"],
                "deviasi_pct_str": cell["deviasi_pct_str"],
                "durasi_hari": dur_h,
                "durasi_sejak_tgl": cell.get("durasi_sejak_tgl", "-"),
                "dpm_mean_region": cell.get("dpm_mean_region", 0.0),
                "kuadran_id": qid,
                "kuadran_label": qmeta["title"],
            }
            c_bucket[qid.lower()] += 1
            c_bucket["active_count"] += 1
            c_bucket["points"].append(pt_obj)

            items_by_k[qid].append({
                "comm_id": cid,
                "comm_name": comm["name"],
                "comm_icon": comm["icon"],
                "satuan": comm["satuan"],
                "harga_aktual_str": cell["harga_aktual_str"],
                "harga_wajar_str": cell["harga_wajar_str"],
                "deviasi_pct": cell["deviasi_pct"],
                "deviasi_pct_str": cell["deviasi_pct_str"],
                "durasi_hari": dur_h,
                "d_bar": d_bar_c,
                "durasi_sejak_tgl": cell.get("durasi_sejak_tgl", "-"),
            })

        total_act_r = sum(rk.values())
        max_k_val = max(rk.values()) if total_act_r > 0 else 0
        # Prioritaskan K1 -> K2 -> K3 -> K4 jika ada skor seri agar risiko terpantau jelas
        dom_ids = [kid for kid in ["K1", "K2", "K3", "K4"] if rk[kid] == max_k_val and max_k_val > 0]
        dom_primary = dom_ids[0] if dom_ids else "K4"
        avg_dur_r = round(sum(r_durs) / float(len(r_durs)), 1) if r_durs else 0.0

        row["kuadran_counts"] = {"k1": rk["K1"], "k2": rk["K2"], "k3": rk["K3"], "k4": rk["K4"], "na": rna}
        row["kuadran_dominant"] = dom_primary

        distribution_rows.append({
            "region_id": rid,
            "region_name": rname,
            "source": row["source"],
            "k1": rk["K1"],
            "k2": rk["K2"],
            "k3": rk["K3"],
            "k4": rk["K4"],
            "na": rna,
            "total_active": total_act_r,
            "dominant_ids": dom_ids,
            "dominant_id": dom_primary,
            "dominant_label": KUADRAN_META[dom_primary]["title"],
            "dominant_count": max_k_val,
            "avg_deviasi_pct": row["avg_deviasi_pct"],
            "avg_durasi_hari": avg_dur_r,
            "na_comms": na_comms,
            "items_by_k": items_by_k,
        })

    # Urutkan default: K1 (Merah/Harga Tinggi Persisten) tertinggi -> K2 -> K3 -> abjad
    distribution_rows.sort(key=lambda r: (-r["k1"], -r["k2"], -r["k3"], r["region_name"]))

    kuadran_by_commodity = []
    for comm in COMMODITIES_10:
        c_b = by_commodity_map[comm["id"]]
        pts_list = c_b["points"]
        if pts_list:
            devs_only = [p["deviasi_pct"] for p in pts_list]
            durs_only = [p["durasi_hari"] for p in pts_list]
            c_b["min_dev_pct"] = min(devs_only)
            c_b["max_dev_pct"] = max(devs_only)
            c_b["max_durasi"] = max(durs_only)
            # Dominant quadrant inside this commodity
            c_counts = {"K1": c_b["k1"], "K2": c_b["k2"], "K3": c_b["k3"], "K4": c_b["k4"]}
            c_max = max(c_counts.values())
            c_dom = [k for k in ["K1", "K2", "K3", "K4"] if c_counts[k] == c_max][0]
            c_b["dominant_id"] = c_dom
            c_b["dominant_label"] = KUADRAN_META[c_dom]["title"]
            c_b["dominant_count"] = c_max
        else:
            c_b["min_dev_pct"] = 0.0
            c_b["max_dev_pct"] = 0.0
            c_b["max_durasi"] = 0
            c_b["dominant_id"] = "na"
            c_b["dominant_label"] = "N/A"
            c_b["dominant_count"] = 0
        kuadran_by_commodity.append(c_b)

    total_act_q = sum(global_k_counts.values())
    max_glob_k = max(global_k_counts.values()) if total_act_q > 0 else 0
    glob_dom_id = [k for k in ["K1", "K3", "K2", "K4"] if global_k_counts[k] == max_glob_k][0]
    most_k1_reg = distribution_rows[0] if distribution_rows else None
    most_k1_comm = max(kuadran_by_commodity, key=lambda x: (x["k1"], x["k2"])) if kuadran_by_commodity else None

    kuadran_payload = {
        "metodologi": {
            "deviasi_rule": "Deviasi > 0% (Aktual > MH-WMA) -> Harga Tinggi; Deviasi <= 0% (Aktual <= MH-WMA) -> Harga Rendah/Terkendali",
            "durasi_rule": "Durasi >= d̄ -> Persisten; Durasi < d̄ -> Sementara (d̄ = rerata durasi seluruh episode pembalikan lintas wilayah Sultra per komoditas)",
            "satuan_durasi": "hari survei berturut-turut",
            "quadrants": KUADRAN_META,
        },
        "summary": {
            "total_active": total_act_q,
            "count_k1": global_k_counts["K1"],
            "count_k2": global_k_counts["K2"],
            "count_k3": global_k_counts["K3"],
            "count_k4": global_k_counts["K4"],
            "count_na": count_na,
            "pct_k1": round((global_k_counts["K1"] / total_act_q) * 100.0, 1) if total_act_q > 0 else 0.0,
            "pct_k2": round((global_k_counts["K2"] / total_act_q) * 100.0, 1) if total_act_q > 0 else 0.0,
            "pct_k3": round((global_k_counts["K3"] / total_act_q) * 100.0, 1) if total_act_q > 0 else 0.0,
            "pct_k4": round((global_k_counts["K4"] / total_act_q) * 100.0, 1) if total_act_q > 0 else 0.0,
            "dominant_id": glob_dom_id,
            "dominant_label": KUADRAN_META[glob_dom_id]["title"],
            "dominant_count": max_glob_k,
            "most_k1_region": {
                "region_id": most_k1_reg["region_id"],
                "region_name": most_k1_reg["region_name"],
                "k1": most_k1_reg["k1"],
                "total_active": most_k1_reg["total_active"],
            } if most_k1_reg else None,
            "most_k1_comm": {
                "comm_id": most_k1_comm["comm_id"],
                "comm_name": most_k1_comm["comm_name"],
                "k1": most_k1_comm["k1"],
                "active_count": most_k1_comm["active_count"],
                "d_bar": most_k1_comm["d_bar"],
            } if most_k1_comm else None,
        },
        "by_commodity": kuadran_by_commodity,
        "distribution_rows": distribution_rows,
    }

    payload = {
        "metadata": {
            "judul": "Matriks Deteksi Lonjakan Harga MH-WMA (17 Kabupaten/Kota Se-Sulawesi Tenggara)",
            "metodologi": "Multi-Horizon Power Weighted Moving Average (MH-WMA) dengan MA 5, 20, 60, 120 dan alpha = 0,5 (Berimbang)",
            "sumber_data": "PIHPS Bank Indonesia (Kota Kendari & Kota Baubau) & SP2KP Kemendag RI (15 Kabupaten)",
            "tanggal_mulai": first_date_str,
            "tanggal_terkini": latest_date_str,
            "waktu_generate": datetime.now().isoformat(),
        },
        "summary": summary,
        "commodities": COMMODITIES_10,
        "rows": matrix_rows,
        "kuadran": kuadran_payload,
    }

    tmp_path = OUT_PATH + ".tmp"
    with open(tmp_path, "w", encoding="utf-8") as f:
        json.dump(payload, f, indent=2, ensure_ascii=False)
    os.replace(tmp_path, OUT_PATH)

    print("\n" + "=" * 85)
    print(f"[SUKSES] Matriks MH-WMA tersimpan ke: {OUT_PATH}")
    print(
        f"Aktif Model: {model_active_total}/170 | Deviasi Positif: {count_positif} ({pct_pos_global}%) | "
        f"Deviasi Negatif: {count_negatif} | Survei N/A: {count_na}"
    )
    if top_spike:
        print(
            f"Lonjakan Tertinggi: {top_spike['comm_name']} - {top_spike['region_name']} "
            f"({top_spike['deviasi_pct_str']} | {top_spike['harga_aktual_str']} vs MH-WMA {top_spike['harga_wajar_str']})"
        )
    return payload


if __name__ == "__main__":
    generate_alps_17_matrix()
