#!/usr/bin/env python3
"""
Simulasi & Validasi Out-of-Sample Backtesting Komparatif 4 Model:
ARIMA vs Meta Prophet vs ARIMAX vs SARIMAX
EWS Inflasi Pangan Sulawesi Tenggara

Pelatihan: Data Historis Harian 2024–2025 (522 Hari Kerja)
Pengujian: 7 Hari Kerja Pertama Tahun 2026 (02 Jan s.d. 12 Jan 2026)
Dibandingkan langsung secara head-to-head dengan realisasi harga riil tahun 2026.
"""

import os
import sys
import json
import math
import zipfile
from datetime import datetime, date, timedelta
import xml.sax.saxutils as saxutils

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DATA_DIR = os.path.join(BASE_DIR, "data")
ARTIFACT_DIR = "/Users/regaprasetyo/.gemini/antigravity/brain/45b29b5e-87d9-439a-b46b-f9c22bf36c3e"

DAILY_PRICE_PATH = os.path.join(DATA_DIR, "bi_daily_2024_2026.json")
DAILY_WEATHER_PATH = os.path.join(DATA_DIR, "weather_daily_2024_2026.json")
OUTPUT_JSON_PATH = os.path.join(DATA_DIR, "backtest_all_models_2026.json")
OUTPUT_EXCEL_PATH = os.path.join(BASE_DIR, "hasil_evaluasi_4_model_2026.xlsx")

from arimax_sarimax_forecast import (
    load_aligned_data, get_exog_vector_for_commodity,
    auto_select_arimax, auto_select_sarimax,
    forecast_arimax_7_steps, forecast_sarimax_7_steps,
    TARGET_COMMODITIES, COMMODITY_ICONS, COMMODITY_UNITS,
    solve_ols, is_stationary, is_invertible
)

def fit_arima(y, p, d, q):
    w = [y[i] - y[i-1] for i in range(1, len(y))]
    N = len(w)
    var_w = sum((x - sum(w)/N)**2 for x in w) / N
    if var_w < 1e-8:
        return {'order': (0, d, 0), 'phi': [], 'theta': [], 'sigma2': 0.0, 'aic': 0.0, 'w': w, 'resids': [0.0]*N}
    m = max(p + q + 2, 4)
    X_ar = [[w[t - i] for i in range(1, m + 1)] for t in range(m, N)]
    y_ar = [w[t] for t in range(m, N)]
    beta_ar = solve_ols(X_ar, y_ar)
    e = [0.0] * m
    for t in range(m, N):
        pred = sum(beta_ar[i] * w[t - 1 - i] for i in range(m))
        e.append(w[t] - pred)
    start_t = max(p, q, 1)
    X = []
    y_reg = []
    for t in range(start_t, N):
        row = [w[t - i] for i in range(1, p + 1)] + [e[t - j] for j in range(1, q + 1)]
        if not row: row = [1.0]
        X.append(row)
        y_reg.append(w[t])
    beta = solve_ols(X, y_reg)
    phi = beta[:p]
    theta = beta[p:p+q]
    if not is_stationary(phi) or not is_invertible(theta):
        return {'order': (p, d, q), 'aic': float('inf')}
    fitted_w = [0.0] * N
    resids = [0.0] * N
    for t in range(N):
        pred = sum(phi[i] * w[t - 1 - i] for i in range(min(p, t))) + sum(theta[j] * resids[t - 1 - j] for j in range(min(q, t)))
        fitted_w[t] = pred
        resids[t] = w[t] - pred
        if abs(resids[t]) > 1e8: return {'order': (p, d, q), 'aic': float('inf')}
    sigma2 = sum(r**2 for r in resids[start_t:]) / (N - start_t)
    if sigma2 <= 0: sigma2 = 1e-6
    k_params = p + q + 1
    llf = -0.5 * (N - start_t) * (math.log(2 * math.pi * sigma2) + 1.0)
    aic = 2 * k_params - 2 * llf
    return {'order': (p, d, q), 'phi': phi, 'theta': theta, 'sigma2': sigma2, 'aic': aic, 'w': w, 'resids': resids}

def forecast_arima_7(y, model):
    p, d, q = model['order']
    phi, theta, w, resids = model['phi'], model['theta'], model['w'], model['resids']
    N = len(w)
    future_w = []
    curr_y = y[-1]
    fc_y = []
    for h in range(1, 8):
        pred_w = 0.0
        for i in range(1, p + 1):
            lag = h - i
            val = future_w[lag - 1] if lag > 0 else (w[N - 1 + lag] if 0 <= N - 1 + lag < N else 0.0)
            pred_w += phi[i - 1] * val
        for j in range(1, q + 1):
            lag = h - j
            val = 0.0 if lag > 0 else (resids[N - 1 + lag] if 0 <= N - 1 + lag < N else 0.0)
            pred_w += theta[j - 1] * val
        future_w.append(pred_w)
        curr_y += pred_w
        fc_y.append(round(curr_y / 50.0) * 50)
    return fc_y

def fit_meta_prophet(dates, prices, n_changepoints=15):
    N = len(prices)
    t = [i / (N - 1) for i in range(N)]
    dts = [datetime.strptime(d, '%d/%m/%Y').date() for d in dates]
    doys = [dt.timetuple().tm_yday for dt in dts]
    doms = [dt.day for dt in dts]
    dows = [dt.weekday() for dt in dts]
    cp_indices = [int((i + 1) * (0.8 * N) / (n_changepoints + 1)) for i in range(n_changepoints)]
    cp_t = [t[idx] for idx in cp_indices]
    X = []
    for i in range(N):
        row = [1.0, t[i]]
        for cp in cp_t: row.append(max(0.0, t[i] - cp))
        for order in range(1, 6):
            arg = 2.0 * math.pi * order * doys[i] / 365.25
            row.append(math.cos(arg)); row.append(math.sin(arg))
        for order in range(1, 3):
            arg = 2.0 * math.pi * order * doms[i] / 30.5
            row.append(math.cos(arg)); row.append(math.sin(arg))
        for order in range(1, 3):
            arg = 2.0 * math.pi * order * dows[i] / 7.0
            row.append(math.cos(arg)); row.append(math.sin(arg))
        X.append(row)
    beta = solve_ols(X, prices, ridge=1e-2)
    return {'beta': beta, 'cp_t': cp_t, 'N_train': N}

def forecast_prophet_7(model, future_dates, last_price):
    beta = model['beta']
    cp_t = model['cp_t']
    N_train = model['N_train']
    dts = [datetime.strptime(d, '%d/%m/%Y').date() for d in future_dates]
    fc_y = []
    for h, dt in enumerate(dts, 1):
        t_val = (N_train - 1 + h) / (N_train - 1)
        doy = dt.timetuple().tm_yday
        dom = dt.day
        dow = dt.weekday()
        row = [1.0, t_val]
        for cp in cp_t: row.append(max(0.0, t_val - cp))
        for order in range(1, 6):
            arg = 2.0 * math.pi * order * doy / 365.25
            row.append(math.cos(arg)); row.append(math.sin(arg))
        for order in range(1, 3):
            arg = 2.0 * math.pi * order * dom / 30.5
            row.append(math.cos(arg)); row.append(math.sin(arg))
        for order in range(1, 3):
            arg = 2.0 * math.pi * order * dow / 7.0
            row.append(math.cos(arg)); row.append(math.sin(arg))
        val = sum(beta[i] * row[i] for i in range(len(row)))
        fc_y.append(round(val / 50.0) * 50)
    return fc_y

def run_backtest_all_models():
    print("-> Menjalankan Out-of-Sample Backtesting 4 Model (ARIMA, Prophet, ARIMAX, SARIMAX)...")
    parsed_dates, price_data, weather_by_date = load_aligned_data()

    # Pisahkan train (2024-2025) dan test (7 hari kerja pertama 2026)
    train_dates = [d for d in parsed_dates if d[0].year in [2024, 2025]]
    test_dates = [d for d in parsed_dates if d[0].year == 2026][:7]

    print(f"   Jumlah Data Latih (In-Sample): {len(train_dates)} hari (02 Jan 2024 s.d. 31 Des 2025)")
    print(f"   Jumlah Data Uji (Out-of-Sample): {len(test_dates)} hari ({test_dates[0][1]} s.d. {test_dates[-1][1]})")

    results = {}

    for cname in TARGET_COMMODITIES:
        row = next((r for r in price_data if r.get("name") == cname), None)
        if not row: continue

        y_train = []
        for dt_obj, dk in train_dates:
            v = float(str(row.get(dk, "0")).replace(",", "").replace(".", "").strip())
            y_train.append(v)

        y_test_actual = []
        test_labels = []
        for dt_obj, dk in test_dates:
            v = float(str(row.get(dk, "0")).replace(",", "").replace(".", "").strip())
            y_test_actual.append(v)
            HARI_ID = {0: "Senin", 1: "Selasa", 2: "Rabu", 3: "Kamis", 4: "Jumat"}
            test_labels.append({"tanggal": dk, "hari": HARI_ID[dt_obj.weekday()], "dt": dt_obj})

        # Matriks eksogen train
        X_train = []
        for dt_obj, dk in train_dates:
            d_str = dt_obj.strftime("%Y-%m-%d")
            w_info = weather_by_date.get(d_str, {"dt": dt_obj, "rain_kendari": 0.0, "temp_kendari": 28.0, "rain_konawe_lag7": 0.0, "hth_konawe": 0, "rain_kolut_lag7": 0.0, "hth_kolut": 0, "wind_baubau": 15.0, "is_hbkn": 0.0, "is_jumat": 0.0})
            X_train.append(get_exog_vector_for_commodity(cname, w_info))

        # Delta X untuk test horizon
        future_deltas = []
        last_exog = X_train[-1]
        for dt_obj, dk in test_dates:
            d_str = dt_obj.strftime("%Y-%m-%d")
            w_info = weather_by_date.get(d_str, {"dt": dt_obj, "rain_kendari": 0.0, "temp_kendari": 28.0, "rain_konawe_lag7": 0.0, "hth_konawe": 0, "rain_kolut_lag7": 0.0, "hth_kolut": 0, "wind_baubau": 15.0, "is_hbkn": 0.0, "is_jumat": 0.0})
            fut_vec = get_exog_vector_for_commodity(cname, w_info)
            delta_X = [fut_vec[k] - last_exog[k] for k in range(len(fut_vec))]
            future_deltas.append(delta_X)
            last_exog = fut_vec

        # 1. ARIMA
        best_arima = None
        best_aic = float('inf')
        for p, d, q in [(2,1,0), (0,1,2), (2,1,1), (2,1,2), (1,1,1)]:
            m = fit_arima(y_train, p, d, q)
            if m.get('aic', float('inf')) < best_aic:
                best_aic = m['aic']
                best_arima = m
        fc_arima = forecast_arima_7(y_train, best_arima)

        # 2. Meta Prophet
        train_d_strs = [dk for _, dk in train_dates]
        model_prophet = fit_meta_prophet(train_d_strs, y_train)
        test_d_strs = [dk for _, dk in test_dates]
        fc_prophet = forecast_prophet_7(model_prophet, test_d_strs, y_train[-1])

        # 3. ARIMAX
        model_arimax = auto_select_arimax(y_train, X_train)
        proj_arimax = forecast_arimax_7_steps(y_train, model_arimax, future_deltas)
        fc_arimax = [p["prediksi"] for p in proj_arimax]

        # 4. SARIMAX
        model_sarimax = auto_select_sarimax(y_train, X_train)
        proj_sarimax = forecast_sarimax_7_steps(y_train, model_sarimax, future_deltas)
        fc_sarimax = [p["prediksi"] for p in proj_sarimax]

        # Evaluasi MAPE Out-of-Sample
        def calc_mape(actuals, preds):
            return sum(abs(a - p) / a for a, p in zip(actuals, preds)) / len(actuals) * 100.0

        mape_arima = calc_mape(y_test_actual, fc_arima)
        mape_prophet = calc_mape(y_test_actual, fc_prophet)
        mape_arimax = calc_mape(y_test_actual, fc_arimax)
        mape_sarimax = calc_mape(y_test_actual, fc_sarimax)

        acc_arima = round(100.0 - mape_arima, 2)
        acc_prophet = round(100.0 - mape_prophet, 2)
        acc_arimax = round(100.0 - mape_arimax, 2)
        acc_sarimax = round(100.0 - mape_sarimax, 2)

        models_acc = {
            "ARIMA": acc_arima,
            "Meta Prophet": acc_prophet,
            "ARIMAX": acc_arimax,
            "SARIMAX": acc_sarimax
        }
        best_model_name = max(models_acc, key=models_acc.get)

        rincian_7_hari = []
        for step in range(7):
            act = y_test_actual[step]
            rincian_7_hari.append({
                "step": step + 1,
                "hari": test_labels[step]["hari"],
                "tanggal": test_labels[step]["tanggal"],
                "harga_realtime_2026": act,
                "proyeksi_arima": fc_arima[step],
                "selisih_arima": round(fc_arima[step] - act),
                "proyeksi_prophet": fc_prophet[step],
                "selisih_prophet": round(fc_prophet[step] - act),
                "proyeksi_arimax": fc_arimax[step],
                "selisih_arimax": round(fc_arimax[step] - act),
                "proyeksi_sarimax": fc_sarimax[step],
                "selisih_sarimax": round(fc_sarimax[step] - act)
            })

        results[cname] = {
            "komoditas": cname,
            "satuan": COMMODITY_UNITS.get(cname, "kg"),
            "icon": COMMODITY_ICONS.get(cname, "📦"),
            "harga_terakhir_2025": y_train[-1],
            "rata_rata_realtime_2026": round(sum(y_test_actual) / 7.0),
            "akurasi_arima": acc_arima,
            "mape_arima": round(mape_arima, 2),
            "akurasi_prophet": acc_prophet,
            "mape_prophet": round(mape_prophet, 2),
            "akurasi_arimax": acc_arimax,
            "mape_arimax": round(mape_arimax, 2),
            "akurasi_sarimax": acc_sarimax,
            "mape_sarimax": round(mape_sarimax, 2),
            "best_model": best_model_name,
            "rincian_7_hari": rincian_7_hari
        }

        print(f"   [OK] {cname:15s} | ARIMA: {acc_arima:5.2f}% | Prophet: {acc_prophet:5.2f}% | ARIMAX: {acc_arimax:5.2f}% | SARIMAX: {acc_sarimax:5.2f}% | Best: {best_model_name}")

    with open(OUTPUT_JSON_PATH, "w", encoding="utf-8") as f:
        json.dump(results, f, indent=2, ensure_ascii=False)
    print(f"[OK] Hasil Backtest 4 Model disimpan di: {OUTPUT_JSON_PATH}")

    # Export Excel
    export_backtest_4_models_excel(results)

def col_letter(col_idx):
    result = ""
    while col_idx > 0:
        col_idx, remainder = divmod(col_idx - 1, 26)
        result = chr(65 + remainder) + result
    return result

def escape_xml(s):
    return saxutils.escape(str(s)) if s is not None else ""

def build_sheet_xml(sheet_data_rows, col_widths=None):
    xml = ['<?xml version="1.0" encoding="UTF-8" standalone="yes"?>']
    xml.append('<worksheet xmlns="http://schemas.openxmlformats.org/spreadsheetml/2006/main">')
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
            if cell is None: continue
            val, c_type, style_id = cell
            cell_ref = f"{col_letter(col_idx)}{row_idx}"
            s_attr = f' s="{style_id}"' if style_id is not None else ''
            if c_type == 'inlineStr':
                xml.append(f'      <c r="{cell_ref}" t="inlineStr"{s_attr}><is><t>{escape_xml(val)}</t></is></c>')
            elif c_type == 'number':
                xml.append(f'      <c r="{cell_ref}"{s_attr}><v>{val}</v></c>')
        xml.append('    </row>')
    xml.append('  </sheetData>')
    xml.append('</worksheet>')
    return '\n'.join(xml)

def build_styles_xml():
    return '''<?xml version="1.0" encoding="UTF-8" standalone="yes"?>
<styleSheet xmlns="http://schemas.openxmlformats.org/spreadsheetml/2006/main">
  <numFmts count="2">
    <numFmt numFmtId="164" formatCode="#,##0"/>
    <numFmt numFmtId="165" formatCode="0.00%"/>
  </numFmts>
  <fonts count="4">
    <font><sz val="10"/><name val="Segoe UI"/><color rgb="FF1E293B"/></font>
    <font><b/><sz val="10"/><name val="Segoe UI"/><color rgb="FFFFFFFF"/></font>
    <font><b/><sz val="13"/><name val="Segoe UI"/><color rgb="FF0F172A"/></font>
    <font><i/><sz val="9.5"/><name val="Segoe UI"/><color rgb="FF64748B"/></font>
  </fonts>
  <fills count="4">
    <fill><patternFill patternType="none"/></fill>
    <fill><patternFill patternType="gray125"/></fill>
    <fill><patternFill patternType="solid"><fgColor rgb="FF1E3A8A"/></patternFill></fill>
    <fill><patternFill patternType="solid"><fgColor rgb="FFF1F5F9"/></patternFill></fill>
  </fills>
  <borders count="2">
    <border><left/><right/><top/><bottom/></border>
    <border>
      <left style="thin"><color rgb="FFE2E8F0"/></left>
      <right style="thin"><color rgb="FFE2E8F0"/></right>
      <top style="thin"><color rgb="FFE2E8F0"/></top>
      <bottom style="thin"><color rgb="FFE2E8F0"/></bottom>
    </border>
  </borders>
  <cellStyleXfs count="1"><xf numFmtId="0" fontId="0" fillId="0" borderId="0"/></cellStyleXfs>
  <cellXfs count="9">
    <xf numFmtId="0" fontId="0" fillId="0" borderId="0" xfId="0"/>
    <xf numFmtId="0" fontId="1" fillId="2" borderId="1" xfId="0" applyFont="1" applyFill="1" applyBorder="1" applyAlignment="1"><alignment horizontal="center" vertical="center"/></xf>
    <xf numFmtId="0" fontId="0" fillId="0" borderId="1" xfId="0" applyBorder="1"/>
    <xf numFmtId="0" fontId="0" fillId="0" borderId="1" xfId="0" applyBorder="1" applyAlignment="1"><alignment horizontal="center"/></xf>
    <xf numFmtId="164" fontId="0" fillId="0" borderId="1" xfId="0" applyBorder="1" applyAlignment="1"><alignment horizontal="right"/></xf>
    <xf numFmtId="165" fontId="0" fillId="0" borderId="1" xfId="0" applyBorder="1" applyAlignment="1"><alignment horizontal="right"/></xf>
    <xf numFmtId="0" fontId="2" fillId="0" borderId="0" xfId="0" applyFont="1"/>
    <xf numFmtId="0" fontId="3" fillId="0" borderId="0" xfId="0" applyFont="1"/>
    <xf numFmtId="0" fontId="0" fillId="3" borderId="1" xfId="0" applyFill="1" applyBorder="1"/>
  </cellXfs>
</styleSheet>'''

def export_backtest_4_models_excel(results):
    sheet_names = ["Komparasi 4 Model", "Rincian 7 Hari 2026"]
    sheets_xml = []

    # Sheet 1: Komparasi 4 Model
    s1_rows = [
        [("EVALUASI KOMPARATIF 4 MODEL: ARIMA vs PROPHET vs ARIMAX vs SARIMAX", "inlineStr", 6)],
        [("Pelatihan: 2024–2025 (522 Hari) | Pengujian: 7 Hari Pertama 2026 (02 Jan - 12 Jan 2026) | Bank Indonesia & BMKG", "inlineStr", 7)],
        [],
        [
            ("Komoditas", "inlineStr", 1),
            ("Satuan", "inlineStr", 1),
            ("Akurasi ARIMA (%)", "inlineStr", 1),
            ("Akurasi Prophet (%)", "inlineStr", 1),
            ("Akurasi ARIMAX (%)", "inlineStr", 1),
            ("Akurasi SARIMAX (%)", "inlineStr", 1),
            ("Model Terbaik", "inlineStr", 1),
            ("Harga Akhir 2025", "inlineStr", 1),
            ("Realisasi 2026 (Avg)", "inlineStr", 1)
        ]
    ]

    for cname, res in results.items():
        s1_rows.append([
            (f"{res.get('icon', '')} {cname}", "inlineStr", 2),
            (res.get("satuan", "kg"), "inlineStr", 3),
            (res["akurasi_arima"] / 100.0, "number", 5),
            (res["akurasi_prophet"] / 100.0, "number", 5),
            (res["akurasi_arimax"] / 100.0, "number", 5),
            (res["akurasi_sarimax"] / 100.0, "number", 5),
            (res["best_model"], "inlineStr", 3),
            (res["harga_terakhir_2025"], "number", 4),
            (res["rata_rata_realtime_2026"], "number", 4)
        ])

    s1_widths = [22, 10, 18, 18, 18, 18, 16, 18, 20]
    sheets_xml.append(build_sheet_xml(s1_rows, s1_widths))

    # Sheet 2: Rincian 7 Hari 2026
    s2_rows = [
        [("RINCIAN 7 HARI KERJA PERTAMA 2026: REALTIME vs 4 MODEL PROYEKSI", "inlineStr", 6)],
        [("Membandingkan angka riil pasar PIHPS 2026 dengan hasil simulasi masing-masing model", "inlineStr", 7)],
        [],
        [
            ("Komoditas", "inlineStr", 1),
            ("Step", "inlineStr", 1),
            ("Hari", "inlineStr", 1),
            ("Tanggal", "inlineStr", 1),
            ("Harga Riil 2026", "inlineStr", 1),
            ("Proyeksi ARIMA", "inlineStr", 1),
            ("Selisih ARIMA", "inlineStr", 1),
            ("Proyeksi Prophet", "inlineStr", 1),
            ("Selisih Prophet", "inlineStr", 1),
            ("Proyeksi ARIMAX", "inlineStr", 1),
            ("Selisih ARIMAX", "inlineStr", 1),
            ("Proyeksi SARIMAX", "inlineStr", 1),
            ("Selisih SARIMAX", "inlineStr", 1)
        ]
    ]

    for cname, res in results.items():
        for r in res.get("rincian_7_hari", []):
            s2_rows.append([
                (f"{res.get('icon', '')} {cname}", "inlineStr", 2),
                (r["step"], "number", 3),
                (r["hari"], "inlineStr", 3),
                (r["tanggal"], "inlineStr", 3),
                (r["harga_realtime_2026"], "number", 4),
                (r["proyeksi_arima"], "number", 4),
                (r["selisih_arima"], "number", 4),
                (r["proyeksi_prophet"], "number", 4),
                (r["selisih_prophet"], "number", 4),
                (r["proyeksi_arimax"], "number", 4),
                (r["selisih_arimax"], "number", 4),
                (r["proyeksi_sarimax"], "number", 4),
                (r["selisih_sarimax"], "number", 4)
            ])

    s2_widths = [20, 8, 10, 14, 16, 16, 14, 16, 14, 16, 14, 16, 14]
    sheets_xml.append(build_sheet_xml(s2_rows, s2_widths))

    content_types_xml = ['<?xml version="1.0" encoding="UTF-8" standalone="yes"?>', '<Types xmlns="http://schemas.openxmlformats.org/package/2006/content-types">', '  <Default Extension="rels" ContentType="application/vnd.openxmlformats-package.relationships+xml"/>', '  <Default Extension="xml" ContentType="application/xml"/>', '  <Override PartName="/xl/workbook.xml" ContentType="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet.main+xml"/>', '  <Override PartName="/xl/styles.xml" ContentType="application/vnd.openxmlformats-officedocument.spreadsheetml.styles+xml"/>', '  <Override PartName="/xl/worksheets/sheet1.xml" ContentType="application/vnd.openxmlformats-officedocument.spreadsheetml.worksheet+xml"/>', '  <Override PartName="/xl/worksheets/sheet2.xml" ContentType="application/vnd.openxmlformats-officedocument.spreadsheetml.worksheet+xml"/>', '</Types>']
    rels_xml = '<?xml version="1.0" encoding="UTF-8" standalone="yes"?><Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships"><Relationship Id="rId1" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/officeDocument" Target="xl/workbook.xml"/></Relationships>'
    workbook_rels_xml = ['<?xml version="1.0" encoding="UTF-8" standalone="yes"?><Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships"><Relationship Id="rIdStyles" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/styles" Target="styles.xml"/><Relationship Id="rIdSheet1" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/worksheet" Target="worksheets/sheet1.xml"/><Relationship Id="rIdSheet2" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/worksheet" Target="worksheets/sheet2.xml"/></Relationships>']
    workbook_xml = ['<?xml version="1.0" encoding="UTF-8" standalone="yes"?><workbook xmlns="http://schemas.openxmlformats.org/spreadsheetml/2006/main"><sheets><sheet name="Komparasi 4 Model" sheetId="1" r:id="rIdSheet1"/><sheet name="Rincian 7 Hari 2026" sheetId="2" r:id="rIdSheet2"/></sheets></workbook>']

    for out_path in [OUTPUT_EXCEL_PATH, os.path.join(DATA_DIR, "hasil_evaluasi_4_model_2026.xlsx")]:
        with zipfile.ZipFile(out_path, 'w', compression=zipfile.ZIP_DEFLATED) as zf:
            zf.writestr('[Content_Types].xml', '\n'.join(content_types_xml))
            zf.writestr('_rels/.rels', rels_xml)
            zf.writestr('xl/_rels/workbook.xml.rels', '\n'.join(workbook_rels_xml))
            zf.writestr('xl/workbook.xml', '\n'.join(workbook_xml))
            zf.writestr('xl/styles.xml', build_styles_xml())
            zf.writestr('xl/worksheets/sheet1.xml', sheets_xml[0])
            zf.writestr('xl/worksheets/sheet2.xml', sheets_xml[1])
        print(f"[OK] Berkas Excel Komparasi 4 Model tersimpan di: {out_path}")

    if os.path.exists(ARTIFACT_DIR):
        import shutil
        shutil.copy2(OUTPUT_EXCEL_PATH, os.path.join(ARTIFACT_DIR, "hasil_evaluasi_4_model_2026.xlsx"))

if __name__ == "__main__":
    run_backtest_all_models()
