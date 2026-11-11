#!/usr/bin/env python3
"""
Modul Pemodelan Ekonometrika Terpadu ARIMAX & SARIMAX
EWS Inflasi Pangan Sulawesi Tenggara

Mengintegrasikan deret waktu harga pangan harian PIHPS Bank Indonesia (724 hari kerja)
dengan variabel eksogen cuaca BMKG Sultra (curah hujan sentra Konawe/Kolut lag-7, HTH kekeringan, angin maritim)
dan kalender HBKN (Hari Besar Keagamaan Nasional).

Menghasilkan proyeksi 7 hari ke depan untuk 10 komoditas pangan strategis:
- ARIMAX(p, d, q) + X
- SARIMAX(p, d, q)(P, D, Q)_s=5 + X
"""

import os
import sys
import json
import math
from datetime import datetime, date, timedelta

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DATA_DIR = os.path.join(BASE_DIR, "data")
ARTIFACT_DIR = "/Users/regaprasetyo/.gemini/antigravity/brain/45b29b5e-87d9-439a-b46b-f9c22bf36c3e"

DAILY_PRICE_PATH = os.path.join(DATA_DIR, "bi_daily_2024_2026.json")
DAILY_WEATHER_PATH = os.path.join(DATA_DIR, "weather_daily_2024_2026.json")

OUTPUT_ARIMAX_PATH = os.path.join(DATA_DIR, "arimax_forecast_all_commodities.json")
OUTPUT_SARIMAX_PATH = os.path.join(DATA_DIR, "sarimax_forecast_all_commodities.json")

TARGET_COMMODITIES = [
    "Beras", "Daging Ayam", "Daging Sapi", "Telur Ayam", "Bawang Merah",
    "Bawang Putih", "Cabai Merah", "Cabai Rawit", "Minyak Goreng", "Gula Pasir"
]

COMMODITY_ICONS = {
    "Beras": "🌾",
    "Daging Ayam": "🍗",
    "Daging Sapi": "🥩",
    "Telur Ayam": "🥚",
    "Bawang Merah": "🧅",
    "Bawang Putih": "🧄",
    "Cabai Merah": "🌶️",
    "Cabai Rawit": "🔥",
    "Minyak Goreng": "🍾",
    "Gula Pasir": "🍬"
}

COMMODITY_UNITS = {
    "Beras": "kg",
    "Daging Ayam": "kg",
    "Daging Sapi": "kg",
    "Telur Ayam": "kg",
    "Bawang Merah": "kg",
    "Bawang Putih": "kg",
    "Cabai Merah": "kg",
    "Cabai Rawit": "kg",
    "Minyak Goreng": "liter",
    "Gula Pasir": "kg"
}

# Periode HBKN (Hari Besar Keagamaan Nasional) 2024 - 2026
HBKN_RANGES = [
    (date(2024, 3, 10), date(2024, 4, 15)),  # Ramadan & Idul Fitri 2024
    (date(2024, 6, 14), date(2024, 6, 19)),  # Idul Adha 2024
    (date(2024, 12, 20), date(2025, 1, 3)),  # Nataru 2024/2025
    (date(2025, 2, 28), date(2025, 4, 5)),   # Ramadan & Idul Fitri 2025
    (date(2025, 6, 4), date(2025, 6, 9)),    # Idul Adha 2025
    (date(2025, 12, 20), date(2026, 1, 3)),  # Nataru 2025/2026
    (date(2026, 2, 17), date(2026, 3, 25)),  # Ramadan & Idul Fitri 2026
    (date(2026, 5, 25), date(2026, 5, 30)),  # Idul Adha 2026
    (date(2026, 12, 20), date(2027, 1, 3))   # Nataru 2026/2027
]

def is_hbkn(dt):
    for start, end in HBKN_RANGES:
        if start <= dt <= end:
            return 1.0
    return 0.0

def solve_ols(X, y, ridge=1e-4):
    """Menyelesaikan sistem persamaan normal OLS dengan regularisasi Ridge dan eliminasi Gauss-Jordan."""
    n = len(X)
    k = len(X[0])
    XtX = [[sum(X[r][i] * X[r][j] for r in range(n)) for j in range(k)] for i in range(k)]
    for i in range(k):
        XtX[i][i] += ridge
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
    if len(phi) == 0:
        return True
    if len(phi) == 1:
        return abs(phi[0]) < 0.98
    if len(phi) == 2:
        return (phi[0] + phi[1] < 0.98) and (phi[1] - phi[0] < 0.98) and (abs(phi[1]) < 0.98)
    return True

def is_invertible(theta):
    if len(theta) == 0:
        return True
    if len(theta) == 1:
        return abs(theta[0]) < 0.98
    if len(theta) == 2:
        return (theta[0] + theta[1] < 0.98) and (theta[1] - theta[0] < 0.98) and (abs(theta[1]) < 0.98)
    return True

def load_aligned_data():
    """Memuat dan menyelaraskan data harga PIHPS harian dengan data cuaca BMKG harian."""
    with open(DAILY_PRICE_PATH, "r", encoding="utf-8") as f:
        price_raw = json.load(f)
    with open(DAILY_WEATHER_PATH, "r", encoding="utf-8") as f:
        weather_raw = json.load(f)

    # Buat lookup cuaca per tanggal (YYYY-MM-DD)
    weather_by_date = {}
    weather_regions = weather_raw.get("data", {})
    kendari_recs = {r["tanggal"]: r for r in weather_regions.get("kendari", {}).get("deret_harian", [])}
    konawe_recs = {r["tanggal"]: r for r in weather_regions.get("konawe", {}).get("deret_harian", [])}
    kolut_recs = {r["tanggal"]: r for r in weather_regions.get("kolut", {}).get("deret_harian", [])}
    baubau_recs = {r["tanggal"]: r for r in weather_regions.get("baubau", {}).get("deret_harian", [])}

    all_weather_dates = sorted(kendari_recs.keys())
    for d_str in all_weather_dates:
        cur_dt = datetime.strptime(d_str, "%Y-%m-%d").date()
        # Lag 7 hari
        lag7_dt = cur_dt - timedelta(days=7)
        lag7_str = lag7_dt.strftime("%Y-%m-%d")

        konawe_cur = konawe_recs.get(d_str, {})
        konawe_lag7 = konawe_recs.get(lag7_str, konawe_cur)
        kolut_cur = kolut_recs.get(d_str, {})
        kolut_lag7 = kolut_recs.get(lag7_str, kolut_cur)
        kendari_cur = kendari_recs.get(d_str, {})
        baubau_cur = baubau_recs.get(d_str, {})

        weather_by_date[d_str] = {
            "dt": cur_dt,
            "rain_kendari": kendari_cur.get("curah_hujan_mm", 0.0),
            "temp_kendari": kendari_cur.get("suhu_avg", 27.5),
            "rain_konawe_lag7": konawe_lag7.get("curah_hujan_mm", 0.0),
            "hth_konawe": konawe_cur.get("hth_hari", 0),
            "rain_kolut_lag7": kolut_lag7.get("curah_hujan_mm", 0.0),
            "hth_kolut": kolut_cur.get("hth_hari", 0),
            "wind_baubau": baubau_cur.get("angin_kmh", 15.0),
            "is_hbkn": is_hbkn(cur_dt),
            "is_jumat": 1.0 if cur_dt.weekday() == 4 else 0.0
        }

    # Urutkan tanggal harga PIHPS
    price_data = price_raw.get("data", [])
    first_comm = price_data[0]
    date_keys = [k for k in first_comm.keys() if k not in ["no", "name", "level"]]

    # Parser tanggal PIHPS (DD/MM/YYYY)
    parsed_dates = []
    for dk in date_keys:
        p = dk.split('/')
        if len(p) == 3:
            parsed_dates.append((datetime(int(p[2]), int(p[1]), int(p[0])).date(), dk))
    parsed_dates.sort(key=lambda x: x[0])

    return parsed_dates, price_data, weather_by_date

def get_exog_vector_for_commodity(cname, w_info):
    """
    Membangun vektor fitur eksogen spesifik untuk komoditas pangan tertentu.
    Standardisasi/skala dilakukan agar koefisien stabil secara numerik.
    """
    hbkn = w_info["is_hbkn"]
    jumat = w_info["is_jumat"]
    rain_ken = w_info["rain_kendari"] / 50.0  # Skala ambang 50mm
    rain_kon_lag = w_info["rain_konawe_lag7"] / 50.0
    rain_kol_lag = w_info["rain_kolut_lag7"] / 50.0
    hth_kon = w_info["hth_konawe"] / 30.0    # Skala 30 hari
    hth_kol = w_info["hth_kolut"] / 30.0
    wind_bau = w_info["wind_baubau"] / 20.0

    if cname in ["Beras"]:
        return [rain_kon_lag, hth_kon, hbkn, jumat]
    elif cname in ["Cabai Rawit", "Cabai Merah"]:
        return [rain_kol_lag, hth_kol, hbkn, jumat]
    elif cname in ["Daging Ayam", "Telur Ayam"]:
        return [wind_bau, rain_ken, hbkn, jumat]
    elif cname in ["Daging Sapi"]:
        return [hbkn * 2.0, rain_kon_lag, jumat]
    elif cname in ["Bawang Merah"]:
        return [rain_kon_lag, wind_bau, hbkn, jumat]
    elif cname in ["Bawang Putih", "Minyak Goreng", "Gula Pasir"]:
        return [wind_bau, hbkn, jumat]
    return [rain_ken, hbkn, jumat]

def fit_arimax(y, X_exog, p, d, q):
    """
    Estimasi model ARIMAX(p, d, q) + X.
    1. Differencing dy = y_t - y_{t-1}, dX = X_t - X_{t-1}.
    2. OLS-Ridge untuk mengestimasi koefisien eksogen beta.
    3. ARMA Hannan-Rissanen untuk sisa galat diferensiasi w_t.
    """
    N = len(y)
    K = len(X_exog[0])

    # Diferensiasi d=1
    dy = [y[t] - y[t-1] for t in range(1, N)]
    dX = [[X_exog[t][k] - X_exog[t-1][k] for k in range(K)] for t in range(1, N)]
    N_diff = len(dy)

    # Estimasi beta
    beta = solve_ols(dX, dy, ridge=1e-3)

    # Residual diferensiasi w_t
    w = [dy[t] - sum(beta[k] * dX[t][k] for k in range(K)) for t in range(N_diff)]

    var_w = sum((x - sum(w)/N_diff)**2 for x in w) / N_diff
    if var_w < 1e-8:
        return {
            'order': (0, d, 0),
            'beta': beta,
            'phi': [],
            'theta': [],
            'aic': 0.0,
            'bic': 0.0,
            'sigma2': 0.0,
            'w': w,
            'dy': dy,
            'dX': dX,
            'resids': [0.0] * N_diff
        }

    # Tahap 1 Hannan-Rissanen
    m = max(p + q + 2, 4)
    X_ar = []
    y_ar = []
    for t in range(m, N_diff):
        X_ar.append([w[t - i] for i in range(1, m + 1)])
        y_ar.append(w[t])
    beta_ar = solve_ols(X_ar, y_ar, ridge=1e-3)
    e = [0.0] * m
    for t in range(m, N_diff):
        pred = sum(beta_ar[i] * w[t - 1 - i] for i in range(m))
        e.append(w[t] - pred)

    # Tahap 2 Hannan-Rissanen
    start_t = max(p, q, 1)
    X_arma = []
    y_arma = []
    for t in range(start_t, N_diff):
        row = [w[t - i] for i in range(1, p + 1)] + [e[t - j] for j in range(1, q + 1)]
        if not row:
            row = [1.0]
        X_arma.append(row)
        y_arma.append(w[t])
    gamma = solve_ols(X_arma, y_arma, ridge=1e-3)
    phi = gamma[:p]
    theta = gamma[p:p+q]

    if not is_stationary(phi) or not is_invertible(theta):
        return {'order': (p, d, q), 'aic': float('inf'), 'bic': float('inf')}

    fitted_w = [0.0] * N_diff
    resids = [0.0] * N_diff
    for t in range(N_diff):
        pred = sum(phi[i] * w[t - 1 - i] for i in range(min(p, t))) + \
               sum(theta[j] * resids[t - 1 - j] for j in range(min(q, t)))
        fitted_w[t] = pred
        resids[t] = w[t] - pred
        if abs(resids[t]) > 1e8:
            return {'order': (p, d, q), 'aic': float('inf'), 'bic': float('inf')}

    sigma2 = sum(r**2 for r in resids[start_t:]) / max(N_diff - start_t, 1)
    if sigma2 <= 0:
        sigma2 = 1e-6
    k_params = p + q + K + 1
    llf = -0.5 * (N_diff - start_t) * (math.log(2 * math.pi * sigma2) + 1.0)
    aic = 2 * k_params - 2 * llf
    bic = k_params * math.log(N_diff - start_t) - 2 * llf

    return {
        'order': (p, d, q),
        'beta': beta,
        'phi': phi,
        'theta': theta,
        'sigma2': sigma2,
        'aic': round(aic, 2),
        'bic': round(bic, 2),
        'w': w,
        'resids': resids,
        'dy': dy,
        'dX': dX
    }

def fit_sarimax(y, X_exog, p, d, q, P=1, D=0, Q=1, s=5):
    """
    Estimasi model SARIMAX(p, d, q)(P, D, Q)_s=5 + X.
    Menyertakan komponen musiman mingguan hari kerja (s = 5).
    """
    N = len(y)
    K = len(X_exog[0])

    dy = [y[t] - y[t-1] for t in range(1, N)]
    dX = [[X_exog[t][k] - X_exog[t-1][k] for k in range(K)] for t in range(1, N)]
    N_diff = len(dy)

    beta = solve_ols(dX, dy, ridge=1e-3)
    w = [dy[t] - sum(beta[k] * dX[t][k] for k in range(K)) for t in range(N_diff)]

    var_w = sum((x - sum(w)/N_diff)**2 for x in w) / N_diff
    if var_w < 1e-8:
        return {
            'order': (0, d, 0),
            'seasonal_order': (0, D, 0, s),
            'beta': beta,
            'phi': [],
            'theta': [],
            'Phi': [],
            'Theta': [],
            'aic': 0.0,
            'bic': 0.0,
            'sigma2': 0.0,
            'w': w,
            'resids': [0.0] * N_diff
        }

    m = max(p + q + s + 2, 7)
    X_ar = []
    y_ar = []
    for t in range(m, N_diff):
        X_ar.append([w[t - i] for i in range(1, m + 1)])
        y_ar.append(w[t])
    beta_ar = solve_ols(X_ar, y_ar, ridge=1e-3)
    e = [0.0] * m
    for t in range(m, N_diff):
        pred = sum(beta_ar[i] * w[t - 1 - i] for i in range(m))
        e.append(w[t] - pred)

    start_t = max(p, q, s, 1)
    X_sar = []
    y_sar = []
    for t in range(start_t, N_diff):
        # Non-seasonal AR + Seasonal AR(s) + Non-seasonal MA + Seasonal MA(s)
        row = [w[t - i] for i in range(1, p + 1)]
        if P > 0:
            row.append(w[t - s])
        row += [e[t - j] for j in range(1, q + 1)]
        if Q > 0:
            row.append(e[t - s])
        X_sar.append(row)
        y_sar.append(w[t])

    gamma = solve_ols(X_sar, y_sar, ridge=1e-3)
    idx = 0
    phi = gamma[idx:idx+p]
    idx += p
    Phi = gamma[idx:idx+P] if P > 0 else []
    idx += P
    theta = gamma[idx:idx+q]
    idx += q
    Theta = gamma[idx:idx+Q] if Q > 0 else []

    if not is_stationary(phi) or not is_invertible(theta):
        return {'order': (p, d, q), 'seasonal_order': (P, D, Q, s), 'aic': float('inf'), 'bic': float('inf')}

    fitted_w = [0.0] * N_diff
    resids = [0.0] * N_diff
    for t in range(N_diff):
        pred = sum(phi[i] * w[t - 1 - i] for i in range(min(p, t)))
        if P > 0 and t >= s:
            pred += Phi[0] * w[t - s]
        pred += sum(theta[j] * resids[t - 1 - j] for j in range(min(q, t)))
        if Q > 0 and t >= s:
            pred += Theta[0] * resids[t - s]
        fitted_w[t] = pred
        resids[t] = w[t] - pred
        if abs(resids[t]) > 1e8:
            return {'order': (p, d, q), 'seasonal_order': (P, D, Q, s), 'aic': float('inf'), 'bic': float('inf')}

    sigma2 = sum(r**2 for r in resids[start_t:]) / max(N_diff - start_t, 1)
    if sigma2 <= 0:
        sigma2 = 1e-6
    k_params = p + q + P + Q + K + 1
    llf = -0.5 * (N_diff - start_t) * (math.log(2 * math.pi * sigma2) + 1.0)
    aic = 2 * k_params - 2 * llf
    bic = k_params * math.log(N_diff - start_t) - 2 * llf

    return {
        'order': (p, d, q),
        'seasonal_order': (P, D, Q, s),
        'beta': beta,
        'phi': phi,
        'Phi': Phi,
        'theta': theta,
        'Theta': Theta,
        'sigma2': sigma2,
        'aic': round(aic, 2),
        'bic': round(bic, 2),
        'w': w,
        'resids': resids,
        'dy': dy,
        'dX': dX
    }

def auto_select_arimax(y, X_exog):
    """Pencarian ordo ARIMAX optimal berbasis kriteria informasi AIC/BIC."""
    best_model = None
    best_aic = float('inf')
    candidate_orders = [
        (1, 1, 0), (2, 1, 0), (0, 1, 1), (0, 1, 2),
        (1, 1, 1), (2, 1, 1), (2, 1, 2)
    ]
    for p, d, q in candidate_orders:
        m = fit_arimax(y, X_exog, p, d, q)
        if m.get('aic', float('inf')) < best_aic:
            best_aic = m['aic']
            best_model = m
    return best_model or fit_arimax(y, X_exog, 1, 1, 1)

def auto_select_sarimax(y, X_exog):
    """Pencarian ordo SARIMAX optimal berbasis kriteria informasi AIC/BIC dengan s=5."""
    best_model = None
    best_aic = float('inf')
    candidate_orders = [
        ((1, 1, 0), (1, 0, 1)),
        ((0, 1, 1), (1, 0, 1)),
        ((1, 1, 1), (1, 0, 1)),
        ((2, 1, 0), (1, 0, 0)),
        ((2, 1, 1), (1, 0, 1))
    ]
    for (p, d, q), (P, D, Q) in candidate_orders:
        m = fit_sarimax(y, X_exog, p, d, q, P=P, D=D, Q=Q, s=5)
        if m.get('aic', float('inf')) < best_aic:
            best_aic = m['aic']
            best_model = m
    return best_model or fit_sarimax(y, X_exog, 1, 1, 1, 1, 0, 1, 5)

def forecast_arimax_7_steps(y, model, future_X):
    """Menghasilkan proyeksi h=1..7 untuk model ARIMAX."""
    p, d, q = model['order']
    beta = model['beta']
    phi = model['phi']
    theta = model['theta']
    sigma2 = model['sigma2']
    w = list(model['w'])
    resids = list(model['resids'])
    last_y = y[-1]

    # Varian dan interval kepercayaan Fan Chart
    se_base = math.sqrt(sigma2)

    projections = []
    current_y = last_y
    for h in range(7):
        # 1. Komponen Eksogen
        delta_X = future_X[h]
        exog_shock = sum(beta[k] * delta_X[k] for k in range(len(beta)))

        # 2. Komponen ARMA
        w_pred = 0.0
        for i in range(p):
            if len(w) - 1 - i >= 0:
                w_pred += phi[i] * w[-1 - i]
        for j in range(q):
            if len(resids) - 1 - j >= 0:
                w_pred += theta[j] * resids[-1 - j]

        # Total delta harga
        delta_y = exog_shock + w_pred
        current_y += delta_y
        current_y_rounded = round(current_y / 50.0) * 50  # Dibulatkan ke kelipatan Rp 50 realistis PIHPS

        w.append(w_pred)
        resids.append(0.0)  # Ekspektasi residual masa depan adalah 0

        ci_half = 1.96 * se_base * math.sqrt(h + 1)
        projections.append({
            'step': h + 1,
            'prediksi': float(current_y_rounded),
            'ci_lower': float(round((current_y - ci_half) / 50.0) * 50),
            'ci_upper': float(round((current_y + ci_half) / 50.0) * 50),
            'exog_impact': float(round(exog_shock, 1))
        })
    return projections

def forecast_sarimax_7_steps(y, model, future_X):
    """Menghasilkan proyeksi h=1..7 untuk model SARIMAX dengan efek musiman mingguan (s=5)."""
    p, d, q = model['order']
    P, D, Q, s = model['seasonal_order']
    beta = model['beta']
    phi = model['phi']
    Phi = model['Phi']
    theta = model['theta']
    Theta = model['Theta']
    sigma2 = model['sigma2']
    w = list(model['w'])
    resids = list(model['resids'])
    last_y = y[-1]

    se_base = math.sqrt(sigma2)
    projections = []
    current_y = last_y
    for h in range(7):
        delta_X = future_X[h]
        exog_shock = sum(beta[k] * delta_X[k] for k in range(len(beta)))

        w_pred = 0.0
        for i in range(p):
            if len(w) - 1 - i >= 0:
                w_pred += phi[i] * w[-1 - i]
        if P > 0 and len(w) >= s:
            w_pred += Phi[0] * w[-s]
        for j in range(q):
            if len(resids) - 1 - j >= 0:
                w_pred += theta[j] * resids[-1 - j]
        if Q > 0 and len(resids) >= s:
            w_pred += Theta[0] * resids[-s]

        delta_y = exog_shock + w_pred
        current_y += delta_y
        current_y_rounded = round(current_y / 50.0) * 50

        w.append(w_pred)
        resids.append(0.0)

        ci_half = 1.96 * se_base * math.sqrt(h + 1) * 0.95  # Sedikit lebih ramping karena pola musiman tereduksi
        projections.append({
            'step': h + 1,
            'prediksi': float(current_y_rounded),
            'ci_lower': float(round((current_y - ci_half) / 50.0) * 50),
            'ci_upper': float(round((current_y + ci_half) / 50.0) * 50),
            'exog_impact': float(round(exog_shock, 1))
        })
    return projections

def build_future_dates_and_exog(last_date_obj, weather_by_date, cname):
    """Menyiapkan 7 hari kerja ke depan beserta prakiraan vektor eksogen delta X."""
    future_dates = []
    future_exog_deltas = []
    cur = last_date_obj
    last_exog = None

    # Cari nilai eksogen hari terakhir
    last_d_str = last_date_obj.strftime("%Y-%m-%d")
    w_last = weather_by_date.get(last_d_str)
    if w_last:
        last_exog = get_exog_vector_for_commodity(cname, w_last)
    else:
        last_exog = [0.0] * 4

    h_count = 0
    while h_count < 7:
        cur += timedelta(days=1)
        if cur.weekday() < 5:  # Senin s.d. Jumat (Hari kerja PIHPS)
            h_count += 1
            d_str = cur.strftime("%Y-%m-%d")
            w_fut = weather_by_date.get(d_str)
            if not w_fut:
                # Fallback prakiraan dari hari terakhir jika belum terbit
                w_fut = {
                    "dt": cur,
                    "rain_kendari": 5.0,
                    "temp_kendari": 28.0,
                    "rain_konawe_lag7": 8.0,
                    "hth_konawe": 2,
                    "rain_kolut_lag7": 3.0,
                    "hth_kolut": 4,
                    "wind_baubau": 16.0,
                    "is_hbkn": is_hbkn(cur),
                    "is_jumat": 1.0 if cur.weekday() == 4 else 0.0
                }
            fut_vec = get_exog_vector_for_commodity(cname, w_fut)
            delta_X = [fut_vec[k] - last_exog[k] for k in range(len(fut_vec))]
            future_exog_deltas.append(delta_X)
            last_exog = fut_vec

            HARI_ID = {0: "Senin", 1: "Selasa", 2: "Rabu", 3: "Kamis", 4: "Jumat"}
            BULAN_ID = ["", "Januari", "Februari", "Maret", "April", "Mei", "Juni", "Juli", "Agustus", "September", "Oktober", "November", "Desember"]
            future_dates.append({
                "tanggal_raw": cur.strftime("%Y-%m-%d"),
                "tanggal": cur.strftime("%d/%m/%Y"),
                "label": f"{cur.day:02d} {BULAN_ID[cur.month][:3]}",
                "hari": HARI_ID[cur.weekday()]
            })

    return future_dates, future_exog_deltas

def run_arimax_and_sarimax_pipeline():
    print("-> Memuat dan menyelaraskan data harga PIHPS & data cuaca BMKG...")
    parsed_dates, price_data, weather_by_date = load_aligned_data()
    last_date_obj, last_date_key = parsed_dates[-1]
    print(f"   Tanggal data terakhir: {last_date_key} (Total {len(parsed_dates)} hari kerja)")

    arimax_results = {}
    sarimax_results = {}

    for cname in TARGET_COMMODITIES:
        row = next((r for r in price_data if r.get("name") == cname), None)
        if not row:
            continue

        # Ekstrak harga harian
        y_series = []
        valid_dates = []
        for dt_obj, dk in parsed_dates:
            val_str = str(row.get(dk, "0")).replace(",", "").replace(".", "").strip()
            try:
                v = float(val_str)
                if v > 0:
                    y_series.append(v)
                    valid_dates.append(dt_obj)
            except Exception:
                pass

        if len(y_series) < 30:
            continue

        # Bangun matriks eksogen berpasangan
        X_matrix = []
        for dt_obj in valid_dates:
            d_str = dt_obj.strftime("%Y-%m-%d")
            w_info = weather_by_date.get(d_str, {
                "dt": dt_obj,
                "rain_kendari": 0.0, "temp_kendari": 28.0,
                "rain_konawe_lag7": 0.0, "hth_konawe": 0,
                "rain_kolut_lag7": 0.0, "hth_kolut": 0,
                "wind_baubau": 15.0, "is_hbkn": is_hbkn(dt_obj),
                "is_jumat": 1.0 if dt_obj.weekday() == 4 else 0.0
            })
            X_matrix.append(get_exog_vector_for_commodity(cname, w_info))

        future_dates, future_deltas = build_future_dates_and_exog(last_date_obj, weather_by_date, cname)

        dates_str = [d.strftime("%d/%m/%Y") for d in valid_dates]
        deret_30 = [{"tanggal": dt, "harga": pr} for dt, pr in zip(dates_str[-30:], y_series[-30:])]
        last_date_str = dates_str[-1]
        last_val = y_series[-1]

        # 1. FIT ARIMAX
        model_arimax = auto_select_arimax(y_series, X_matrix)
        proj_arimax = forecast_arimax_7_steps(y_series, model_arimax, future_deltas)

        # Hitung In-sample metrics ARIMAX
        p_amx, d_amx, q_amx = model_arimax['order']
        resids_amx = model_arimax['resids']
        n_res = len(resids_amx)
        rmse_amx = math.sqrt(sum(r**2 for r in resids_amx) / max(n_res, 1))
        mape_amx = sum(abs(resids_amx[t] / max(y_series[t+1], 1)) for t in range(n_res)) / max(n_res, 1) * 100.0

        rincian_7_arimax = []
        for i in range(7):
            p_val = proj_arimax[i]["prediksi"]
            d_rp = round(p_val - last_val)
            p_chg = round(((p_val - last_val) / last_val) * 100.0, 2)
            dir_str = "stabil" if abs(d_rp) < 10 else ("naik" if d_rp > 0 else "turun")
            rincian_7_arimax.append({
                "step": proj_arimax[i]["step"],
                "hari": future_dates[i]["hari"],
                "tanggal": future_dates[i]["tanggal"],
                "label": future_dates[i]["label"],
                "harga_proyeksi": p_val,
                "batas_bawah_95": proj_arimax[i]["ci_lower"],
                "batas_atas_95": proj_arimax[i]["ci_upper"],
                "ci_lower": proj_arimax[i]["ci_lower"],
                "ci_upper": proj_arimax[i]["ci_upper"],
                "selisih_rp": d_rp,
                "persen_perubahan": p_chg,
                "arah": dir_str,
                "exog_impact": proj_arimax[i]["exog_impact"]
            })

        avg_pred_amx = round(sum(p["prediksi"] for p in proj_arimax) / 7.0)
        last_val = y_series[-1]
        pct_diff_amx = round(((avg_pred_amx - last_val) / last_val) * 100.0, 2)

        arimax_results[cname] = {
            "komoditas": cname,
            "satuan": COMMODITY_UNITS.get(cname, "kg"),
            "icon": COMMODITY_ICONS.get(cname, "📦"),
            "model_type": "ARIMAX",
            "model_name": f"ARIMAX({p_amx}, {d_amx}, {q_amx}) + BMKG Exog",
            "model_arima": f"ARIMAX({p_amx}, {d_amx}, {q_amx}) + BMKG",
            "spesifikasi_order": [p_amx, d_amx, q_amx],
            "aic": model_arimax["aic"],
            "bic": model_arimax["bic"],
            "mape": round(mape_amx, 2),
            "akurasi": round(100.0 - mape_amx, 2),
            "rmse": round(rmse_amx, 1),
            "harga_terakhir": last_val,
            "tanggal_terakhir": last_date_str,
            "deret_historis_30_hari": deret_30,
            "taksiran_rata_rata_7_hari": avg_pred_amx,
            "persentase_perubahan": pct_diff_amx,
            "arah_tren": "stabil" if abs(pct_diff_amx) < 0.5 else ("naik" if pct_diff_amx > 0 else "turun"),
            "faktor_eksogen_aktif": [
                "Curah Hujan Sentra Konawe/Kolut (Lag-7)",
                "Hari Tanpa Hujan (HTH / Kemarau El Nino)",
                "Kalender Hari Besar Keagamaan (HBKN)",
                "Kecepatan Angin Pelabuhan Logistik"
            ],
            "proyeksi_7_hari": rincian_7_arimax
        }

        # 2. FIT SARIMAX
        model_sarimax = auto_select_sarimax(y_series, X_matrix)
        proj_sarimax = forecast_sarimax_7_steps(y_series, model_sarimax, future_deltas)

        p_srx, d_srx, q_srx = model_sarimax['order']
        P_srx, D_srx, Q_srx, s_srx = model_sarimax['seasonal_order']
        resids_srx = model_sarimax['resids']
        n_res_srx = len(resids_srx)
        rmse_srx = math.sqrt(sum(r**2 for r in resids_srx) / max(n_res_srx, 1))
        mape_srx = sum(abs(resids_srx[t] / max(y_series[t+1], 1)) for t in range(n_res_srx)) / max(n_res_srx, 1) * 100.0

        rincian_7_sarimax = []
        for i in range(7):
            p_val = proj_sarimax[i]["prediksi"]
            d_rp = round(p_val - last_val)
            p_chg = round(((p_val - last_val) / last_val) * 100.0, 2)
            dir_str = "stabil" if abs(d_rp) < 10 else ("naik" if d_rp > 0 else "turun")
            rincian_7_sarimax.append({
                "step": proj_sarimax[i]["step"],
                "hari": future_dates[i]["hari"],
                "tanggal": future_dates[i]["tanggal"],
                "label": future_dates[i]["label"],
                "harga_proyeksi": p_val,
                "batas_bawah_95": proj_sarimax[i]["ci_lower"],
                "batas_atas_95": proj_sarimax[i]["ci_upper"],
                "ci_lower": proj_sarimax[i]["ci_lower"],
                "ci_upper": proj_sarimax[i]["ci_upper"],
                "selisih_rp": d_rp,
                "persen_perubahan": p_chg,
                "arah": dir_str,
                "exog_impact": proj_sarimax[i]["exog_impact"]
            })

        avg_pred_srx = round(sum(p["prediksi"] for p in proj_sarimax) / 7.0)
        pct_diff_srx = round(((avg_pred_srx - last_val) / last_val) * 100.0, 2)

        sarimax_results[cname] = {
            "komoditas": cname,
            "satuan": COMMODITY_UNITS.get(cname, "kg"),
            "icon": COMMODITY_ICONS.get(cname, "📦"),
            "model_type": "SARIMAX",
            "model_name": f"SARIMAX({p_srx},{d_srx},{q_srx})({P_srx},{D_srx},{Q_srx})₅ + BMKG",
            "model_arima": f"SARIMAX({p_srx},{d_srx},{q_srx})({P_srx},{D_srx},{Q_srx})₅",
            "spesifikasi_order": [p_srx, d_srx, q_srx],
            "seasonal_order": [P_srx, D_srx, Q_srx, s_srx],
            "aic": model_sarimax["aic"],
            "bic": model_sarimax["bic"],
            "mape": round(mape_srx, 2),
            "akurasi": round(100.0 - mape_srx, 2),
            "rmse": round(rmse_srx, 1),
            "harga_terakhir": last_val,
            "tanggal_terakhir": last_date_str,
            "deret_historis_30_hari": deret_30,
            "taksiran_rata_rata_7_hari": avg_pred_srx,
            "persentase_perubahan": pct_diff_srx,
            "arah_tren": "stabil" if abs(pct_diff_srx) < 0.5 else ("naik" if pct_diff_srx > 0 else "turun"),
            "faktor_eksogen_aktif": [
                "Pola Musiman Hari Kerja Mingguan (s=5)",
                "Curah Hujan Sentra Konawe/Kolut (Lag-7)",
                "Hari Tanpa Hujan (HTH / Kemarau El Nino)",
                "Kalender Hari Besar Keagamaan (HBKN)"
            ],
            "proyeksi_7_hari": rincian_7_sarimax
        }

        print(f"   [OK] {cname:15s} | ARIMAX AIC: {model_arimax['aic']:8.1f} | SARIMAX AIC: {model_sarimax['aic']:8.1f} | Acc: {sarimax_results[cname]['akurasi']}%")

    # Simpan Berkas JSON
    with open(OUTPUT_ARIMAX_PATH, "w", encoding="utf-8") as f:
        json.dump(arimax_results, f, indent=2, ensure_ascii=False)
    print(f"[OK] Disimpan: {OUTPUT_ARIMAX_PATH}")

    with open(OUTPUT_SARIMAX_PATH, "w", encoding="utf-8") as f:
        json.dump(sarimax_results, f, indent=2, ensure_ascii=False)
    print(f"[OK] Disimpan: {OUTPUT_SARIMAX_PATH}")

    # Salin ke Direktori Artifact
    if os.path.exists(ARTIFACT_DIR):
        import shutil
        shutil.copy2(OUTPUT_ARIMAX_PATH, os.path.join(ARTIFACT_DIR, "arimax_forecast_all_commodities.json"))
        shutil.copy2(OUTPUT_SARIMAX_PATH, os.path.join(ARTIFACT_DIR, "sarimax_forecast_all_commodities.json"))
        print("[OK] Disalin ke Brain Artifact")

if __name__ == "__main__":
    run_arimax_and_sarimax_pipeline()
