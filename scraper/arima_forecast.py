#!/usr/bin/env python3
"""
Modul Pemodelan Deret Waktu ARIMA (Autoregressive Integrated Moving Average)
EWS Inflasi Pangan Sulawesi Tenggara
Memproyeksikan harga 10 kelompok komoditas pangan strategis 7 hari kerja ke depan.
Dilatih pada data historis harian BI PIHPS dari 2024 hingga 2026 (~724 observasi).
"""

import sys
import os
import json
import math
import warnings
warnings.filterwarnings('ignore')

# Tambahkan user site-packages jika tersedia
sys.path.append(os.path.expanduser('~/Library/Python/3.9/lib/python/site-packages'))

import urllib.request
from datetime import datetime, timedelta

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DATA_DIR = os.path.join(BASE_DIR, "data")
DAILY_CACHE_PATH = os.path.join(DATA_DIR, "bi_daily_2024_2026.json")
OUTPUT_FORECAST_PATH = os.path.join(DATA_DIR, "arima_forecast_all_commodities.json")
OUTPUT_LEGACY_PATH = os.path.join(DATA_DIR, "arima_forecast_beras_ayam.json")

def load_or_fetch_daily_data():
    if os.path.exists(DAILY_CACHE_PATH):
        try:
            with open(DAILY_CACHE_PATH, "r", encoding="utf-8") as f:
                data = json.load(f)
            if data and data.get("data"):
                return data
        except Exception:
            pass

    # Ambil dari API BI jika cache belum tersedia
    url = 'https://www.bi.go.id/hargapangan/WebSite/TabelHarga/GetGridDataDaerah?price_type_id=1&comcat_id=&province_id=27&regency_id=&market_id=&tipe_laporan=1&start_date=2026-07-01&end_date=2026-10-09'
    headers = {'User-Agent': 'Mozilla/5.0'}
    try:
        req = urllib.request.Request(url, headers=headers)
        with urllib.request.urlopen(req, timeout=20) as resp:
            data = json.loads(resp.read().decode())
        with open(DAILY_CACHE_PATH, "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False)
        return data
    except Exception as e:
        print(f"[ARIMA] Warning: gagal mengambil data harian dari API: {e}")
        return None

def solve_ols(X, y):
    """Menyelesaikan persamaan normal (X^T X) beta = X^T y dengan eliminasi Gauss-Jordan dan regularisasi ridge numerik."""
    n = len(X)
    k = len(X[0])
    XtX = [[sum(X[r][i] * X[r][j] for r in range(n)) for j in range(k)] for i in range(k)]
    for i in range(k):
        XtX[i][i] += 1e-5  # Ridge untuk stabilitas numerik pada deret panjang
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
    """Memeriksa kondisi stasioneritas polinomial AR(p)."""
    if len(phi) == 0:
        return True
    if len(phi) == 1:
        return abs(phi[0]) < 0.98
    if len(phi) == 2:
        return (phi[0] + phi[1] < 0.98) and (phi[1] - phi[0] < 0.98) and (abs(phi[1]) < 0.98)
    return False

def is_invertible(theta):
    """Memeriksa kondisi invertibilitas polinomial MA(q)."""
    if len(theta) == 0:
        return True
    if len(theta) == 1:
        return abs(theta[0]) < 0.98
    if len(theta) == 2:
        return (theta[0] + theta[1] < 0.98) and (theta[1] - theta[0] < 0.98) and (abs(theta[1]) < 0.98)
    return False

def fit_arima_engine(y, p, d, q):
    """Estimasi ARIMA(p, d, q) berbasis algoritma dua tahap Hannan-Rissanen (Box-Jenkins)."""
    w = [y[i] - y[i-1] for i in range(1, len(y))]
    N = len(w)
    var_w = sum((x - sum(w)/N)**2 for x in w) / N
    if var_w < 1e-8:
        # Deret konstan (variansi nol)
        return {
            'order': (0, d, 0),
            'phi': [],
            'theta': [],
            'sigma2': 0.0,
            'aic': 0.0,
            'bic': 0.0,
            'fitted': [y[0]] + [y[i-1] for i in range(1, len(y))],
            'w': w,
            'resids': [0.0] * N
        }
    m = max(p + q + 2, 4)
    X_ar = []
    y_ar = []
    for t in range(m, N):
        X_ar.append([w[t - i] for i in range(1, m + 1)])
        y_ar.append(w[t])
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
        if not row:
            row = [1.0]
        X.append(row)
        y_reg.append(w[t])
    beta = solve_ols(X, y_reg)
    phi = beta[:p]
    theta = beta[p:p+q]

    # Validasi stasioneritas dan invertibilitas
    if not is_stationary(phi) or not is_invertible(theta):
        return {'order': (p, d, q), 'aic': float('inf'), 'bic': float('inf')}

    fitted_w = [0.0] * N
    resids = [0.0] * N
    for t in range(N):
        pred = sum(phi[i] * w[t - 1 - i] for i in range(min(p, t))) + \
               sum(theta[j] * resids[t - 1 - j] for j in range(min(q, t)))
        fitted_w[t] = pred
        resids[t] = w[t] - pred
        if abs(resids[t]) > 1e8:  # Deteksi divergensi numerik
            return {'order': (p, d, q), 'aic': float('inf'), 'bic': float('inf')}

    sigma2 = sum(r**2 for r in resids[start_t:]) / (N - start_t)
    if sigma2 <= 0:
        sigma2 = 1e-6
    k_params = p + q + 1
    llf = -0.5 * (N - start_t) * (math.log(2 * math.pi * sigma2) + 1.0)
    aic = 2 * k_params - 2 * llf
    bic = k_params * math.log(N - start_t) - 2 * llf
    fitted_y = [y[0]]
    for t in range(N):
        fitted_y.append(y[t] + fitted_w[t])
    return {
        'order': (p, d, q),
        'phi': phi,
        'theta': theta,
        'sigma2': sigma2,
        'aic': aic,
        'bic': bic,
        'fitted': fitted_y,
        'w': w,
        'resids': resids
    }

def forecast_7_steps(y, model):
    """Menghitung proyeksi 7 hari ke depan beserta interval kepercayaan 95% (Fan Chart CI)."""
    p, d, q = model['order']
    phi = model['phi']
    theta = model['theta']
    sigma2 = model['sigma2']
    w = model['w']
    resids = model['resids']
    N = len(w)
    last_y = y[-1]
    
    # Menghitung bobot psi (impulse response function) untuk variansi terintegrasi
    psi = [1.0]
    for k in range(1, 10):
        val = 0.0
        for i in range(1, p + 1):
            if k - i >= 0:
                val += phi[i - 1] * psi[k - i]
        if k <= q:
            val += theta[k - 1]
        psi.append(val)
        
    Psi_cum = []
    running = 0.0
    for val in psi:
        running += val
        Psi_cum.append(running)
        
    future_w = []
    fc_y = []
    ci_low = []
    ci_up = []
    curr_y = last_y
    
    for h in range(1, 8):
        pred_w = 0.0
        for i in range(1, p + 1):
            lag = h - i
            if lag > 0:
                val = future_w[lag - 1]
            else:
                idx = N - 1 + lag
                val = w[idx] if 0 <= idx < N else 0.0
            pred_w += phi[i - 1] * val
        for j in range(1, q + 1):
            lag = h - j
            if lag <= 0:
                idx = N - 1 + lag
                val = resids[idx] if 0 <= idx < N else 0.0
                pred_w += theta[j - 1] * val
        future_w.append(pred_w)
        curr_y += pred_w
        fc_y.append(curr_y)
        
        var_h = sigma2 * sum(Psi_cum[k]**2 for k in range(h))
        se_h = math.sqrt(var_h)
        ci_low.append(curr_y - 1.96 * se_h)
        ci_up.append(curr_y + 1.96 * se_h)
        
    return fc_y, ci_low, ci_up

def run_arima_forecasting():
    print("=" * 80)
    print("PEMODELAN ARIMA: PROYEKSI HARGA 10 KOMODITAS PANGAN 7 HARI KE DEPAN (2024-2026)")
    print("=" * 80)

    raw_data = load_or_fetch_daily_data()
    if not raw_data or not raw_data.get("data"):
        print("[ARIMA] Data harian tidak tersedia, membatalkan kalkulasi.")
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

    candidate_orders = [
        (0, 1, 0), (1, 1, 0), (0, 1, 1), (1, 1, 1),
        (2, 1, 0), (0, 1, 2), (2, 1, 1), (1, 1, 2), (2, 1, 2)
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

        best_fit = None
        for p, d, q in candidate_orders:
            res = fit_arima_engine(prices, p, d, q)
            if best_fit is None or res['aic'] < best_fit['aic']:
                best_fit = res

        fc_y, ci_low, ci_up = forecast_7_steps(prices, best_fit)

        # In-sample metrics
        mape = sum(abs(prices[i] - best_fit['fitted'][i]) / prices[i] for i in range(1, len(prices))) / (len(prices) - 1) * 100
        rmse = math.sqrt(sum((prices[i] - best_fit['fitted'][i])**2 for i in range(1, len(prices))) / (len(prices) - 1))

        forecast_list = []
        for step in range(7):
            day_str, d_code = fc_schedule[step]
            pred_p = round(fc_y[step])
            ci_l = round(ci_low[step])
            ci_u = round(ci_up[step])
            diff_last = pred_p - last_price
            pct_last = (diff_last / last_price) * 100 if last_price else 0.0
            arah = "naik" if diff_last > 10 else ("turun" if diff_last < -10 else "stabil")
            forecast_list.append({
                "step": step + 1,
                "hari": day_str,
                "tanggal": d_code,
                "harga_proyeksi": pred_p,
                "batas_bawah_95": ci_l,
                "batas_atas_95": ci_u,
                "selisih_rp": diff_last,
                "persen_perubahan": round(pct_last, 2),
                "arah": arah
            })

        p, d, q = best_fit['order']
        param_dict = {}
        for i, coef in enumerate(best_fit['phi']):
            param_dict[f'ar.L{i+1}'] = {'coef': round(coef, 4)}
        for j, coef in enumerate(best_fit['theta']):
            param_dict[f'ma.L{j+1}'] = {'coef': round(coef, 4)}
        param_dict['sigma2'] = {'coef': round(best_fit['sigma2'], 4)}

        results[cname] = {
            "komoditas": cname,
            "icon": icon,
            "satuan": unit,
            "jumlah_observasi": n,
            "tanggal_terakhir": last_date,
            "harga_terakhir": last_price,
            "model_arima": f"ARIMA({p}, {d}, {q})",
            "ordo": {"p": p, "d": d, "q": q},
            "aic": round(best_fit['aic'], 2),
            "bic": round(best_fit['bic'], 2),
            "rmse": round(rmse, 2),
            "mape": round(mape, 2),
            "parameter_koefisien": param_dict,
            "proyeksi_7_hari": forecast_list,
            "deret_historis_30_hari": [{"tanggal": dt, "harga": pr} for dt, pr in zip(dates[-30:], prices[-30:])]
        }
        print(f"[OK] {icon} {cname:15} -> ARIMA({p},{d},{q}) [Akurasi: {(100-mape):.2f}%, MAPE: {mape:.2f}%, RMSE: Rp {rmse:.1f}, Obs: {n}]")

    # Simpan ke kedua lokasi berkas JSON
    with open(OUTPUT_FORECAST_PATH, "w", encoding="utf-8") as f:
        json.dump(results, f, indent=2, ensure_ascii=False)
    with open(OUTPUT_LEGACY_PATH, "w", encoding="utf-8") as f:
        json.dump(results, f, indent=2, ensure_ascii=False)

    print(f"\n[SELESAI] Hasil proyeksi 10 komoditas tersimpan di:")
    print(f"  -> {OUTPUT_FORECAST_PATH}")
    print(f"  -> {OUTPUT_LEGACY_PATH}")
    return True

if __name__ == "__main__":
    run_arima_forecasting()
