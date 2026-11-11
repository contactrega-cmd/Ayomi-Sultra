/**
 * Modul JavaScript: Deteksi Lonjakan Harga 17 Kabupaten/Kota Se-Sulawesi Tenggara
 * Metodologi: Multi-Horizon Power Weighted Moving Average (MH-WMA)
 * Parameter Terkunci: alpha = 0,5 (Berimbang) -> MA5 (8,8%) + MA20 (17,6%) + MA60 (30,5%) + MA120 (43,1%)
 * Sumber Data Harian Empiris: PIHPS Bank Indonesia (Kendari & Baubau) & SP2KP Kemendag RI (15 Kabupaten)
 */

let mhwmaChartRegionId = null;
let mhwmaChartCommId = null;
let mhwmaChartRange = "all"; // "all" | "1y" | "6m" | "3m"
let mhwmaSelectorsPopulated = false;

let mhwmaVisiblePtsCache = [];
let mhwmaChartGeomCache = null;

const MHWMA_WEIGHTS = {
  ma5: 0.088,
  ma20: 0.176,
  ma60: 0.305,
  ma120: 0.431
};
const MHWMA_EPS = 1e-6;

const MHWMA_MONTHS_ID = [
  "Januari", "Februari", "Maret", "April", "Mei", "Juni",
  "Juli", "Agustus", "September", "Oktober", "November", "Desember"
];
const MHWMA_MONTHS_SHORT = [
  "Jan", "Feb", "Mar", "Apr", "Mei", "Jun",
  "Jul", "Agu", "Sep", "Okt", "Nov", "Des"
];
const MHWMA_DAYS_ID = [
  "Minggu", "Senin", "Selasa", "Rabu", "Kamis", "Jumat", "Sabtu"
];

function fmtRpId(val) {
  if (val === null || val === undefined || Number.isNaN(val)) return "N/A";
  return "Rp" + Math.round(val).toLocaleString("id-ID");
}

function fmtDiffRpId(val) {
  if (val === null || val === undefined || Number.isNaN(val)) return "-";
  const iv = Math.round(val);
  if (iv === 0) return "Rp0";
  return (iv > 0 ? "+" : "-") + "Rp" + Math.abs(iv).toLocaleString("id-ID");
}

function fmtPctId(val) {
  if (val === null || val === undefined || Number.isNaN(val)) return "N/A";
  const sign = val > 0 ? "+" : "";
  return sign + val.toFixed(1).replace(".", ",") + "%";
}

function parseDateDdMmYyyy(dStr) {
  if (!dStr || typeof dStr !== "string") return null;
  const parts = dStr.split("/");
  if (parts.length !== 3) return null;
  const d = parseInt(parts[0], 10);
  const m = parseInt(parts[1], 10);
  const y = parseInt(parts[2], 10);
  if (!d || !m || !y) return null;
  return new Date(y, m - 1, d);
}

function formatFullDateId(dStr) {
  const dt = parseDateDdMmYyyy(dStr);
  if (!dt) return dStr || "-";
  return `${MHWMA_DAYS_ID[dt.getDay()]}, ${dt.getDate()} ${MHWMA_MONTHS_ID[dt.getMonth()]} ${dt.getFullYear()}`;
}

function formatMonthYearId(dt) {
  if (!dt) return "-";
  return `${MHWMA_MONTHS_ID[dt.getMonth()]} ${dt.getFullYear()}`;
}

/**
 * Mengambil seluruh deret harga harian dan menghitung MA5, MA20, MA60, MA120, serta MH-WMA
 */
function buildMhwmaSeries(regionId, commId) {
  if (typeof ALPS_17_DATA === "undefined" || !ALPS_17_DATA.rows || !ALPS_17_DATA.commodities) {
    return null;
  }
  const row = ALPS_17_DATA.rows.find(r => r.region_id === regionId);
  const comm = ALPS_17_DATA.commodities.find(c => c.id === commId);
  if (!row || !comm) return null;

  const datePriceMap = new Map();

  if (row.source === "PIHPS BI") {
    const cityKey = row.pihps_key || (row.region_id === "baubau" ? "Kota Bau-Bau" : "Kota Kendari");
    if (typeof PIHPS_CITY_LOOKUP !== "undefined" && PIHPS_CITY_LOOKUP) {
      const cObj = PIHPS_CITY_LOOKUP[cityKey] || PIHPS_CITY_LOOKUP[row.region_name];
      const mapObj = cObj ? cObj[comm.name] : null;
      if (mapObj) {
        Object.keys(mapObj).forEach(k => {
          const p = Number(mapObj[k]);
          if (p > 0) datePriceMap.set(k, p);
        });
      }
    }
    if (typeof PIHPS_DATA !== "undefined" && PIHPS_DATA && Array.isArray(PIHPS_DATA.data)) {
      const rec = PIHPS_DATA.data.find(it =>
        it.kategori_id === 1 &&
        it.level === 1 &&
        it.kota === cityKey &&
        it.komoditas === comm.name
      );
      if (rec && rec.harga_harian_terkini) {
        Object.keys(rec.harga_harian_terkini).forEach(k => {
          const rawVal = rec.harga_harian_terkini[k];
          const p = (rawVal && typeof rawVal === "object") ? Number(rawVal.harga_rp) : Number(rawVal);
          if (p > 0) datePriceMap.set(k, p);
        });
      }
    }
  } else {
    if (typeof SP2KP_DAILY_LOOKUP !== "undefined" && SP2KP_DAILY_LOOKUP && SP2KP_DAILY_LOOKUP[row.region_name]) {
      const mapObj = SP2KP_DAILY_LOOKUP[row.region_name][comm.name];
      if (mapObj) {
        Object.keys(mapObj).forEach(k => {
          const p = Number(mapObj[k]);
          if (p > 0) datePriceMap.set(k, p);
        });
      }
    }
  }

  const pts = [];
  datePriceMap.forEach((price, dateStr) => {
    const dt = parseDateDdMmYyyy(dateStr);
    if (dt && price > 0) {
      pts.push({ dateStr, dt, ts: dt.getTime(), actual: price });
    }
  });
  pts.sort((a, b) => a.ts - b.ts);

  const n = pts.length;
  if (n === 0) {
    return { row, comm, pts: [], n: 0 };
  }

  const prefix = new Float64Array(n + 1);
  for (let i = 0; i < n; i++) {
    prefix[i + 1] = prefix[i] + pts[i].actual;
  }

  const calcSma = (idx, w) => (idx >= w - 1 ? (prefix[idx + 1] - prefix[idx + 1 - w]) / w : null);

  for (let i = 0; i < n; i++) {
    const ma5 = calcSma(i, 5);
    const ma20 = calcSma(i, 20);
    const ma60 = calcSma(i, 60);
    const ma120 = calcSma(i, 120);
    let mhWma = null;
    let devRp = null;
    let devPct = null;
    if (ma120 !== null) {
      mhWma = MHWMA_WEIGHTS.ma5 * ma5 +
              MHWMA_WEIGHTS.ma20 * ma20 +
              MHWMA_WEIGHTS.ma60 * ma60 +
              MHWMA_WEIGHTS.ma120 * ma120;
      const rawDiff = pts[i].actual - mhWma;
      if (Math.abs(rawDiff) <= MHWMA_EPS) {
        devRp = 0;
        devPct = 0;
      } else {
        devRp = rawDiff;
        devPct = mhWma > 0 ? (devRp / mhWma) * 100 : 0;
      }
    }
    pts[i].idx = i;
    pts[i].ma5 = ma5;
    pts[i].ma20 = ma20;
    pts[i].ma60 = ma60;
    pts[i].ma120 = ma120;
    pts[i].mhWma = mhWma;
    pts[i].devRp = devRp;
    pts[i].devPct = devPct;
  }

  return { row, comm, pts, n };
}

/**
 * Stub KPI Ringkasan MH-WMA (bagian kartu KPI dihilangkan atas permintaan pengguna)
 */
function renderMhwmaKpiSummaryCards() {}

/**
 * Mengisi Dropdown & Default Pair untuk Grafik MH-WMA
 */
function ensureMhwmaChartSelectors() {
  if (typeof ALPS_17_DATA === "undefined" || !ALPS_17_DATA.rows || !ALPS_17_DATA.commodities) return;
  const selReg = document.getElementById("mhwmaChartRegion");
  const selComm = document.getElementById("mhwmaChartCommodity");
  if (!selReg || !selComm) return;

  if (!mhwmaSelectorsPopulated) {
    const regRows = ALPS_17_DATA.rows.filter(r => r.region_id !== "sultra");
    selReg.innerHTML = regRows.map(r => `<option value="${r.region_id}">${r.region_name}</option>`).join("");
    selComm.innerHTML = ALPS_17_DATA.commodities.map(c => `<option value="${c.id}">${c.name}</option>`).join("");
    mhwmaSelectorsPopulated = true;

    if (!mhwmaChartRegionId) {
      mhwmaChartRegionId = regRows.some(r => r.region_id === "kendari")
        ? "kendari"
        : (regRows[0] ? regRows[0].region_id : "kendari");
    }
    if (!mhwmaChartCommId) {
      mhwmaChartCommId = ALPS_17_DATA.commodities.some(c => c.id === "beras")
        ? "beras"
        : (ALPS_17_DATA.commodities[0] ? ALPS_17_DATA.commodities[0].id : "beras");
    }
  }

  if (mhwmaChartRegionId) selReg.value = mhwmaChartRegionId;
  if (mhwmaChartCommId) selComm.value = mhwmaChartCommId;
}

function onMhwmaChartSelectorChange() {
  const selReg = document.getElementById("mhwmaChartRegion");
  const selComm = document.getElementById("mhwmaChartCommodity");
  if (selReg) mhwmaChartRegionId = selReg.value;
  if (selComm) mhwmaChartCommId = selComm.value;
  renderMhwmaChartModule();
}

function setMhwmaChartRange(rangeKey) {
  mhwmaChartRange = rangeKey || "all";
  document.querySelectorAll(".mhwma-range-btn").forEach(btn => {
    const isAct = btn.getAttribute("data-mhwma-range") === mhwmaChartRange;
    btn.className = isAct
      ? "mhwma-range-btn h-full rounded-lg text-xs font-extrabold transition cursor-pointer bg-white text-blue-700 shadow-2xs"
      : "mhwma-range-btn h-full rounded-lg text-xs font-bold transition cursor-pointer text-slate-600 hover:text-slate-900";
  });
  renderMhwmaChartModule();
}

function focusMhwmaPair(regionId, commId, scrollToChart) {
  mhwmaChartRegionId = regionId;
  mhwmaChartCommId = commId;
  const selReg = document.getElementById("mhwmaChartRegion");
  const selComm = document.getElementById("mhwmaChartCommodity");
  if (selReg) selReg.value = regionId;
  if (selComm) selComm.value = commId;
  renderMhwmaChartModule();
  if (scrollToChart) {
    const card = document.getElementById("mhwmaChartSectionCard");
    if (card) card.scrollIntoView({ behavior: "smooth", block: "start" });
  }
}

// Stub kompatibilitas mundur: strip top deviasi positif telah dihilangkan dari UI Tab 4
function renderMhwmaTopSpikesStrip() {}

/**
 * Menghitung interval grid sumbu-Y yang rapi
 */
function pickNiceStep(rawStep) {
  const candidates = [250, 500, 1000, 2000, 2500, 5000, 10000, 15000, 20000, 25000, 50000];
  for (let i = 0; i < candidates.length; i++) {
    if (candidates[i] >= rawStep) return candidates[i];
  }
  return Math.ceil(rawStep / 50000) * 50000;
}

/**
 * Menggambar Grafik Interaktif SVG dengan Shading Deviasi Positif (Merah) & Negatif (Biru)
 * Lengkap dengan interpolasi linear persis pada titik potong (crossing points)
 */
function renderMhwmaChartModule() {
  ensureMhwmaChartSelectors();

  const wrap = document.getElementById("mhwmaChartSvgWrapper");
  const metricsBar = document.getElementById("mhwmaChartMetricsBar");
  const titleEl = document.getElementById("mhwmaChartTitle");
  const legendActEl = document.getElementById("mhwmaLegendActualLabel");

  if (!wrap || !mhwmaChartRegionId || !mhwmaChartCommId) return;

  const series = buildMhwmaSeries(mhwmaChartRegionId, mhwmaChartCommId);
  if (!series || series.n === 0) {
    if (titleEl) titleEl.textContent = "Perkembangan Harga Aktual vs. Harga Acuan MH-WMA";
    if (legendActEl && series) legendActEl.textContent = `Harga Aktual ${series.comm.name} (${series.row.region_name})`;
    wrap.innerHTML = `
      <div class="h-[320px] flex flex-col items-center justify-center text-center p-6 bg-slate-50/70 rounded-xl">
        <div class="text-2xl mb-2">📭</div>
        <div class="text-sm font-extrabold text-slate-700">Data Harga ${series ? series.comm.name : ""} Belum Tersedia untuk ${series ? series.row.region_name : ""}</div>
        <p class="text-xs text-slate-500 mt-1 max-w-md">Komoditas ini tidak tercatat dalam survei harian resmi ${series ? series.row.source : ""} pada wilayah bersangkutan. Silakan pilih kombinasi wilayah atau komoditas lain.</p>
      </div>
    `;
    if (metricsBar) metricsBar.innerHTML = "";
    mhwmaVisiblePtsCache = [];
    return;
  }

  const { row, comm, pts } = series;

  // Slice rentang periode sesuai tombol
  let vis = pts;
  if (mhwmaChartRange !== "all" && pts.length > 0) {
    const endTs = pts[pts.length - 1].ts;
    const daysBack = mhwmaChartRange === "3m" ? 92 : (mhwmaChartRange === "6m" ? 183 : 366);
    const cutoffTs = endTs - daysBack * 86400000;
    const sliced = pts.filter(p => p.ts >= cutoffTs);
    if (sliced.length >= 2) vis = sliced;
  }

  if (titleEl) titleEl.textContent = "Perkembangan Harga Aktual vs. Harga Acuan MH-WMA";
  if (legendActEl) legendActEl.textContent = `Harga Aktual ${comm.name} (${row.region_name})`;

  // Kalkulasi domain Y
  let minVal = Infinity;
  let maxVal = -Infinity;
  vis.forEach(p => {
    if (p.actual < minVal) minVal = p.actual;
    if (p.actual > maxVal) maxVal = p.actual;
    if (p.mhWma !== null) {
      if (p.mhWma < minVal) minVal = p.mhWma;
      if (p.mhWma > maxVal) maxVal = p.mhWma;
    }
  });
  if (!Number.isFinite(minVal) || !Number.isFinite(maxVal)) {
    minVal = 0; maxVal = 10000;
  }
  const rawSpan = Math.max(1000, maxVal - minVal);
  const paddedMin = Math.max(0, minVal - rawSpan * 0.08);
  const paddedMax = maxVal + rawSpan * 0.09;
  const tickStep = pickNiceStep((paddedMax - paddedMin) / 5.5);
  const minY = Math.floor(paddedMin / tickStep) * tickStep;
  const maxY = Math.ceil(paddedMax / tickStep) * tickStep;
  const spanY = Math.max(1, maxY - minY);

  // Dimensi SVG
  const svgW = 1040;
  const svgH = 365;
  const padL = 78;
  const padR = 22;
  const padT = 16;
  const padB = 34;
  const plotW = svgW - padL - padR;
  const plotH = svgH - padT - padB;
  const denomX = Math.max(1, vis.length - 1);

  const mapX = (i) => padL + (i / denomX) * plotW;
  const mapY = (v) => padT + (1 - (v - minY) / spanY) * plotH;

  mhwmaVisiblePtsCache = vis.map((p, k) => ({
    ...p,
    svgX: mapX(k),
    svgYAct: mapY(p.actual),
    svgYMh: p.mhWma !== null ? mapY(p.mhWma) : null
  }));
  mhwmaChartGeomCache = { svgW, svgH, padL, padR, padT, padB, plotW, plotH, minY, maxY };

  // 1. Horizontal Gridlines + Y Labels
  let gridSvg = "";
  for (let val = minY; val <= maxY + 0.01; val += tickStep) {
    const yy = mapY(val).toFixed(2);
    gridSvg += `<line x1="${padL}" y1="${yy}" x2="${svgW - padR}" y2="${yy}" stroke="#e2e8f0" stroke-width="1" stroke-dasharray="3 3" />`;
    gridSvg += `<text x="${padL - 8}" y="${Number(yy) + 3.5}" text-anchor="end" font-size="10.5" font-weight="600" fill="#64748b">${fmtRpId(val)}</text>`;
  }

  // 2. X-Axis Gridlines + Month Labels: HANYA Januari, April, Juli, Oktober
  // (Apabila data Januari 2024 belum tersedia seperti pada SP2KP, tampilkan Februari 2024 sebagai label awal)
  let xAxisSvg = "";
  const hasJan2024 = mhwmaVisiblePtsCache.some(p => p.dt.getFullYear() === 2024 && p.dt.getMonth() === 0);
  let lastLabelX = -999;
  let prevMonthKey = "";
  mhwmaVisiblePtsCache.forEach((p) => {
    const yr = p.dt.getFullYear();
    const mo = p.dt.getMonth();
    const mKey = `${yr}-${mo}`;
    if (mKey !== prevMonthKey) {
      prevMonthKey = mKey;
      const isQuarterMonth = (mo === 0 || mo === 3 || mo === 6 || mo === 9);
      const isFeb2024Fallback = (!hasJan2024 && yr === 2024 && mo === 1 && mhwmaChartRange === "all");
      if ((isQuarterMonth || isFeb2024Fallback) && p.svgX - lastLabelX >= 42 && p.svgX <= svgW - 22) {
        const lbl = `${MHWMA_MONTHS_SHORT[mo]} ${yr}`;
        xAxisSvg += `<line x1="${p.svgX.toFixed(1)}" y1="${padT}" x2="${p.svgX.toFixed(1)}" y2="${padT + plotH}" stroke="#f1f5f9" stroke-width="1" />`;
        xAxisSvg += `<text x="${p.svgX.toFixed(1)}" y="${svgH - 11}" text-anchor="middle" font-size="10.5" font-weight="600" fill="#64748b">${lbl}</text>`;
        lastLabelX = p.svgX;
      }
    }
  });

  // 3. Poligon Shading Deviasi Positif (Merah) & Deviasi Negatif (Biru) dengan Crossing Interpolation
  const posPaths = [];
  const negPaths = [];
  const activeSlice = mhwmaVisiblePtsCache.filter(p => p.mhWma !== null);

  if (activeSlice.length >= 2) {
    let topPts = [[activeSlice[0].svgX, activeSlice[0].svgYAct]];
    let botPts = [[activeSlice[0].svgX, activeSlice[0].svgYMh]];
    let curSign = (activeSlice[0].actual - activeSlice[0].mhWma) > 0 ? 1 : -1;

    const flushPoly = (signVal, tArr, bArr) => {
      if (tArr.length < 2) return;
      const allPts = tArr.concat([...bArr].reverse());
      const dStr = "M " + allPts.map(pt => `${pt[0].toFixed(2)},${pt[1].toFixed(2)}`).join(" L ") + " Z";
      if (signVal > 0) posPaths.push(dStr);
      else negPaths.push(dStr);
    };

    for (let k = 1; k < activeSlice.length; k++) {
      const p0 = activeSlice[k - 1];
      const p1 = activeSlice[k];
      const diff0 = p0.actual - p0.mhWma;
      const diff1 = p1.actual - p1.mhWma;

      if ((curSign > 0 && diff1 < 0) || (curSign < 0 && diff1 > 0)) {
        const denom = Math.abs(diff0) + Math.abs(diff1);
        const t = denom > 0 ? (Math.abs(diff0) / denom) : 0.5;
        const xc = p0.svgX + t * (p1.svgX - p0.svgX);
        const ym = p0.svgYMh + t * (p1.svgYMh - p0.svgYMh);

        topPts.push([xc, ym]);
        botPts.push([xc, ym]);
        flushPoly(curSign, topPts, botPts);

        curSign = -curSign;
        topPts = [[xc, ym], [p1.svgX, p1.svgYAct]];
        botPts = [[xc, ym], [p1.svgX, p1.svgYMh]];
      } else {
        topPts.push([p1.svgX, p1.svgYAct]);
        botPts.push([p1.svgX, p1.svgYMh]);
      }
    }
    flushPoly(curSign, topPts, botPts);
  }

  const posFillSvg = posPaths.map(d => `<path d="${d}" fill="rgba(239, 68, 68, 0.20)" stroke="none" />`).join("");
  const negFillSvg = negPaths.map(d => `<path d="${d}" fill="rgba(59, 130, 246, 0.18)" stroke="none" />`).join("");

  // 4. Garis Harga Aktual (Biru) & Garis Harga Acuan MH-WMA (Oranye)
  const actualLineD = "M " + mhwmaVisiblePtsCache.map(p => `${p.svgX.toFixed(2)},${p.svgYAct.toFixed(2)}`).join(" L ");
  const mhwmaLineD = activeSlice.length >= 2
    ? ("M " + activeSlice.map(p => `${p.svgX.toFixed(2)},${p.svgYMh.toFixed(2)}`).join(" L "))
    : "";

  const lastPt = mhwmaVisiblePtsCache[mhwmaVisiblePtsCache.length - 1];

  wrap.innerHTML = `
    <div class="relative w-full">
      <svg
        id="mhwmaSvgCanvas"
        viewBox="0 0 ${svgW} ${svgH}"
        class="w-full h-auto block cursor-crosshair touch-none"
        onmousemove="handleMhwmaChartHover(event)"
        onmouseleave="hideMhwmaChartHover()"
        ontouchmove="handleMhwmaChartTouch(event)"
        ontouchend="hideMhwmaChartHover()"
      >
        <!-- Frame & Grid -->
        <rect x="${padL}" y="${padT}" width="${plotW}" height="${plotH}" fill="#ffffff" stroke="#cbd5e1" stroke-width="1" />
        ${xAxisSvg}
        ${gridSvg}

        <!-- Area Shading Deviasi Positif (Merah) & Negatif (Biru) -->
        ${posFillSvg}
        ${negFillSvg}

        <!-- Garis Utama -->
        <path d="${actualLineD}" fill="none" stroke="#2563eb" stroke-width="1.85" stroke-linejoin="round" stroke-linecap="round" />
        ${mhwmaLineD ? `<path d="${mhwmaLineD}" fill="none" stroke="#f97316" stroke-width="2.1" stroke-linejoin="round" stroke-linecap="round" />` : ""}

        <!-- Endpoint Dots -->
        <circle cx="${lastPt.svgX.toFixed(2)}" cy="${lastPt.svgYAct.toFixed(2)}" r="3.6" fill="#2563eb" stroke="#ffffff" stroke-width="1.5" />
        ${lastPt.svgYMh !== null ? `<circle cx="${lastPt.svgX.toFixed(2)}" cy="${lastPt.svgYMh.toFixed(2)}" r="3.6" fill="#f97316" stroke="#ffffff" stroke-width="1.5" />` : ""}

        <!-- Interactive Crosshair (Hidden until hover) -->
        <line id="mhwmaCrossLine" x1="0" y1="${padT}" x2="0" y2="${padT + plotH}" stroke="#334155" stroke-width="1" stroke-dasharray="3 3" visibility="hidden" />
        <circle id="mhwmaCrossDotAct" cx="0" cy="0" r="4.8" fill="#2563eb" stroke="#ffffff" stroke-width="2" visibility="hidden" />
        <circle id="mhwmaCrossDotMh" cx="0" cy="0" r="4.8" fill="#f97316" stroke="#ffffff" stroke-width="2" visibility="hidden" />
      </svg>

      <!-- Floating Hover Tooltip Box -->
      <div id="mhwmaChartHoverCard" class="hidden pointer-events-none absolute top-3 left-20 z-20 bg-white/95 backdrop-blur-md border border-slate-300 rounded-2xl p-3 shadow-lg text-xs max-w-[290px]"></div>
    </div>
  `;

  // 5. Render Strip Ringkasan Harga Terkini Bawah Grafik (3 Kartu Utama)
  if (metricsBar) {
    const latestFull = pts[pts.length - 1];
    const isPosLatest = latestFull.mhWma !== null && ((latestFull.actual - latestFull.mhWma) > MHWMA_EPS);
    const statusBadge = latestFull.mhWma === null
      ? '<span class="px-2.5 py-0.5 rounded-lg text-xs font-extrabold bg-slate-100 text-slate-600">&lt; 120 hari</span>'
      : (isPosLatest
          ? `<span class="px-2.5 py-0.5 rounded-lg text-xs font-extrabold bg-rose-100 text-rose-800 border border-rose-200">Positif (${fmtPctId(latestFull.devPct)})</span>`
          : `<span class="px-2.5 py-0.5 rounded-lg text-xs font-extrabold bg-sky-100 text-sky-800 border border-sky-200">Negatif (${fmtPctId(latestFull.devPct)})</span>`);

    metricsBar.innerHTML = `
      <div class="p-4 rounded-2xl bg-blue-50/70 border border-blue-200/80">
        <div class="text-xs font-bold text-blue-700 uppercase tracking-wider">Harga Aktual (${latestFull.dateStr})</div>
        <div class="text-lg md:text-xl font-black text-slate-900 mt-1">${fmtRpId(latestFull.actual)} <span class="text-xs font-semibold text-slate-500">/ ${comm.satuan}</span></div>
      </div>
      <div class="p-4 rounded-2xl bg-orange-50/70 border border-orange-200/80">
        <div class="text-xs font-bold text-orange-700 uppercase tracking-wider">Harga Acuan MH-WMA</div>
        <div class="text-lg md:text-xl font-black text-slate-900 mt-1">${latestFull.mhWma !== null ? fmtRpId(latestFull.mhWma) : "-"}</div>
      </div>
      <div class="p-4 rounded-2xl bg-slate-50 border border-slate-200/90">
        <div class="text-xs font-bold text-slate-500 uppercase tracking-wider">Deviasi &amp; Status</div>
        <div class="mt-1.5 flex items-center gap-1 flex-wrap">${statusBadge}</div>
      </div>
    `;
  }
}

function handleMhwmaChartTouch(e) {
  if (e.touches && e.touches.length > 0) {
    handleMhwmaChartHover({ clientX: e.touches[0].clientX, clientY: e.touches[0].clientY });
  }
}

function handleMhwmaChartHover(e) {
  const svg = document.getElementById("mhwmaSvgCanvas");
  const card = document.getElementById("mhwmaChartHoverCard");
  const crossLine = document.getElementById("mhwmaCrossLine");
  const dotAct = document.getElementById("mhwmaCrossDotAct");
  const dotMh = document.getElementById("mhwmaCrossDotMh");

  if (!svg || !card || !mhwmaChartGeomCache || mhwmaVisiblePtsCache.length === 0) return;

  const rect = svg.getBoundingClientRect();
  if (!rect.width) return;

  const relX = ((e.clientX - rect.left) / rect.width) * mhwmaChartGeomCache.svgW;
  const clampedX = Math.max(mhwmaChartGeomCache.padL, Math.min(mhwmaChartGeomCache.svgW - mhwmaChartGeomCache.padR, relX));

  // Binary search titik terdekat
  let lo = 0;
  let hi = mhwmaVisiblePtsCache.length - 1;
  while (lo < hi) {
    const mid = (lo + hi) >> 1;
    if (mhwmaVisiblePtsCache[mid].svgX < clampedX) lo = mid + 1;
    else hi = mid;
  }
  if (lo > 0 && Math.abs(mhwmaVisiblePtsCache[lo - 1].svgX - clampedX) < Math.abs(mhwmaVisiblePtsCache[lo].svgX - clampedX)) {
    lo = lo - 1;
  }
  const pt = mhwmaVisiblePtsCache[lo];
  if (!pt) return;

  if (crossLine) {
    crossLine.setAttribute("x1", pt.svgX.toFixed(2));
    crossLine.setAttribute("x2", pt.svgX.toFixed(2));
    crossLine.setAttribute("visibility", "visible");
  }
  if (dotAct) {
    dotAct.setAttribute("cx", pt.svgX.toFixed(2));
    dotAct.setAttribute("cy", pt.svgYAct.toFixed(2));
    dotAct.setAttribute("visibility", "visible");
  }
  if (dotMh) {
    if (pt.svgYMh !== null) {
      dotMh.setAttribute("cx", pt.svgX.toFixed(2));
      dotMh.setAttribute("cy", pt.svgYMh.toFixed(2));
      dotMh.setAttribute("visibility", "visible");
    } else {
      dotMh.setAttribute("visibility", "hidden");
    }
  }

  let devHtml = '<span class="text-slate-400 font-semibold">Menunggu akumulasi 120 hari untuk MH-WMA</span>';
  if (pt.mhWma !== null) {
    const isPos = (pt.actual - pt.mhWma) > MHWMA_EPS;
    const badgeCls = isPos ? "bg-rose-100 text-rose-800 border-rose-200" : "bg-sky-100 text-sky-800 border-sky-200";
    const statusTxt = isPos ? "Deviasi Positif" : "Deviasi Negatif";
    devHtml = `
      <div class="flex items-center justify-between pt-1.5 mt-1 border-t border-slate-100">
        <span class="px-1.5 py-0.5 rounded text-[11px] font-black border ${badgeCls}">${statusTxt}</span>
        <strong class="font-black ${isPos ? 'text-rose-700' : 'text-sky-700'}">${fmtDiffRpId(pt.devRp)} (${fmtPctId(pt.devPct)})</strong>
      </div>
      <div class="grid grid-cols-2 gap-x-3 gap-y-0.5 pt-1.5 mt-1 border-t border-slate-100 text-[11px] text-slate-600">
        <div>MA5 (8,8%): <strong class="text-slate-800">${fmtRpId(pt.ma5)}</strong></div>
        <div>MA20 (17,6%): <strong class="text-slate-800">${fmtRpId(pt.ma20)}</strong></div>
        <div>MA60 (30,5%): <strong class="text-slate-800">${fmtRpId(pt.ma60)}</strong></div>
        <div>MA120 (43,1%): <strong class="text-slate-800">${fmtRpId(pt.ma120)}</strong></div>
      </div>
    `;
  }

  card.innerHTML = `
    <div class="font-extrabold text-slate-900 border-b border-slate-100 pb-1 mb-1.5">${formatFullDateId(pt.dateStr)}</div>
    <div class="space-y-1 text-xs">
      <div class="flex items-center justify-between gap-4">
        <span class="text-blue-700 font-bold">&#9679; Harga Aktual</span>
        <strong class="text-slate-900 font-black">${fmtRpId(pt.actual)}</strong>
      </div>
      <div class="flex items-center justify-between gap-4">
        <span class="text-orange-600 font-bold">&#9679; Acuan MH-WMA</span>
        <strong class="text-slate-900 font-black">${pt.mhWma !== null ? fmtRpId(pt.mhWma) : "-"}</strong>
      </div>
      ${devHtml}
    </div>
  `;
  card.classList.remove("hidden");

  // Posisikan tooltip kiri atau kanan garis agar tidak menabrak kursor
  const pctX = pt.svgX / mhwmaChartGeomCache.svgW;
  if (pctX > 0.62) {
    card.style.left = "auto";
    card.style.right = `${Math.round((1 - pctX) * rect.width + 18)}px`;
  } else {
    card.style.right = "auto";
    card.style.left = `${Math.max(82, Math.round(pctX * rect.width + 16))}px`;
  }
}

function hideMhwmaChartHover() {
  const card = document.getElementById("mhwmaChartHoverCard");
  const crossLine = document.getElementById("mhwmaCrossLine");
  const dotAct = document.getElementById("mhwmaCrossDotAct");
  const dotMh = document.getElementById("mhwmaCrossDotMh");
  if (card) card.classList.add("hidden");
  if (crossLine) crossLine.setAttribute("visibility", "hidden");
  if (dotAct) dotAct.setAttribute("visibility", "hidden");
  if (dotMh) dotMh.setAttribute("visibility", "hidden");
}

/**
 * Render Utama Seluruh Komponen Tab Deteksi Lonjakan Harga
 */
function renderAlps17MatrixModule(forceReload) {
  ensureMhwmaChartSelectors();
  renderMhwmaChartModule();

  if (window.renderMathInElement) {
    try {
      const tabRoot = document.getElementById("tabContent_alps");
      if (tabRoot) {
        renderMathInElement(tabRoot, {
          delimiters: [
            { left: "$$", right: "$$", display: true },
            { left: "\\(", right: "\\)", display: false },
            { left: "$", right: "$", display: false }
          ],
          throwOnError: false
        });
      }
    } catch (kErr) {
      console.warn("KaTeX render notice:", kErr);
    }
  }
}

// Stub kompatibilitas mundur
function renderAlps17MatrixOnly() {}
function onAlpsFilterRiskChange() {}
function onAlpsFilterRegionChange() {}
function onAlpsFilterCommodityChange() {}
function quickFilterAlpsRisk() {}
function resetAlps17Filters() {}
function onAlpsCellClick() {}
function showAlps17Tooltip() {}
function positionAlps17Tooltip() {}
function hideAlps17Tooltip() {}
function updateAlpsRiskFilterUI() {}
function onAlpsRiskDropdownChange() {}
function toggleAlpsRiskDropdown() {}
function closeAlpsRiskDropdown() {}
function onAlpsRiskCheckboxChange() {}
function selectAllAlpsRiskFilters() {}
function resetAlps17RiskFilter() {}
function toggleAlps17RiskFilter() {}
function filterAlps17Group() {}
function onAlpsRegionSearchInput() {}
function moveAlps17Tooltip() {}
function renderAlpsSpatialMapModule() {}
