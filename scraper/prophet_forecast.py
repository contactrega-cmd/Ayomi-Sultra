#!/usr/bin/env python3
"""
Modul Pemodelan Machine Learning Meta Prophet (Additive GAM Time Series)
EWS Inflasi Pangan Sulawesi Tenggara
Memproyeksikan harga 10 kelompok komoditas pangan 7 hari kerja ke depan menggunakan
dekomposisi aditif multi-musiman: 
  y(t) = Trend(t) + Yearly_Seasonality(t) + Monthly_Seasonality(t) + Weekly_Seasonality(t) + Error(t).
Dilatih pada data historis harian BI PIHPS dari 2024 hingga 2026 (~724 observasi).
"""

import os
import sys
import json
import math
import datetime

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DATA_DIR = os.path.join(BASE_DIR, "data")
DAILY_CACHE_PATH = os.path.join(DATA_DIR, "bi_daily_2024_2026.json")
OUTPUT_PROPHET_PATH = os.path.join(DATA_DIR, "prophet_forecast_all_commodities.json")

def load_daily_data():
    if os.path.exists(DAILY_CACHE_PATH):
        try:
            with open(DAILY_CACHE_PATH, "r", encoding="utf-8") as f:
                data = json.load(f)
            if data and data.get("data"):
                return data
        except Exception:
            pass
    return None

def solve_ridge_regression(X, y, alpha=0.6):
    """Menyelesaikan estimasi regularisasi Ridge (X^T X + alpha * I) beta = X^T y."""
    n = len(X)
    k = len(X[0])
    XtX = [[sum(X[r][i] * X[r][j] for r in range(n)) for j in range(k)] for i in range(k)]
    for i in range(k):
        XtX[i][i] += alpha
    Xty = [sum(X[r][i] * y[r] for r in range(n)) for i in range(k)]
    
    A = [XtX[i] + [Xty[i]] for i in range(k)]
    for i in range(k):
        max_r = max(range(i, k), key=lambda r: abs(A[r][i]))
        A[i], A[max_r] = A[max_r], A[i]
        pivot = A[i][i]
        if abs(pivot) < 1e-12:
            return [0.0] * k
        for j in range(i, k + 1):
            A[i][j] /= pivot
        for r in range(k):
            if r != i:
                factor = A[r][i]
                for j in range(i, k + 1):
                    A[r][j] -= factor * A[i][j]
    return [A[i][-1] for i in range(k)]

def fit_meta_prophet_model(dates, prices, n_changepoints=20):
    """
    Mengestimasi arsitektur Meta Prophet GAM Multi-Musiman:
    1. Piecewise linear trend dengan n_changepoints adaptif
    2. Yearly seasonality menggunakan deret Fourier N=5 (periode 365.25 hari)
    3. Monthly seasonality menggunakan deret Fourier N=2 (periode 30.5 hari)
    4. Weekly seasonality menggunakan deret Fourier N=2 (periode 7 hari)
    5. Parametric residual uncertainty interval (95% CI)
    """
    N = len(prices)
    last_price = prices[-1]

    # Kasus khusus: jika harga konstan (variansi 0)
    if max(prices) == min(prices):
        fitted = [last_price] * N
        return {
            "model_name": "Meta Prophet (Constant Trend)",
            "changepoints_count": 0,
            "fitted": fitted,
            "resids": [0.0] * N,
            "sigma": 0.0,
            "mape": 0.0,
            "rmse": 0.0,
            "is_constant": True,
            "beta": [last_price],
            "cp_t": []
        }

    # Waktu t dinormalisasi [0, 1]
    t = [i / (N - 1) for i in range(N)]
    dts = [datetime.datetime.strptime(d, '%d/%m/%Y') for d in dates]
    doys = [dt.timetuple().tm_yday for dt in dts]
    doms = [dt.day for dt in dts]
    dows = [dt.weekday() for dt in dts]

    # Changepoints terdistribusi di 80% rentang data pertama
    cp_indices = [int((i + 1) * (0.8 * N) / (n_changepoints + 1)) for i in range(n_changepoints)]
    cp_t = [t[idx] for idx in cp_indices]

    # Matriks fitur X multi-musiman
    X = []
    for i in range(N):
        row = [1.0, t[i]]
        # Piecewise trend
        for cp in cp_t:
            row.append(max(0.0, t[i] - cp))
        # Yearly Seasonality (N=5)
        for order in range(1, 6):
            arg = 2.0 * math.pi * order * doys[i] / 365.25
            row.append(math.cos(arg))
            row.append(math.sin(arg))
        # Monthly Seasonality (N=2)
        for order in range(1, 3):
            arg = 2.0 * math.pi * order * doms[i] / 30.5
            row.append(math.cos(arg))
            row.append(math.sin(arg))
        # Weekly Seasonality (N=2)
        for order in range(1, 3):
            arg = 2.0 * math.pi * order * dows[i] / 7.0
            row.append(math.cos(arg))
            row.append(math.sin(arg))
        X.append(row)

    beta = solve_ridge_regression(X, prices, alpha=0.6)
    fitted = [sum(X[i][j] * beta[j] for j in range(len(beta))) for i in range(N)]
    resids = [prices[i] - fitted[i] for i in range(N)]
    sigma = math.sqrt(sum(r**2 for r in resids) / max(1, N - len(beta)))
    mape = sum(abs(prices[i] - fitted[i]) / prices[i] for i in range(N)) / N * 100.0
    rmse = math.sqrt(sum(r**2 for r in resids) / N)

    return {
        "model_name": f"Meta Prophet GAM ({n_changepoints} Changepoints + Multi-Seasonal)",
        "changepoints_count": n_changepoints,
        "fitted": fitted,
        "resids": resids,
        "sigma": sigma,
        "mape": round(mape, 2),
        "rmse": round(rmse, 2),
        "is_constant": False,
        "beta": beta,
        "cp_t": cp_t,
        "last_resid": resids[-1],
        "dt_step": 1.0 / (N - 1)
    }

def run_prophet_forecasting():
    print("=" * 80)
    print("PEMODELAN MACHINE LEARNING META PROPHET: 10 KOMODITAS PANGAN SULTRA (2024-2026)")
    print("=" * 80)

    raw_data = load_daily_data()
    if not raw_data or not raw_data.get("data"):
        print("[PROPHET] Data harian 2024-2026 tidak ditemukan, membatalkan proses.")
        return False

    rows = raw_data.get("data", [])
    results = {}

    target_commodities = [
        {"name": "Beras", "icon": "🌾", "unit": "kg"},
        {"name": "Daging Ayam", "icon": "🍗", "unit": "kg"},
        {"name": "Daging Sapi", "icon": "🥩", "unit": "kg"},
        {"name": "Telur Ayam", "icon": "🥚", "unit": "kg"},
        {"name": "Bawang Merah", "icon": "🧅", "unit": "kg"},
        {"name": "Bawang Putih", "icon": "🧄", "unit": "kg"},
        {"name": "Cabai Merah", "icon": "🌶️", "unit": "kg"},
        {"name": "Cabai Rawit", "icon": "🔥", "unit": "kg"},
        {"name": "Minyak Goreng", "icon": "🍾", "unit": "kg"},
        {"name": "Gula Pasir", "icon": "🍬", "unit": "kg"},
    ]

    # Jadwal hari kerja 7 hari ke depan (12 s.d. 20 Oktober 2026)
    fc_schedule = [
        ("Senin, 12 Okt 2026", "12/10/2026"),
        ("Selasa, 13 Okt 2026", "13/10/2026"),
        ("Rabu, 14 Okt 2026", "14/10/2026"),
        ("Kamis, 15 Okt 2026", "15/10/2026"),
        ("Jumat, 16 Okt 2026", "16/10/2026"),
        ("Senin, 19 Okt 2026", "19/10/2026"),
        ("Selasa, 20 Okt 2026", "20/10/2026"),
    ]

    for comm_meta in target_commodities:
        cname = comm_meta["name"]
        icon = comm_meta["icon"]
        unit = comm_meta["unit"]

        row = next((r for r in rows if r.get("name") == cname and r.get("level") == 1), None)
        if not row:
            continue

        date_keys = [k for k in row.keys() if '/' in k]
        date_keys.sort(key=lambda d: [int(x) for x in reversed(d.split('/'))])

        prices = []
        dates = []
        for d in date_keys:
            val = row.get(d)
            if val and val != '-':
                prices.append(float(str(val).replace(',', '').strip()))
                dates.append(d)

        n = len(prices)
        last_date = dates[-1]
        last_price = prices[-1]

        # Fit Meta Prophet model dengan 20 changepoints dan multi-musiman
        model = fit_meta_prophet_model(dates, prices, n_changepoints=20)

        forecast_list = []
        if model["is_constant"]:
            for step_idx, (day_str, d_code) in enumerate(fc_schedule):
                forecast_list.append({
                    "step": step_idx + 1,
                    "hari": day_str,
                    "tanggal": d_code,
                    "harga_proyeksi": round(last_price),
                    "batas_bawah_95": round(last_price),
                    "batas_atas_95": round(last_price),
                    "selisih_rp": 0.0,
                    "persen_perubahan": 0.0,
                    "arah": "stabil"
                })
        else:
            beta = model["beta"]
            cp_t = model["cp_t"]
            last_resid = model["last_resid"]
            dt_step = model["dt_step"]
            sigma = model["sigma"]

            for step_idx, (day_str, d_code) in enumerate(fc_schedule):
                h = step_idx + 1
                t_fut = 1.0 + h * dt_step
                dt_fut = datetime.datetime.strptime(d_code, '%d/%m/%Y')
                doy_fut = dt_fut.timetuple().tm_yday
                dom_fut = dt_fut.day
                dow_fut = dt_fut.weekday()
                
                row_x = [1.0, t_fut]
                for cp in cp_t:
                    row_x.append(max(0.0, t_fut - cp))
                for order in range(1, 6):
                    arg = 2.0 * math.pi * order * doy_fut / 365.25
                    row_x.append(math.cos(arg))
                    row_x.append(math.sin(arg))
                for order in range(1, 3):
                    arg = 2.0 * math.pi * order * dom_fut / 30.5
                    row_x.append(math.cos(arg))
                    row_x.append(math.sin(arg))
                for order in range(1, 3):
                    arg = 2.0 * math.pi * order * dow_fut / 7.0
                    row_x.append(math.cos(arg))
                    row_x.append(math.sin(arg))
                
                raw_pred = sum(row_x[j] * beta[j] for j in range(len(beta)))
                # Peluruhan residu halus untuk kontinuitas sambungan proyeksi dari observasi terakhir
                smooth_pred = raw_pred + last_resid * (0.65 ** h)
                pred_p = round(smooth_pred)

                # Pelebaran interval ketidakpastian seiring bertambahnya horizon proyeksi
                se_h = sigma * math.sqrt(1.0 + 0.12 * h)
                ci_l = round(max(0.0, smooth_pred - 1.96 * se_h))
                ci_u = round(smooth_pred + 1.96 * se_h)

                diff_last = pred_p - last_price
                pct_last = (diff_last / last_price) * 100.0 if last_price else 0.0
                arah = "naik" if diff_last > 15 else ("turun" if diff_last < -15 else "stabil")

                forecast_list.append({
                    "step": h,
                    "hari": day_str,
                    "tanggal": d_code,
                    "harga_proyeksi": pred_p,
                    "batas_bawah_95": ci_l,
                    "batas_atas_95": ci_u,
                    "selisih_rp": diff_last,
                    "persen_perubahan": round(pct_last, 2),
                    "arah": arah
                })

        acc = round(100.0 - model["mape"], 2)
        results[cname] = {
            "komoditas": cname,
            "icon": icon,
            "satuan": unit,
            "model_tipe": "Machine Learning",
            "model_name": "Meta Prophet",
            "model_arima": "Meta Prophet (GAM)",
            "jumlah_observasi": n,
            "tanggal_terakhir": last_date,
            "harga_terakhir": last_price,
            "mape": model["mape"],
            "rmse": model["rmse"],
            "akurasi": acc,
            "komponen": {
                "tren": f"Piecewise Linear ({model['changepoints_count']} Changepoints)",
                "musiman": "Multi-Musiman (Tahunan N=5, Bulanan N=2, Mingguan N=2)",
                "regularisasi": "Ridge L2 Prior (alpha=0.6)"
            },
            "proyeksi_7_hari": forecast_list,
            "deret_historis_30_hari": [{"tanggal": dt, "harga": pr} for dt, pr in zip(dates[-30:], prices[-30:])]
        }
        print(f"[OK] {icon} {cname:15} -> Meta Prophet GAM [Akurasi: {acc:.2f}%, MAPE: {model['mape']:.2f}%, RMSE: Rp {model['rmse']:.1f}, Obs: {n}]")

    with open(OUTPUT_PROPHET_PATH, "w", encoding="utf-8") as f:
        json.dump(results, f, indent=2, ensure_ascii=False)

    print(f"\n[SELESAI] Hasil pemodelan Meta Prophet tersimpan di: {OUTPUT_PROPHET_PATH}")
    return True

if __name__ == "__main__":
    run_prophet_forecasting()
