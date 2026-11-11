#!/usr/bin/env python3
"""
Simulasi & Validasi Out-of-Sample (Backtesting):
Pelatihan Model ARIMA & Meta Prophet Menggunakan Data Historis 2024–2025 (522 Hari Kerja)
Untuk Memproyeksikan 7 Hari Kerja Pertama Tahun 2026 (02/01/2026 s.d. 12/01/2026)
dan Membandingkannya Secara Presisi dengan Realisasi Angka Riil Tahun 2026.
"""

import os
import sys
import json
import math
import datetime

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DATA_DIR = os.path.join(BASE_DIR, "data")
DAILY_DATA_PATH = os.path.join(DATA_DIR, "bi_daily_2024_2026.json")
OUTPUT_BACKTEST_PATH = os.path.join(DATA_DIR, "backtest_2024_2025_to_2026.json")

def solve_ols(X, y):
    n, k = len(X), len(X[0])
    XtX = [[sum(X[r][i] * X[r][j] for r in range(n)) for j in range(k)] for i in range(k)]
    for i in range(k):
        XtX[i][i] += 1e-5
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

def is_stationary(phi):
    if len(phi) == 0: return True
    if len(phi) == 1: return abs(phi[0]) < 0.98
    if len(phi) == 2: return (phi[0] + phi[1] < 0.98) and (phi[1] - phi[0] < 0.98) and (abs(phi[1]) < 0.98)
    return False

def is_invertible(theta):
    if len(theta) == 0: return True
    if len(theta) == 1: return abs(theta[0]) < 0.98
    if len(theta) == 2: return (theta[0] + theta[1] < 0.98) and (theta[1] - theta[0] < 0.98) and (abs(theta[1]) < 0.98)
    return False

def fit_arima(y, p, d, q):
    w = [y[i] - y[i-1] for i in range(1, len(y))]
    N = len(w)
    var_w = sum((x - sum(w)/N)**2 for x in w) / N
    if var_w < 1e-8:
        return {'order': (0, d, 0), 'phi': [], 'theta': [], 'sigma2': 0.0, 'aic': 0.0, 'bic': 0.0, 'fitted': [y[0]] + [y[i-1] for i in range(1, len(y))], 'w': w, 'resids': [0.0]*N}
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
        return {'order': (p, d, q), 'aic': float('inf'), 'bic': float('inf')}
    fitted_w = [0.0] * N
    resids = [0.0] * N
    for t in range(N):
        pred = sum(phi[i] * w[t - 1 - i] for i in range(min(p, t))) + sum(theta[j] * resids[t - 1 - j] for j in range(min(q, t)))
        fitted_w[t] = pred
        resids[t] = w[t] - pred
        if abs(resids[t]) > 1e8: return {'order': (p, d, q), 'aic': float('inf'), 'bic': float('inf')}
    sigma2 = sum(r**2 for r in resids[start_t:]) / (N - start_t)
    if sigma2 <= 0: sigma2 = 1e-6
    k_params = p + q + 1
    llf = -0.5 * (N - start_t) * (math.log(2 * math.pi * sigma2) + 1.0)
    aic = 2 * k_params - 2 * llf
    bic = k_params * math.log(N - start_t) - 2 * llf
    fitted_y = [y[0]]
    for t in range(N): fitted_y.append(y[t] + fitted_w[t])
    return {'order': (p, d, q), 'phi': phi, 'theta': theta, 'sigma2': sigma2, 'aic': aic, 'bic': bic, 'fitted': fitted_y, 'w': w, 'resids': resids}

def forecast_arima_7(y, model):
    p, d, q = model['order']
    phi, theta, sigma2, w, resids = model['phi'], model['theta'], model['sigma2'], model['w'], model['resids']
    N = len(w)
    psi = [1.0]
    for k in range(1, 10):
        val = sum(phi[i - 1] * psi[k - i] for i in range(1, p + 1) if k - i >= 0)
        if k <= q: val += theta[k - 1]
        psi.append(val)
    Psi_cum = []
    run_tot = 0.0
    for v in psi:
        run_tot += v
        Psi_cum.append(run_tot)
    future_w, fc_y, ci_low, ci_up = [], [], [], []
    curr_y = y[-1]
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
        fc_y.append(curr_y)
        se_h = math.sqrt(sigma2 * sum(Psi_cum[k]**2 for k in range(h)))
        ci_low.append(curr_y - 1.96 * se_h)
        ci_up.append(curr_y + 1.96 * se_h)
    return fc_y, ci_low, ci_up

def fit_meta_prophet(dates, prices, n_changepoints=15):
    N = len(prices)
    t = [i / (N - 1) for i in range(N)]
    dts = [datetime.datetime.strptime(d, '%d/%m/%Y') for d in dates]
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
    beta = solve_ols(X, prices)
    fitted = [sum(X[i][j] * beta[j] for j in range(len(beta))) for i in range(N)]
    resids = [prices[i] - fitted[i] for i in range(N)]
    sigma = math.sqrt(sum(r**2 for r in resids) / max(1, N - len(beta)))
    return {'beta': beta, 'cp_t': cp_t, 'resids': resids, 'sigma': sigma, 'dt_step': 1.0 / (N - 1)}

def forecast_prophet_7(fc_dates, model):
    beta, cp_t, resids, sigma, dt_step = model['beta'], model['cp_t'], model['resids'], model['sigma'], model['dt_step']
    last_resid = resids[-1]
    fc_y, ci_low, ci_up = [], [], []
    for h, d_str in enumerate(fc_dates, 1):
        t_fut = 1.0 + h * dt_step
        dt_fut = datetime.datetime.strptime(d_str, '%d/%m/%Y')
        doy = dt_fut.timetuple().tm_yday
        dom = dt_fut.day
        dow = dt_fut.weekday()
        row = [1.0, t_fut]
        for cp in cp_t: row.append(max(0.0, t_fut - cp))
        for order in range(1, 6):
            arg = 2.0 * math.pi * order * doy / 365.25
            row.append(math.cos(arg)); row.append(math.sin(arg))
        for order in range(1, 3):
            arg = 2.0 * math.pi * order * dom / 30.5
            row.append(math.cos(arg)); row.append(math.sin(arg))
        for order in range(1, 3):
            arg = 2.0 * math.pi * order * dow / 7.0
            row.append(math.cos(arg)); row.append(math.sin(arg))
        raw_pred = sum(row[j] * beta[j] for j in range(len(beta)))
        smooth_pred = raw_pred + last_resid * (0.65 ** h)
        se_h = sigma * math.sqrt(1.0 + 0.12 * h)
        fc_y.append(round(smooth_pred))
        ci_low.append(round(max(0.0, smooth_pred - 1.96 * se_h)))
        ci_up.append(round(smooth_pred + 1.96 * se_h))
    return fc_y, ci_low, ci_up

def run_backtest():
    with open(DAILY_DATA_PATH, "r", encoding="utf-8") as f:
        daily_json = json.load(f)
    
    r0 = daily_json['data'][0]
    all_dates = [k for k in r0.keys() if '/' in k]
    all_dates.sort(key=lambda x: [int(v) for v in reversed(x.split('/'))])

    train_dates = [k for k in all_dates if '/2024' in k or '/2025' in k]
    test_dates = [k for k in all_dates if '/2026' in k and k != '01/01/2026'][:7]

    day_names = ["Jumat", "Senin", "Selasa", "Rabu", "Kamis", "Jumat", "Senin"]

    candidate_orders = [
        (0, 1, 0), (1, 1, 0), (0, 1, 1), (1, 1, 1),
        (2, 1, 0), (0, 1, 2), (2, 1, 1), (1, 1, 2), (2, 1, 2)
    ]

    commodities = [
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

    results = {}

    print("=" * 85)
    print("HASIL SIMULASI PROYEKSI OUT-OF-SAMPLE (PELATIHAN 2024–2025 -> PROYEKSI 7 HARI 2026)")
    print("=" * 85)

    for comm in commodities:
        cname = comm["name"]
        icon = comm["icon"]
        unit = comm["unit"]

        row = next(r for r in daily_json['data'] if r['name'] == cname and r.get('level') == 1)
        y_train = [float(str(row[k]).replace(',', '')) for k in train_dates]
        y_test_real = [float(str(row[k]).replace(',', '')) for k in test_dates]

        # ARIMA
        best_arima = None
        for p, d_ord, q in candidate_orders:
            res = fit_arima(y_train, p, d_ord, q)
            if best_arima is None or res['aic'] < best_arima['aic']:
                best_arima = res
        fc_arima, ci_l_ar, ci_u_ar = forecast_arima_7(y_train, best_arima)

        # Meta Prophet
        model_p = fit_meta_prophet(train_dates, y_train, n_changepoints=15)
        fc_prophet, ci_l_pr, ci_u_pr = forecast_prophet_7(test_dates, model_p)

        mape_ar = sum(abs(fc_arima[i] - y_test_real[i]) / y_test_real[i] for i in range(7)) / 7 * 100
        mape_pr = sum(abs(fc_prophet[i] - y_test_real[i]) / y_test_real[i] for i in range(7)) / 7 * 100

        details = []
        for i in range(7):
            dt = test_dates[i]
            d_name = day_names[i]
            real_val = y_test_real[i]
            pred_ar = round(fc_arima[i])
            pred_pr = round(fc_prophet[i])
            diff_ar = pred_ar - real_val
            diff_pr = pred_pr - real_val
            pct_ar = round((diff_ar / real_val) * 100, 2)
            pct_pr = round((diff_pr / real_val) * 100, 2)

            details.append({
                "step": i + 1,
                "hari": d_name,
                "tanggal": dt,
                "harga_realtime_2026": real_val,
                "proyeksi_arima": pred_ar,
                "selisih_arima": diff_ar,
                "deviasi_arima_pct": pct_ar,
                "proyeksi_prophet": pred_pr,
                "selisih_prophet": diff_pr,
                "deviasi_prophet_pct": pct_pr
            })

        results[cname] = {
            "komoditas": cname,
            "icon": icon,
            "satuan": unit,
            "ordo_arima": best_arima['order'],
            "harga_terakhir_2025": y_train[-1],
            "mape_arima_test": round(mape_ar, 2),
            "akurasi_arima_test": round(100.0 - mape_ar, 2),
            "mape_prophet_test": round(mape_pr, 2),
            "akurasi_prophet_test": round(100.0 - mape_pr, 2),
            "rincian_7_hari": details
        }

        print(f"{icon} {cname:15} | ARIMA{str(best_arima['order']):8} (Akurasi: {100-mape_ar:6.2f}%) | Prophet (Akurasi: {100-mape_pr:6.2f}%)")

    with open(OUTPUT_BACKTEST_PATH, "w", encoding="utf-8") as f:
        json.dump(results, f, indent=2, ensure_ascii=False)

    print(f"\n[SUKSES] Seluruh kalkulasi proyeksi 7 hari awal 2026 tersimpan di: {OUTPUT_BACKTEST_PATH}")
    return results

if __name__ == "__main__":
    run_backtest()
