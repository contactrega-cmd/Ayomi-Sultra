/**
 * Modul JavaScript: Kuadran Pangan (Deviasi Harga vs. Durasi Pergerakan Harga)
 * Basis Data & Perhitungan: Model MH-WMA (alpha = 0,5) dari ALPS_17_DATA.kuadran
 * Cakupan: 17 Kabupaten/Kota Se-Sultra x 10 Komoditas Pangan Strategis
 */

let kuadranHighlightK = "all"; // "all" | "K1" | "K2" | "K3" | "K4"
let kuadranFocusRegionId = "all";
let kuadranCommSortMode = "canonical"; // Terkunci urutan baku 10 komoditas
let kuadranGridCols = 2; // Terkunci 2 kolom panel per baris
let kuadranRegionSelectPopulated = false;
let kuadranSelectedHeatmapCell = null; // { regionId, qid }

const KUADRAN_COLORS = {
  K1: {
    id: "K1",
    roman: "K I",
    title: "Harga Tinggi Persisten",
    short: "Tinggi Persisten",
    rule: "Deviasi > 0%, Durasi ≥ d̄",
    dot: "#dc2626",
    dotStroke: "#7f1d1d",
    bgQuad: "#fdedec",
    titleColor: "#b91c1c",
    badgeCls: "bg-rose-100 text-rose-900 border-rose-300",
    kpiCardCls: "bg-rose-50/80 border-rose-200/90 hover:border-rose-400",
    kpiActiveRing: "bg-rose-100/90 ring-2 ring-rose-600",
    kpiNumCls: "text-rose-950",
    kpiSubCls: "text-rose-800/80"
  },
  K2: {
    id: "K2",
    roman: "K II",
    title: "Harga Tinggi Sementara",
    short: "Tinggi Sementara",
    rule: "Deviasi > 0%, Durasi < d̄",
    dot: "#eab308",
    dotStroke: "#854d0e",
    bgQuad: "#fef9db",
    titleColor: "#a16207",
    badgeCls: "bg-yellow-100 text-yellow-900 border-yellow-400",
    kpiCardCls: "bg-yellow-50/90 border-yellow-300/90 hover:border-yellow-500",
    kpiActiveRing: "bg-yellow-100/90 ring-2 ring-yellow-500",
    kpiNumCls: "text-yellow-950",
    kpiSubCls: "text-yellow-900/80"
  },
  K3: {
    id: "K3",
    roman: "K III",
    title: "Harga Rendah Persisten",
    short: "Rendah Persisten",
    rule: "Deviasi ≤ 0%, Durasi ≥ d̄",
    dot: "#2563eb",
    dotStroke: "#1e3a8a",
    bgQuad: "#eaf2fc",
    titleColor: "#1d4ed8",
    badgeCls: "bg-blue-100 text-blue-900 border-blue-300",
    kpiCardCls: "bg-blue-50/80 border-blue-200/90 hover:border-blue-400",
    kpiActiveRing: "bg-blue-100/90 ring-2 ring-blue-600",
    kpiNumCls: "text-blue-950",
    kpiSubCls: "text-blue-800/80"
  },
  K4: {
    id: "K4",
    roman: "K IV",
    title: "Harga Rendah Sementara",
    short: "Rendah Sementara",
    rule: "Deviasi ≤ 0%, Durasi < d̄",
    dot: "#16a34a",
    dotStroke: "#14532d",
    bgQuad: "#ebf8ee",
    titleColor: "#15803d",
    badgeCls: "bg-emerald-100 text-emerald-900 border-emerald-300",
    kpiCardCls: "bg-emerald-50/80 border-emerald-200/90 hover:border-emerald-400",
    kpiActiveRing: "bg-emerald-100/90 ring-2 ring-emerald-600",
    kpiNumCls: "text-emerald-950",
    kpiSubCls: "text-emerald-800/80"
  }
};

function kpFmtPct(val) {
  if (val === null || val === undefined || Number.isNaN(val)) return "N/A";
  if (val === 0) return "0,0%";
  if (Math.abs(val) < 0.05) {
    const sign = val > 0 ? "+" : "-";
    return sign + Math.abs(val).toFixed(2).replace(".", ",") + "%";
  }
  const sign = val > 0 ? "+" : "";
  return sign + val.toFixed(1).replace(".", ",") + "%";
}

function kpFmtNum(val, dec) {
  if (val === null || val === undefined || Number.isNaN(val)) return "-";
  if (dec === 0) return Math.round(val).toString();
  return Number(val).toFixed(dec).replace(".", ",");
}

function kpShortDateId(dStr) {
  if (!dStr) return "-";
  if (typeof formatFullDateId === "function") {
    return formatFullDateId(dStr).replace(/^[^,]+,\s*/, "");
  }
  return dStr;
}

function ensureKuadranControls() {
  return;
}

function toggleKuadranHighlight(qid) {
  kuadranHighlightK = (kuadranHighlightK === qid) ? "all" : qid;
  renderKuadranKpiCards();
  renderKuadranChartsGrid();
  renderKuadranDistributionHeatmap();
}

function onKuadranControlChange() {
  kuadranFocusRegionId = "all";
  kuadranCommSortMode = "canonical";
  renderKuadranChartsGrid();
}

function setKuadranGridCols() {
  kuadranGridCols = 2;
  const grid = document.getElementById("kuadranChartsGrid");
  if (grid) {
    grid.className = "grid grid-cols-1 lg:grid-cols-2 gap-5";
  }
  renderKuadranChartsGrid();
}

/**
 * Stub no-op: 4 KPI Kartu Kuadran telah dihapus dari tampilan UI Tab Kuadran Pangan
 */
function renderKuadranKpiCards() {
  const container = document.getElementById("kuadranKpiCards");
  if (container) container.innerHTML = "";
}

/**
 * Pemilihan tick rapi
 */
function pickKuadranStep(rawStep, preferSmall) {
  const cands = preferSmall
    ? [0.25, 0.5, 1, 2, 2.5, 5, 10, 15, 20, 25, 50]
    : [5, 10, 20, 25, 40, 50, 100, 150, 200];
  for (let i = 0; i < cands.length; i++) {
    if (cands[i] >= rawStep) return cands[i];
  }
  return Math.ceil(rawStep / 50) * 50;
}

/**
 * Penempatan Label Anti-Tumpuk dengan Leader Line Presisi di SVG
 */
function solveKuadranLabelLayout(ptsGeo, bounds) {
  const { plotL, plotR, plotT, plotB, safeTopY, safeBotY, fontSz, lineH, boxPadX, boxPadY, pillRect, dotClearance } = bounds;
  const minDotDist = dotClearance !== undefined ? dotClearance : 7.5;
  const charW = fontSz * 0.57;
  const minYClamp = safeTopY !== undefined ? safeTopY : (plotT + 28);
  const maxYClamp = safeBotY !== undefined ? safeBotY : (plotB - 26);

  // Obstacle wajib dihindari: pill garis d̄
  const hardObs = [];
  if (pillRect) hardObs.push(pillRect);

  const placed = [];
  // Prioritaskan titik terluar & highlight dulu supaya posisi terbaik didapat titik penting
  const order = ptsGeo.map((p, idx) => idx).sort((ia, ib) => {
    const pa = ptsGeo[ia];
    const pb = ptsGeo[ib];
    if (pa.isFocus !== pb.isFocus) return pa.isFocus ? -1 : 1;
    return pb.pt.durasi_hari - pa.pt.durasi_hari;
  });

  const baseAngles = [
    -Math.PI / 4, Math.PI / 4, -3 * Math.PI / 4, 3 * Math.PI / 4,
    0, Math.PI, -Math.PI / 2, Math.PI / 2,
    -Math.PI / 8, Math.PI / 8, -3 * Math.PI / 8, 3 * Math.PI / 8,
    -5 * Math.PI / 8, 5 * Math.PI / 8, -7 * Math.PI / 8, 7 * Math.PI / 8
  ];
  const ringRadii = [16, 26, 38, 52, 68, 86, 108, 134, 164, 198, 236];
  const upwardFanOffsets = [];
  [-85, -112, -142, -176, -214, -256].forEach(oy => {
    [0, -45, 45, -95, 95, -145, 145].forEach(ox => upwardFanOffsets.push([ox, oy]));
  });

  const boxOverlapArea = (a, b, pad = 0) => {
    const ox = Math.max(0, Math.min(a.x2 + pad, b.x2 + pad) - Math.max(a.x1 - pad, b.x1 - pad));
    const oy = Math.max(0, Math.min(a.y2 + pad, b.y2 + pad) - Math.max(a.y1 - pad, b.y1 - pad));
    return ox * oy;
  };

  const evaluateCandidate = (cand, g, idx) => {
    let score = 0;
    for (let i = 0; i < placed.length; i++) {
      const ov = boxOverlapArea(cand, placed[i].box, 0);
      if (ov > 0) score += 500000 + ov * 5000;
      else {
        const gapOv = boxOverlapArea(cand, placed[i].box, 2);
        if (gapOv > 0) score += gapOv * 80;
      }
    }
    for (let j = 0; j < ptsGeo.length; j++) {
      const dp = ptsGeo[j];
      const nx = Math.max(cand.x1, Math.min(dp.px, cand.x2));
      const ny = Math.max(cand.y1, Math.min(dp.py, cand.y2));
      const dist = Math.hypot(dp.px - nx, dp.py - ny);
      if (dist <= minDotDist) {
        score += (j === idx ? 450000 : 380000) + (minDotDist + 1 - dist) * 4000;
      }
    }
    for (let c = 0; c < hardObs.length; c++) {
      const ov = boxOverlapArea(cand, hardObs[c], 0);
      if (ov > 0) score += 800000 + ov * 8000;
      else {
        const gapOv = boxOverlapArea(cand, hardObs[c], 2);
        if (gapOv > 0) score += gapOv * 150;
      }
    }
    const cx = (cand.x1 + cand.x2) / 2;
    const cy = (cand.y1 + cand.y2) / 2;
    score += Math.hypot(cx - g.px, cy - g.py) * 0.45;
    return score;
  };

  order.forEach(idx => {
    const g = ptsGeo[idx];
    const line1 = g.pt.short_name;
    const line2 = `(${kpFmtPct(g.pt.deviasi_pct)}, ${g.pt.durasi_hari}h)`;
    const textW = Math.max(line1.length, line2.length) * charW;
    const bw = Math.max(58, Math.round(textW + boxPadX * 2));
    const bh = Math.round(lineH * 2 + boxPadY * 2);

    let bestBox = null;
    let bestScore = Infinity;
    const seen = new Set();

    const trySlot = (rawX1, rawY1) => {
      const x1 = Math.max(plotL + 4, Math.min(plotR - bw - 4, Math.round(rawX1)));
      const y1 = Math.max(minYClamp, Math.min(maxYClamp - bh, Math.round(rawY1)));
      const key = `${x1},${y1}`;
      if (seen.has(key)) return;
      seen.add(key);

      const cand = { x1, y1, x2: x1 + bw, y2: y1 + bh, bw, bh };
      const sc = evaluateCandidate(cand, g, idx);
      if (sc < bestScore) {
        bestScore = sc;
        bestBox = cand;
      }
    };

    ringRadii.forEach(r => {
      baseAngles.forEach(ang => {
        const dx = Math.cos(ang) * r;
        const dy = Math.sin(ang) * r;
        trySlot(g.px + dx - bw / 2, g.py + dy - bh / 2);
      });
    });

    upwardFanOffsets.forEach(([ox, oy]) => {
      trySlot(g.px + ox - bw / 2, g.py + oy - bh / 2);
    });

    // Jika area lokal masih penuh, sapu kisi seluruh plot agar tetap 0 tumpang tindih
    if (bestScore >= 350000) {
      for (let sy = minYClamp; sy <= maxYClamp - bh; sy += 18) {
        for (let sx = plotL + 4; sx <= plotR - bw - 4; sx += 26) {
          trySlot(sx, sy);
        }
      }
    }

    placed.push({ idx, g, line1, line2, box: bestBox });
  });

  return placed;
}

/**
 * Bangun SVG Grafik Kuadran Satu Komoditas
 */
function buildKuadranScatterSvg(commObj, isZoomMode) {
  const pts = commObj.points || [];
  if (pts.length === 0) {
    return '<div class="h-64 flex items-center justify-center text-xs text-slate-400">Data survei belum tersedia</div>';
  }

  const svgW = isZoomMode ? 900 : 660;
  const svgH = isZoomMode ? 540 : 480;
  const padL = isZoomMode ? 62 : 54;
  const padR = isZoomMode ? 24 : 20;
  const padT = isZoomMode ? 18 : 14;
  const padB = isZoomMode ? 48 : 44;
  const plotL = padL;
  const plotR = svgW - padR;
  const plotT = padT;
  const plotB = svgH - padB;
  const plotW = plotR - plotL;
  const plotH = plotB - plotT;

  // Zona bantal atas & bawah di dalam plot agar judul sudut K I..K IV selalu terpisah bersih dari titik & label
  const topPadPx = isZoomMode ? 32 : 30;
  const botPadPx = isZoomMode ? 28 : 26;
  const dataTopPx = plotT + topPadPx;
  const dataBotPx = plotB - botPadPx;
  const dataH = Math.max(120, dataBotPx - dataTopPx);

  const dBar = Number(commObj.d_bar || 0);
  const devs = pts.map(p => Number(p.deviasi_pct || 0));
  const durs = pts.map(p => Number(p.durasi_hari || 0));

  // Domain X selalu mencakup 0 secara nyaman
  const rawMinX = Math.min(0, ...devs);
  const rawMaxX = Math.max(0, ...devs);
  const spanX0 = Math.max(1.5, rawMaxX - rawMinX);
  let minX = Math.min(rawMinX - spanX0 * 0.14, -Math.max(0.8, spanX0 * 0.22));
  let maxX = Math.max(rawMaxX + spanX0 * 0.16, Math.max(0.8, spanX0 * 0.22));
  const stepX = pickKuadranStep((maxX - minX) / 5.5, true);
  minX = Math.floor(minX / stepX) * stepX;
  maxX = Math.ceil(maxX / stepX) * stepX;
  if (minX >= 0) minX = -stepX;
  if (maxX <= 0) maxX = stepX;
  const domainX = Math.max(0.5, maxX - minX);

  const mapX = (xVal) => plotL + ((xVal - minX) / domainX) * plotW;

  // Domain Y linear penuh tanpa jeda skala (skala seragam dari 0 s.d. durasi maksimum)
  const maxDur = durs.length > 0 ? Math.max(...durs) : 0;
  const rawMaxY = Math.max(dBar * 1.38, maxDur * 1.08, 12);
  const stepY = pickKuadranStep(rawMaxY / 5.5, false);
  const yCeil = Math.ceil(rawMaxY / stepY) * stepY;
  const mapY = (yVal) => dataBotPx - (Math.max(0, yVal) / yCeil) * dataH;
  const yTicks = [];
  for (let v = 0; v <= yCeil + 0.01; v += stepY) {
    yTicks.push(v);
  }

  const zeroX = mapX(0);
  const dBarY = mapY(dBar);

  // Latar 4 Kuadran Pastel
  const qLeftW = Math.max(0, zeroX - plotL);
  const qRightW = Math.max(0, plotR - zeroX);
  const qTopH = Math.max(0, dBarY - plotT);
  const qBotH = Math.max(0, plotB - dBarY);

  const minWCls = isZoomMode ? "min-w-[640px] sm:min-w-0" : "min-w-[540px] sm:min-w-0";
  let svg = `<svg viewBox="0 0 ${svgW} ${svgH}" class="${minWCls} w-full h-auto block select-none" role="img" aria-label="Kuadran ${commObj.comm_name}">`;

  // 4 Quadrant Rectangles (K III Biru top-left, K I Merah top-right, K IV Hijau bottom-left, K II Kuning bottom-right)
  svg += `<rect x="${plotL.toFixed(1)}" y="${plotT.toFixed(1)}" width="${qLeftW.toFixed(1)}" height="${qTopH.toFixed(1)}" fill="${KUADRAN_COLORS.K3.bgQuad}" />`;
  svg += `<rect x="${zeroX.toFixed(1)}" y="${plotT.toFixed(1)}" width="${qRightW.toFixed(1)}" height="${qTopH.toFixed(1)}" fill="${KUADRAN_COLORS.K1.bgQuad}" />`;
  svg += `<rect x="${plotL.toFixed(1)}" y="${dBarY.toFixed(1)}" width="${qLeftW.toFixed(1)}" height="${qBotH.toFixed(1)}" fill="${KUADRAN_COLORS.K4.bgQuad}" />`;
  svg += `<rect x="${zeroX.toFixed(1)}" y="${dBarY.toFixed(1)}" width="${qRightW.toFixed(1)}" height="${qBotH.toFixed(1)}" fill="${KUADRAN_COLORS.K2.bgQuad}" />`;

  // Gridlines X
  for (let vx = minX; vx <= maxX + 1e-6; vx += stepX) {
    const xv = Math.abs(vx) < 1e-6 ? 0 : vx;
    const xx = mapX(xv).toFixed(1);
    svg += `<line x1="${xx}" y1="${plotT}" x2="${xx}" y2="${plotB}" stroke="#cbd5e1" stroke-width="0.7" stroke-dasharray="2.5 2.5" opacity="0.75" />`;
    const lblX = Math.abs(stepX) < 1 ? kpFmtNum(xv, 1) : (Number.isInteger(xv) ? xv.toString() : kpFmtNum(xv, 1));
    svg += `<text x="${xx}" y="${plotB + 16}" text-anchor="middle" font-size="${isZoomMode ? 11.5 : 10}" font-weight="600" fill="#475569">${lblX}</text>`;
  }

  // Gridlines Y (linear penuh)
  yTicks.forEach(vy => {
    const yy = mapY(vy).toFixed(1);
    svg += `<line x1="${plotL}" y1="${yy}" x2="${plotR}" y2="${yy}" stroke="#cbd5e1" stroke-width="0.7" stroke-dasharray="2.5 2.5" opacity="0.75" />`;
    svg += `<text x="${plotL - 7}" y="${(Number(yy) + 3.5).toFixed(1)}" text-anchor="end" font-size="${isZoomMode ? 11.5 : 10}" font-weight="600" fill="#475569">${Math.round(vy)}</text>`;
  });

  // Garis Pembatas Utama (X = 0% & Y = d_bar)
  svg += `<line x1="${zeroX.toFixed(1)}" y1="${plotT}" x2="${zeroX.toFixed(1)}" y2="${plotB}" stroke="#334155" stroke-width="1.35" stroke-dasharray="4 3" />`;
  svg += `<line x1="${plotL}" y1="${dBarY.toFixed(1)}" x2="${plotR}" y2="${dBarY.toFixed(1)}" stroke="#334155" stroke-width="1.35" stroke-dasharray="4 3" />`;

  // Border Plot Outer Frame
  svg += `<rect x="${plotL}" y="${plotT}" width="${plotW}" height="${plotH}" fill="none" stroke="#94a3b8" stroke-width="1.1" />`;

  // Label Sudut 4 Kuadran (adaptif terhadap lebar kuadran agar tidak melintasi X=0%)
  const qTitFs = isZoomMode ? 11 : 9.2;
  const qSubFs = isZoomMode ? 9.2 : 7.8;

  const drawCornerLabel = (qW, qH, xPos, anchor, topNotBot, titleLong, titleShort, subLong, subShort, col) => {
    if (qH < 28 || qW < 55) return;
    const tTxt = qW >= 185 ? titleLong : (qW >= 115 ? titleShort : titleShort.split(":")[0]);
    const sTxt = qW >= 185 ? subLong : (qW >= 105 ? subShort : "");
    const yT = topNotBot ? (plotT + 13) : (plotB - 14);
    const yS = topNotBot ? (plotT + 23.5) : (plotB - 4.5);
    svg += `<text x="${xPos}" y="${yT}" text-anchor="${anchor}" font-size="${qTitFs}" font-weight="900" fill="${col}">${tTxt}</text>`;
    if (sTxt) {
      svg += `<text x="${xPos}" y="${yS}" text-anchor="${anchor}" font-size="${qSubFs}" font-weight="700" fill="${col}" opacity="0.88">${sTxt}</text>`;
    }
  };

  drawCornerLabel(qLeftW, qTopH, plotL + 8, "start", true,
    "↓ K III: HARGA RENDAH PERSISTEN", "↓ K III: RENDAH PERSISTEN",
    "(Deviasi ≤ 0%, Durasi ≥ d̄)", "(≤ 0%, ≥ d̄)", KUADRAN_COLORS.K3.titleColor);
  drawCornerLabel(qRightW, qTopH, plotR - 8, "end", true,
    "↑ K I: HARGA TINGGI PERSISTEN", "↑ K I: TINGGI PERSISTEN",
    "(Deviasi &gt; 0%, Durasi ≥ d̄)", "(&gt; 0%, ≥ d̄)", KUADRAN_COLORS.K1.titleColor);
  drawCornerLabel(qLeftW, qBotH, plotL + 8, "start", false,
    "↓ K IV: HARGA RENDAH SEMENTARA", "↓ K IV: RENDAH SEMENTARA",
    "(Deviasi ≤ 0%, Durasi &lt; d̄)", "(≤ 0%, &lt; d̄)", KUADRAN_COLORS.K4.titleColor);
  drawCornerLabel(qRightW, qBotH, plotR - 8, "end", false,
    "↑ K II: HARGA TINGGI SEMENTARA", "↑ K II: TINGGI SEMENTARA",
    "(Deviasi &gt; 0%, Durasi &lt; d̄)", "(&gt; 0%, &lt; d̄)", KUADRAN_COLORS.K2.titleColor);

  // Hitung koordinat seluruh titik aktif
  const hasFocusFilter = (kuadranFocusRegionId !== "all" || kuadranHighlightK !== "all");
  const ptsGeo = pts.map(pt => {
    const matchReg = (kuadranFocusRegionId === "all" || pt.region_id === kuadranFocusRegionId);
    const matchK = (kuadranHighlightK === "all" || pt.kuadran_id === kuadranHighlightK);
    const isFocus = hasFocusFilter && matchReg && matchK;
    const isDim = hasFocusFilter && (!matchReg || !matchK);
    return {
      pt,
      px: mapX(Number(pt.deviasi_pct || 0)),
      py: mapY(Number(pt.durasi_hari || 0)),
      isFocus,
      isDim
    };
  });

  // Pill Label d̄ horizontal: lebar ringkas & evaluasi kandidat posisi geser (kiri/kanan/sepanjang sumbu X x atas/bawah d̄) agar 100% bebas dot
  const dBarText = `d̄ (Rerata Sultra) = ${kpFmtNum(dBar, 1)} hari`;
  const pillFs = isZoomMode ? 9.5 : 8.4;
  const pillW = Math.max(isZoomMode ? 204 : 182, Math.ceil(dBarText.length * pillFs * 0.58) + 18);
  const pillH = 17;
  const dotPad = (isZoomMode ? 6.5 : 5.4) + 5;
  const yAbove = dBarY - pillH - 3;
  const yBelow = dBarY + 4;
  const maxPillX = Math.max(plotL + 8, plotR - pillW - 8);
  const candXSet = new Set([plotL + 8, maxPillX]);
  if (zeroX - pillW - 8 >= plotL + 6) candXSet.add(Math.round(zeroX - pillW - 8));
  if (zeroX + 8 <= maxPillX) candXSet.add(Math.round(zeroX + 8));
  for (let gx = plotL + 8; gx <= maxPillX; gx += 28) {
    candXSet.add(Math.round(gx));
  }
  const candX = [...candXSet];
  const candY = [];
  if (yAbove >= dataTopPx - 2) candY.push({ y: yAbove, isAbove: true });
  if (yBelow + pillH <= dataBotPx + 6) candY.push({ y: yBelow, isAbove: false });
  if (candY.length === 0) candY.push({ y: Math.max(plotT + 4, yAbove), isAbove: true });

  let bestPill = { x: candX[0], y: candY[0].y, score: Infinity };
  candX.forEach(cx => {
    const crossesZero = (cx < zeroX) && ((cx + pillW) > zeroX);
    const distFromEdge = Math.min(cx - (plotL + 8), maxPillX - cx);
    candY.forEach(cyObj => {
      const cy = cyObj.y;
      let sc = (cyObj.isAbove ? 0 : 4) + distFromEdge * 0.08;
      if (crossesZero) sc += 30;
      ptsGeo.forEach(g => {
        const nx = Math.max(cx, Math.min(g.px, cx + pillW));
        const ny = Math.max(cy, Math.min(g.py, cy + pillH));
        const dist = Math.hypot(g.px - nx, g.py - ny);
        if (dist <= dotPad) {
          sc += 20000 + (dotPad - dist) * 500;
        } else if (dist <= dotPad + 14) {
          sc += 250;
        }
      });
      if (sc < bestPill.score) {
        bestPill = { x: cx, y: cy, score: sc };
      }
    });
  });
  const pillX = bestPill.x;
  const pillY = bestPill.y;
  const pillRect = { x1: pillX, y1: pillY, x2: pillX + pillW, y2: pillY + pillH };

  svg += `<rect x="${pillX.toFixed(1)}" y="${pillY.toFixed(1)}" width="${pillW}" height="${pillH}" rx="4" fill="#ffffff" stroke="#64748b" stroke-width="0.95" opacity="0.96" />`;
  svg += `<text x="${(pillX + pillW / 2).toFixed(1)}" y="${(pillY + 11.8).toFixed(1)}" text-anchor="middle" font-size="${pillFs}" font-weight="800" fill="#1e293b">${dBarText}</text>`;

  // Layout label non-overlapping dalam zona aman [dataTopPx, dataBotPx - 2]
  const labelFontSz = isZoomMode ? 10 : 8.8;
  const placedLabels = solveKuadranLabelLayout(ptsGeo, {
    plotL, plotR, plotT, plotB,
    safeTopY: dataTopPx,
    safeBotY: Math.max(dataBotPx, plotB - 28),
    fontSz: labelFontSz,
    lineH: isZoomMode ? 11.5 : 10.4,
    boxPadX: isZoomMode ? 6 : 4.5,
    boxPadY: isZoomMode ? 3.5 : 2.8,
    pillRect,
    dotClearance: isZoomMode ? 8.5 : 7.0
  });

  // 1. Leader lines & label boxes (di bawah titik)
  placedLabels.forEach(item => {
    const { g, line1, line2, box } = item;
    const cx = Math.max(box.x1, Math.min(box.x2, g.px));
    const cy = Math.max(box.y1, Math.min(box.y2, g.py));
    const op = g.isDim ? "0.2" : "0.95";
    const strokeCol = g.isFocus ? "#4338ca" : "#94a3b8";
    const bgFill = g.isFocus ? "#eef2ff" : "#ffffff";
    const textCol = g.isFocus ? "#1e1b4b" : "#1e293b";

    svg += `<g opacity="${op}" class="cursor-pointer" onmousemove="showKuadranDotTooltip(event, '${commObj.comm_id}', '${g.pt.region_id}')" onmouseleave="hideKuadranDotTooltip()" onclick="focusKuadranSingleRegion('${g.pt.region_id}')">`;
    svg += `<line x1="${g.px.toFixed(1)}" y1="${g.py.toFixed(1)}" x2="${cx.toFixed(1)}" y2="${cy.toFixed(1)}" stroke="${strokeCol}" stroke-width="${g.isFocus ? '1.35' : '0.85'}" />`;
    svg += `<rect x="${box.x1.toFixed(1)}" y="${box.y1.toFixed(1)}" width="${box.bw}" height="${box.bh}" rx="3.5" fill="${bgFill}" fill-opacity="0.92" stroke="${g.isFocus ? '#6366f1' : '#cbd5e1'}" stroke-width="${g.isFocus ? '1.2' : '0.7'}" />`;
    const tx = (box.x1 + box.bw / 2).toFixed(1);
    const ty1 = (box.y1 + (isZoomMode ? 11.5 : 10.3)).toFixed(1);
    const ty2 = (box.y1 + (isZoomMode ? 22 : 19.8)).toFixed(1);
    svg += `<text x="${tx}" y="${ty1}" text-anchor="middle" font-size="${labelFontSz}" font-weight="800" fill="${textCol}">${line1}</text>`;
    svg += `<text x="${tx}" y="${ty2}" text-anchor="middle" font-size="${(labelFontSz - 0.6).toFixed(1)}" font-weight="700" fill="#475569">${line2}</text>`;
    svg += `</g>`;
  });

  // 2. Dots (di atas label)
  ptsGeo.forEach(g => {
    const kc = KUADRAN_COLORS[g.pt.kuadran_id] || KUADRAN_COLORS.K4;
    const baseR = isZoomMode ? 6.5 : 5.4;
    const r = g.isFocus ? baseR + 2 : baseR;
    const op = g.isDim ? "0.22" : "1";

    svg += `<g opacity="${op}" class="cursor-pointer" onmousemove="showKuadranDotTooltip(event, '${commObj.comm_id}', '${g.pt.region_id}')" onmouseleave="hideKuadranDotTooltip()" onclick="focusKuadranSingleRegion('${g.pt.region_id}')">`;
    if (g.isFocus) {
      svg += `<circle cx="${g.px.toFixed(1)}" cy="${g.py.toFixed(1)}" r="${r + 4}" fill="${kc.dot}" opacity="0.22" />`;
    }
    svg += `<circle cx="${g.px.toFixed(1)}" cy="${g.py.toFixed(1)}" r="${r}" fill="${kc.dot}" stroke="${g.isFocus ? '#1e1b4b' : '#0f172a'}" stroke-width="${g.isFocus ? '2' : '1.25'}" />`;
    svg += `</g>`;
  });

  // Axis Titles
  svg += `<text x="${(plotL + plotW / 2).toFixed(1)}" y="${svgH - 8}" text-anchor="middle" font-size="${isZoomMode ? 11.5 : 10}" font-weight="800" fill="#334155">Score MH-WMA / Deviasi Harga Aktual terhadap Harga Acuan (%)</text>`;
  const yLblX = 14;
  const yLblY = (plotT + plotH / 2).toFixed(1);
  svg += `<text x="${yLblX}" y="${yLblY}" text-anchor="middle" transform="rotate(-90 ${yLblX} ${yLblY})" font-size="${isZoomMode ? 11.5 : 10}" font-weight="800" fill="#334155">Durasi Berturut-turut di Sisi Harga Terkini (Hari)</text>`;

  svg += `</svg>`;
  return svg;
}

function focusKuadranSingleRegion(regionId) {
  kuadranFocusRegionId = (kuadranFocusRegionId === regionId) ? "all" : regionId;
  renderKuadranChartsGrid();
}

/**
 * Render Grid 10 Panel Grafik Kuadran
 */
function renderKuadranChartsGrid() {
  const grid = document.getElementById("kuadranChartsGrid");
  if (!grid || typeof ALPS_17_DATA === "undefined" || !ALPS_17_DATA.kuadran) return;

  // Terkunci pada urutan baku 10 komoditas (selaras ALPS_17_DATA.commodities)
  let list = [...(ALPS_17_DATA.kuadran.by_commodity || [])];
  if (Array.isArray(ALPS_17_DATA.commodities) && ALPS_17_DATA.commodities.length > 0) {
    const orderMap = new Map(ALPS_17_DATA.commodities.map((c, idx) => [c.id, idx]));
    list.sort((a, b) => (orderMap.get(a.comm_id) ?? 999) - (orderMap.get(b.comm_id) ?? 999));
  }

  grid.innerHTML = list.map(c => {
    const svgHtml = buildKuadranScatterSvg(c, false);
    const naBadge = c.na > 0 ? `<span class="text-[9.5px] font-bold px-1.5 py-0.5 rounded bg-slate-100 text-slate-600 border border-slate-200 whitespace-nowrap shrink-0">${c.na} N/A</span>` : "";

    return `
      <div class="rounded-2xl border border-slate-200/90 bg-white shadow-2xs hover:shadow-md transition flex flex-col overflow-hidden">
        <!-- Header Card Komoditas -->
        <div class="px-3.5 sm:px-4 py-3 bg-slate-50/85 border-b border-slate-200/80 flex items-center justify-between gap-2.5 flex-wrap sm:flex-nowrap">
          <div class="min-w-0">
            <div class="flex items-center gap-1.5 flex-wrap">
              <h4 class="font-black text-slate-900 text-sm leading-snug">${c.comm_name}</h4>
              ${naBadge}
            </div>
            <div class="text-[11px] font-semibold text-slate-500 mt-0.5 leading-snug">
              ${c.active_count} Kab/Kota aktif &bull; d&#772; = <strong class="text-slate-800">${kpFmtNum(c.d_bar, 1)} hari</strong>
            </div>
          </div>

          <div class="flex flex-wrap items-center gap-1.5 shrink-0 max-w-full">
            <div class="flex flex-wrap items-center gap-1 text-[10px] font-black">
              <span class="px-1.5 py-0.5 rounded bg-rose-100 text-rose-900 border border-rose-300" title="K I (Merah): Harga Tinggi Persisten">K I:${c.k1}</span>
              <span class="px-1.5 py-0.5 rounded bg-yellow-100 text-yellow-900 border border-yellow-400" title="K II (Kuning): Harga Tinggi Sementara">K II:${c.k2}</span>
              <span class="px-1.5 py-0.5 rounded bg-blue-100 text-blue-900 border border-blue-200" title="K III (Biru): Harga Rendah Persisten">K III:${c.k3}</span>
              <span class="px-1.5 py-0.5 rounded bg-emerald-100 text-emerald-900 border border-emerald-200" title="K IV (Hijau): Harga Rendah Sementara">K IV:${c.k4}</span>
            </div>
            <button
              type="button"
              onclick="openKuadranZoomModal('${c.comm_id}')"
              class="w-7 h-7 rounded-lg bg-white hover:bg-blue-50 border border-slate-200 hover:border-blue-300 text-slate-600 hover:text-blue-800 flex items-center justify-center text-xs transition cursor-pointer shadow-2xs shrink-0"
              title="Perbesar grafik & lihat daftar 17 Kab/Kota ${c.comm_name}"
            >🔍</button>
          </div>
        </div>

        <!-- Kanvas SVG (dapat digeser horizontal di layar ponsel agar label titik tetap tajam) -->
        <div class="p-2.5 sm:p-3 bg-white flex-1">
          <div class="sm:hidden flex items-center justify-between text-[10px] font-bold text-slate-400 pb-1.5">
            <span>Ketuk titik untuk sorot</span>
            <span>&larr; Geser grafik &rarr;</span>
          </div>
          <div class="overflow-x-auto sm:overflow-visible -mx-1 px-1">
            ${svgHtml}
          </div>
        </div>
      </div>
    `;
  }).join("");
}

/**
 * Tooltip Melayang saat Hover Titik Scatter
 */
function showKuadranDotTooltip(e, commId, regionId) {
  const tip = document.getElementById("kuadranFloatingTooltip");
  if (!tip || typeof ALPS_17_DATA === "undefined" || !ALPS_17_DATA.kuadran) return;

  const commObj = (ALPS_17_DATA.kuadran.by_commodity || []).find(c => c.comm_id === commId);
  const pt = commObj && (commObj.points || []).find(p => p.region_id === regionId);
  if (!commObj || !pt) return;

  const kc = KUADRAN_COLORS[pt.kuadran_id] || KUADRAN_COLORS.K4;
  const isPos = pt.deviasi_pct > 0;
  const devCls = isPos ? "text-rose-700" : "text-sky-700";

  tip.innerHTML = `
    <div class="border-b border-slate-100 pb-2 mb-2">
      <div class="flex items-center justify-between gap-2">
        <span class="font-black text-slate-900 truncate">${pt.region_name}</span>
        <span class="px-2 py-0.5 rounded-full text-[9.5px] font-black border shrink-0 ${kc.badgeCls}">${kc.roman}</span>
      </div>
      <div class="text-[11px] font-bold text-slate-600 mt-0.5">${commObj.comm_name} &bull; <span class="text-slate-400">${pt.source}</span></div>
    </div>

    <div class="space-y-1.5 text-[11px]">
      <div class="px-2.5 py-1 rounded-lg border font-extrabold text-center ${kc.badgeCls}">
        ${kc.title}
      </div>
      <div class="grid grid-cols-2 gap-1.5 pt-0.5">
        <div class="bg-slate-50 p-1.5 rounded-lg border border-slate-200/80">
          <div class="text-[9.5px] text-slate-500 font-bold">Harga Aktual</div>
          <div class="font-black text-slate-900">${pt.harga_aktual_str}</div>
        </div>
        <div class="bg-slate-50 p-1.5 rounded-lg border border-slate-200/80">
          <div class="text-[9.5px] text-slate-500 font-bold">Acuan MH-WMA</div>
          <div class="font-black text-slate-900">${pt.harga_wajar_str}</div>
        </div>
      </div>
      <div class="flex justify-between items-center pt-1 border-t border-slate-100">
        <span class="text-slate-500 font-semibold">Price Deviation:</span>
        <strong class="font-black ${devCls}">${pt.deviasi_pct_str} (${pt.deviasi_rp_str})</strong>
      </div>
      <div class="flex justify-between items-center">
        <span class="text-slate-500 font-semibold">Durasi Sisi Terkini:</span>
        <strong class="font-black text-slate-900">${pt.durasi_hari} hari survei</strong>
      </div>
      <div class="flex justify-between items-center text-[10px] text-slate-500">
        <span>Bertahan sejak: ${pt.durasi_sejak_tgl}</span>
        <span>d&#772; = ${kpFmtNum(commObj.d_bar, 1)}h</span>
      </div>
    </div>
  `;

  tip.classList.remove("hidden");

  const vw = typeof window !== "undefined" ? (window.innerWidth || 1024) : 1024;
  const vh = typeof window !== "undefined" ? (window.innerHeight || 768) : 768;
  const clientX = e && typeof e.clientX === "number" ? e.clientX : vw / 2;
  const clientY = e && typeof e.clientY === "number" ? e.clientY : vh / 2;
  const tipW = tip.offsetWidth || Math.min(280, Math.max(180, vw - 20));
  const tipH = tip.offsetHeight || 220;

  let left = clientX + 14;
  let top = clientY + 14;
  if (left + tipW > vw - 10) left = clientX - tipW - 14;
  if (top + tipH > vh - 10) top = clientY - tipH - 14;
  left = Math.max(10, Math.min(Math.max(10, vw - tipW - 10), left));
  top = Math.max(10, Math.min(Math.max(10, vh - tipH - 10), top));

  tip.style.left = Math.round(left) + "px";
  tip.style.top = Math.round(top) + "px";
}

function hideKuadranDotTooltip() {
  const tip = document.getElementById("kuadranFloatingTooltip");
  if (tip) tip.classList.add("hidden");
}

let kuadranScrollLockActive = false;
let kuadranScrollLockTouchStartY = 0;

function getActiveKuadranModal() {
  const cellModal = document.getElementById("kuadranCellModal");
  if (cellModal && !cellModal.classList.contains("hidden")) return cellModal;
  const zoomModal = document.getElementById("kuadranZoomModal");
  if (zoomModal && !zoomModal.classList.contains("hidden")) return zoomModal;
  return null;
}

function ensureKuadranModalInBody(modal) {
  if (modal && typeof document !== "undefined" && document.body && typeof document.body.appendChild === "function") {
    if (modal.parentElement !== document.body) {
      document.body.appendChild(modal);
    }
  }
  if (modal && modal.style) {
    modal.style.margin = "0";
  }
}

function canElementScrollVertically(el, deltaY) {
  if (!el || typeof el.scrollHeight !== "number" || typeof el.clientHeight !== "number") return false;
  if (el.scrollHeight <= el.clientHeight + 1) return false;
  if (deltaY < 0 && (el.scrollTop || 0) <= 0) return false;
  if (deltaY > 0 && (el.scrollTop || 0) + el.clientHeight >= el.scrollHeight - 1) return false;
  return true;
}

function canTargetScrollInModal(target, deltaY, modal) {
  if (!modal || !target) return false;
  let cur = target;
  while (cur && cur !== (typeof document !== "undefined" ? document.body : null) && cur !== (typeof document !== "undefined" ? document.documentElement : null)) {
    const isScrollableOverflow = cur === modal || (
      typeof window !== "undefined" &&
      typeof window.getComputedStyle === "function" &&
      /(auto|scroll)/.test((window.getComputedStyle(cur) || {}).overflowY || "")
    );
    if (isScrollableOverflow && canElementScrollVertically(cur, deltaY)) {
      return true;
    }
    if (cur === modal) break;
    cur = cur.parentElement;
  }
  return false;
}

function onKuadranModalWheel(e) {
  const modal = getActiveKuadranModal();
  if (!modal) return;
  const dy = e.deltaY || 0;
  const dx = e.deltaX || 0;
  if (Math.abs(dx) > Math.abs(dy)) {
    let cur = e.target;
    while (cur && cur !== (typeof document !== "undefined" ? document.body : null) && cur !== (typeof document !== "undefined" ? document.documentElement : null)) {
      if (typeof cur.scrollWidth === "number" && typeof cur.clientWidth === "number" && cur.scrollWidth > cur.clientWidth + 1) {
        return;
      }
      if (cur === modal) break;
      cur = cur.parentElement;
    }
    if (e.cancelable && typeof e.preventDefault === "function") e.preventDefault();
    return;
  }
  if (dy === 0) return;
  if (!canTargetScrollInModal(e.target, dy, modal)) {
    if (e.cancelable && typeof e.preventDefault === "function") e.preventDefault();
  }
}

function onKuadranModalTouchStart(e) {
  if (e && e.touches && e.touches.length > 0) {
    kuadranScrollLockTouchStartY = e.touches[0].clientY;
  }
}

function onKuadranModalTouchMove(e) {
  const modal = getActiveKuadranModal();
  if (!modal || !e || !e.touches || e.touches.length === 0) return;
  const dy = kuadranScrollLockTouchStartY - e.touches[0].clientY;
  kuadranScrollLockTouchStartY = e.touches[0].clientY;
  if (!canTargetScrollInModal(e.target, dy, modal)) {
    if (e.cancelable && typeof e.preventDefault === "function") e.preventDefault();
  }
}

function onKuadranModalKeyScroll(e) {
  const modal = getActiveKuadranModal();
  if (!modal || !e) return;
  const scrollKeys = ["ArrowUp", "ArrowDown", "PageUp", "PageDown", "Home", "End", " "];
  if (!scrollKeys.includes(e.key)) return;
  const tag = e.target && e.target.tagName ? e.target.tagName.toUpperCase() : "";
  if (tag === "INPUT" || tag === "TEXTAREA" || tag === "SELECT") return;
  const deltaY = (e.key === "ArrowUp" || e.key === "PageUp" || e.key === "Home") ? -100 : 100;
  if (!canTargetScrollInModal(e.target || modal, deltaY, modal)) {
    if (typeof e.preventDefault === "function") e.preventDefault();
  }
}

function syncKuadranModalScrollLock() {
  const shouldLock = !!getActiveKuadranModal();
  if (typeof document === "undefined") return;
  const docEl = document.documentElement;
  const body = document.body;

  if (shouldLock && !kuadranScrollLockActive) {
    kuadranScrollLockActive = true;
    if (docEl && body && body.style && typeof window !== "undefined") {
      const sbWidth = Math.max(0, (window.innerWidth || 0) - (docEl.clientWidth || window.innerWidth || 0));
      if (sbWidth > 0) {
        if (!body.dataset) body.dataset = {};
        body.dataset.prevPaddingRight = body.style.paddingRight || "";
        body.style.paddingRight = sbWidth + "px";
      }
    }
    if (docEl && docEl.classList) docEl.classList.add("kuadran-modal-open");
    if (body && body.classList) body.classList.add("kuadran-modal-open");
    if (docEl && docEl.style) docEl.style.overflow = "hidden";
    if (body && body.style) body.style.overflow = "hidden";

    if (typeof window !== "undefined" && typeof window.addEventListener === "function") {
      window.addEventListener("wheel", onKuadranModalWheel, { passive: false });
      window.addEventListener("touchstart", onKuadranModalTouchStart, { passive: true });
      window.addEventListener("touchmove", onKuadranModalTouchMove, { passive: false });
      window.addEventListener("keydown", onKuadranModalKeyScroll, { passive: false });
    }
  } else if (!shouldLock && kuadranScrollLockActive) {
    kuadranScrollLockActive = false;
    if (docEl && docEl.classList) docEl.classList.remove("kuadran-modal-open");
    if (body && body.classList) body.classList.remove("kuadran-modal-open");
    if (docEl && docEl.style) docEl.style.overflow = "";
    if (body && body.style) {
      body.style.overflow = "";
      if (body.dataset && "prevPaddingRight" in body.dataset) {
        body.style.paddingRight = body.dataset.prevPaddingRight;
        delete body.dataset.prevPaddingRight;
      } else {
        body.style.paddingRight = "";
      }
    }

    if (typeof window !== "undefined" && typeof window.removeEventListener === "function") {
      window.removeEventListener("wheel", onKuadranModalWheel, { passive: false });
      window.removeEventListener("touchstart", onKuadranModalTouchStart, { passive: true });
      window.removeEventListener("touchmove", onKuadranModalTouchMove, { passive: false });
      window.removeEventListener("keydown", onKuadranModalKeyScroll, { passive: false });
    }
  }
}

/**
 * Modal Perbesar 1 Komoditas + Tabel 17 Wilayah
 */
function openKuadranZoomModal(commId) {
  const modal = document.getElementById("kuadranZoomModal");
  const titleEl = document.getElementById("kuadranZoomTitle");
  const bodyEl = document.getElementById("kuadranZoomBody");
  if (!modal || !bodyEl || typeof ALPS_17_DATA === "undefined" || !ALPS_17_DATA.kuadran) return;

  const commObj = (ALPS_17_DATA.kuadran.by_commodity || []).find(c => c.comm_id === commId);
  if (!commObj) return;

  if (titleEl) {
    titleEl.textContent = `Kuadran Persistensi & Deviasi Harga — ${commObj.comm_name} (d̄ = ${kpFmtNum(commObj.d_bar, 1)} hari)`;
  }

  const bigSvg = buildKuadranScatterSvg(commObj, true);
  const sortedPts = [...(commObj.points || [])].sort((a, b) => (b.deviasi_pct - a.deviasi_pct) || (b.durasi_hari - a.durasi_hari));

  const tableRowsHtml = sortedPts.map((p, idx) => {
    const kc = KUADRAN_COLORS[p.kuadran_id] || KUADRAN_COLORS.K4;
    const isPos = p.deviasi_pct > 0;
    return `
      <tr class="border-b border-slate-100 hover:bg-slate-50/70">
        <td class="py-2 px-3 text-[11px] font-bold text-slate-400">${idx + 1}</td>
        <td class="py-2 px-3 text-xs font-extrabold text-slate-900">${p.region_name} <span class="text-[9.5px] font-bold text-slate-400 ml-1">${p.source}</span></td>
        <td class="py-2 px-3 text-xs font-bold text-slate-700 text-right">${p.harga_aktual_str}</td>
        <td class="py-2 px-3 text-xs font-semibold text-slate-500 text-right">${p.harga_wajar_str}</td>
        <td class="py-2 px-3 text-xs font-black text-right ${isPos ? 'text-rose-700' : 'text-sky-700'}">${p.deviasi_pct_str}</td>
        <td class="py-2 px-3 text-xs font-extrabold text-slate-900 text-right">${p.durasi_hari} hari</td>
        <td class="py-2 px-3 text-[11px] text-slate-500">${p.durasi_sejak_tgl}</td>
        <td class="py-2 px-3"><span class="px-2 py-0.5 rounded-full text-[10px] font-black border ${kc.badgeCls}">${kc.roman}: ${kc.short}</span></td>
      </tr>
    `;
  }).join("");

  const naNotice = (commObj.na_regions && commObj.na_regions.length > 0)
    ? `<div class="text-[11px] text-slate-500 bg-slate-50 border border-slate-200 rounded-xl px-3 py-2"><strong>Catatan N/A (${commObj.na_regions.length} wilayah):</strong> Data survei ${commObj.comm_name} belum tersedia resmi untuk ${commObj.na_regions.join(", ")}.</div>`
    : "";

  bodyEl.innerHTML = `
    <div class="rounded-2xl border border-slate-200 p-2.5 sm:p-3 bg-white overflow-x-auto">${bigSvg}</div>
    ${naNotice}
    <div class="overflow-x-auto rounded-2xl border border-slate-200">
      <table class="w-full text-left border-collapse">
        <thead class="bg-slate-100/90 border-b border-slate-200 text-[10.5px] font-black uppercase tracking-wider text-slate-600">
          <tr>
            <th class="py-2.5 px-3">#</th>
            <th class="py-2.5 px-3">Kabupaten / Kota</th>
            <th class="py-2.5 px-3 text-right">Aktual</th>
            <th class="py-2.5 px-3 text-right">MH-WMA</th>
            <th class="py-2.5 px-3 text-right">Deviasi</th>
            <th class="py-2.5 px-3 text-right">Durasi</th>
            <th class="py-2.5 px-3">Sejak Tgl</th>
            <th class="py-2.5 px-3">Kuadran</th>
          </tr>
        </thead>
        <tbody>${tableRowsHtml}</tbody>
      </table>
    </div>
  `;

  ensureKuadranModalInBody(modal);
  modal.classList.remove("hidden");
  modal.scrollTop = 0;
  syncKuadranModalScrollLock();
}

function closeKuadranZoomModal() {
  const modal = document.getElementById("kuadranZoomModal");
  if (modal) modal.classList.add("hidden");
  syncKuadranModalScrollLock();
}

/**
 * Warna Heatmap Distribusi Skala YlOrRd (Persis Gambar 2)
 */
function getHeatmapCellStyle(val, maxVal) {
  if (!val || val <= 0) {
    return { bg: "#fefce8", color: "#475569", weight: "font-bold" };
  }
  if (val === 1) {
    return { bg: "#fde68a", color: "#78350f", weight: "font-extrabold" };
  }
  if (val === 2) {
    return { bg: "#fb923c", color: "#431407", weight: "font-black" };
  }
  if (val === 3) {
    return { bg: "#ea580c", color: "#ffffff", weight: "font-black" };
  }
  // 4 atau lebih -> Dark Burgundy Crimson seperti angka tertinggi pada Gambar 2
  const darkHex = val >= Math.max(4, maxVal) ? "#881337" : "#be123c";
  return { bg: darkHex, color: "#ffffff", weight: "font-black" };
}

/**
 * Render Heatmap Distribusi Kuadran per 17 Kabupaten/Kota
 */
function renderKuadranDistributionHeatmap() {
  const summaryEl = document.getElementById("kuadranDistSummaryBanner");
  const container = document.getElementById("kuadranDistTableContainer");
  if (!container || typeof ALPS_17_DATA === "undefined" || !ALPS_17_DATA.kuadran) return;

  const kData = ALPS_17_DATA.kuadran;

  // 1. Summary Banner dihapus dari UI sesuai permintaan penyederhanaan tampilan
  if (summaryEl) summaryEl.innerHTML = "";

  // 2. Urutkan baris wilayah mengikuti urutan baku 17 Kabupaten/Kota (ALPS_17_DATA.rows)
  const rows = [...(kData.distribution_rows || [])];
  if (Array.isArray(ALPS_17_DATA.rows) && ALPS_17_DATA.rows.length > 0) {
    const regOrder = new Map(
      ALPS_17_DATA.rows.filter(r => r.region_id !== "sultra").map((r, idx) => [r.region_id, idx])
    );
    rows.sort((a, b) => (regOrder.get(a.region_id) ?? 999) - (regOrder.get(b.region_id) ?? 999));
  }

  let globalCellMax = 0;
  rows.forEach(r => {
    globalCellMax = Math.max(globalCellMax, r.k1, r.k2, r.k3, r.k4);
  });

  // 3. Build Heatmap HTML Table
  let html = '<table class="w-full border-collapse text-center">';
  html += '<thead>';
  html += '<tr class="border-b-2 border-slate-200 bg-slate-50 text-[11px] font-black text-slate-800">';
  html += '<th class="py-3 px-2.5 sm:px-3.5 text-left sticky left-0 z-20 bg-slate-100 border-r border-slate-200 min-w-[138px] sm:min-w-[185px]">Kabupaten / Kota</th>';
  html += '<th class="py-3 px-2 min-w-[105px] sm:min-w-[125px] text-rose-900">K I: Harga Tinggi<br><span class="text-[9.5px] font-bold text-rose-700">Persisten (&gt;0%, &ge;d&#772;)</span></th>';
  html += '<th class="py-3 px-2 min-w-[105px] sm:min-w-[125px]">K II: Harga Tinggi<br><span class="text-[9.5px] font-bold text-yellow-700">Sementara (&gt;0%, &lt;d&#772;)</span></th>';
  html += '<th class="py-3 px-2 min-w-[105px] sm:min-w-[125px]">K III: Harga Rendah<br><span class="text-[9.5px] font-bold text-blue-700">Persisten (&le;0%, &ge;d&#772;)</span></th>';
  html += '<th class="py-3 px-2 min-w-[105px] sm:min-w-[125px]">K IV: Harga Rendah<br><span class="text-[9.5px] font-bold text-emerald-700">Sementara (&le;0%, &lt;d&#772;)</span></th>';
  html += '</tr></thead>';

  html += '<tbody class="divide-y divide-white text-xs">';
  rows.forEach((r) => {
    const naTag = r.na > 0 ? `<span class="text-[9px] font-semibold text-slate-400">(${r.total_active}/10)</span>` : "";

    html += '<tr class="group hover:brightness-[0.98] transition">';
    html += `<td class="py-2.5 px-2.5 sm:px-3.5 text-left sticky left-0 z-10 bg-white border-r border-slate-200 whitespace-normal sm:whitespace-nowrap">
      <span class="font-bold text-slate-900 text-xs">${r.region_name} ${naTag}</span>
    </td>`;

    ["K1", "K2", "K3", "K4"].forEach(qid => {
      const cnt = r[qid.toLowerCase()];
      const st = getHeatmapCellStyle(cnt, globalCellMax);
      const kcCell = KUADRAN_COLORS[qid];
      const isKColDim = (kuadranHighlightK !== "all" && kuadranHighlightK !== qid);

      html += `<td
        onclick="selectKuadranHeatmapCell('${r.region_id}', '${qid}')"
        style="background:${st.bg};color:${st.color};${isKColDim ? 'opacity:0.45;' : ''}"
        class="py-2.5 px-2 transition border-l border-white cursor-pointer hover:brightness-95 active:scale-[0.98] select-none ${st.weight}"
        title="${r.region_name} • ${kcCell.roman} (${kcCell.title}): ${cnt} komoditas — Klik untuk melihat komoditas & upaya intervensi"
      >${cnt}</td>`;
    });

    html += '</tr>';
  });
  html += '</tbody>';
  html += '</table>';

  container.innerHTML = html;
}

function getKuadranGpipsIntervention(qid) {
  if (qid === "K1") {
    return {
      tag: "K I • Stabilisasi Pasokan & Harga",
      text: "Strategi yang dapat dilakukan sejalan dengan GPIPS yaitu: Kerjasama Antar-Daerah, Fasilitasi Distribusi Pangan, atau Pasar Murah.",
      boxCls: "bg-rose-50/80 border-rose-200/90",
      titleCls: "text-rose-900",
      badgeCls: "bg-rose-100 text-rose-900 border-rose-300"
    };
  }
  const kc = KUADRAN_COLORS[qid] || KUADRAN_COLORS.K3;
  return {
    tag: `${kc.roman} • Pengendalian Ekspektasi TPID`,
    text: "Strategi yang dapat dilakukan sejalan dengan GPIPS yaitu koordinasi dan komunikasi di tingkat TPID dalam rangka pengendalian ekspektasi masyarakat.",
    boxCls: "bg-slate-50/95 border-slate-200/90",
    titleCls: "text-slate-900",
    badgeCls: kc.badgeCls
  };
}

function selectKuadranHeatmapCell(regionId, qid) {
  kuadranSelectedHeatmapCell = { regionId, qid };
  renderKuadranHeatmapDetail();

  const modal = document.getElementById("kuadranCellModal");
  const badgeEl = document.getElementById("kuadranCellModalBadge");
  const titleEl = document.getElementById("kuadranCellModalTitle");
  const bodyEl = document.getElementById("kuadranCellModalBody");
  if (!modal || !bodyEl || typeof ALPS_17_DATA === "undefined" || !ALPS_17_DATA.kuadran) return;

  const row = (ALPS_17_DATA.kuadran.distribution_rows || []).find(r => r.region_id === regionId);
  const kc = KUADRAN_COLORS[qid] || KUADRAN_COLORS.K1;
  if (!row) return;

  const rawItems = (row.items_by_k && row.items_by_k[qid]) ? [...row.items_by_k[qid]] : [];
  const items = rawItems.sort((a, b) => {
    if (qid === "K1" || qid === "K2") {
      return (b.deviasi_pct - a.deviasi_pct) || (b.durasi_hari - a.durasi_hari);
    }
    return (b.durasi_hari - a.durasi_hari) || (a.deviasi_pct - b.deviasi_pct);
  });

  if (badgeEl) {
    badgeEl.innerHTML = `
      <span class="px-2.5 py-0.5 rounded-full border ${kc.badgeCls}">${kc.roman}: ${kc.title}</span>
      <span class="px-2.5 py-0.5 rounded-full bg-white text-slate-700 border border-slate-200">${items.length} Komoditas</span>
    `;
  }
  if (titleEl) {
    titleEl.textContent = `${row.region_name} — ${kc.roman} (${kc.title})`;
  }

  let commSectionHtml = "";
  if (items.length > 0) {
    const commRowsHtml = items.map((it, idx) => {
      const isPos = Number(it.deviasi_pct) > 0;
      const devCls = isPos ? "text-rose-700" : "text-sky-700";
      return `
        <tr class="border-b border-slate-100 last:border-b-0 hover:bg-slate-50/70">
          <td class="py-2.5 px-3 text-[11px] font-bold text-slate-400">${idx + 1}</td>
          <td class="py-2.5 px-3">
            <div class="font-extrabold text-slate-900 text-xs">${it.comm_name}</div>
            <div class="text-[10px] text-slate-500 font-medium">Satuan: Rp/${it.satuan || "kg"}</div>
          </td>
          <td class="py-2.5 px-3 text-xs font-bold text-slate-800 text-right whitespace-nowrap">${it.harga_aktual_str}</td>
          <td class="py-2.5 px-3 text-xs font-semibold text-slate-500 text-right whitespace-nowrap">${it.harga_wajar_str}</td>
          <td class="py-2.5 px-3 text-xs font-black text-right whitespace-nowrap ${devCls}">${it.deviasi_pct_str}</td>
          <td class="py-2.5 px-3 text-right whitespace-nowrap">
            <div class="text-xs font-extrabold text-slate-900">${it.durasi_hari} hari</div>
            <div class="text-[10px] text-slate-400">Sejak ${it.durasi_sejak_tgl}</div>
          </td>
        </tr>
      `;
    }).join("");

    commSectionHtml = `
      <div class="space-y-2.5">
        <div class="flex flex-wrap items-center justify-between gap-2">
          <h4 class="text-xs font-extrabold text-slate-700 uppercase tracking-wider">
            Daftar Komoditas pada ${kc.roman} (${items.length} Komoditas)
          </h4>
          <span class="text-[11px] font-semibold text-slate-500">${kc.rule}</span>
        </div>
        <div class="overflow-x-auto rounded-2xl border border-slate-200 bg-white">
          <table class="w-full text-left border-collapse">
            <thead class="bg-slate-100/90 border-b border-slate-200 text-[10.5px] font-black uppercase tracking-wider text-slate-600">
              <tr>
                <th class="py-2.5 px-3">#</th>
                <th class="py-2.5 px-3">Komoditas</th>
                <th class="py-2.5 px-3 text-right">Harga Aktual</th>
                <th class="py-2.5 px-3 text-right">Acuan MH-WMA</th>
                <th class="py-2.5 px-3 text-right">Deviasi</th>
                <th class="py-2.5 px-3 text-right">Durasi</th>
              </tr>
            </thead>
            <tbody>${commRowsHtml}</tbody>
          </table>
        </div>
      </div>
    `;
  } else {
    const naNote = (row.na > 0 && row.na_comms && row.na_comms.length > 0)
      ? `<div class="mt-2 text-[11px] text-slate-500">Catatan: ${row.total_active}/10 komoditas aktif terpantau (${row.na} belum tersedia survei: ${row.na_comms.join(", ")}).</div>`
      : "";
    commSectionHtml = `
      <div class="space-y-2.5">
        <div class="flex flex-wrap items-center justify-between gap-2">
          <h4 class="text-xs font-extrabold text-slate-700 uppercase tracking-wider">
            Daftar Komoditas pada ${kc.roman} (0 Komoditas)
          </h4>
          <span class="text-[11px] font-semibold text-slate-500">${kc.rule}</span>
        </div>
        <div class="rounded-2xl border border-slate-200 bg-slate-50/80 p-4 text-center text-xs text-slate-600">
          <div class="font-bold text-slate-800">Tidak ada komoditas di ${row.region_name} yang berada pada ${kc.roman} (${kc.title}) saat ini.</div>
          ${naNote}
        </div>
      </div>
    `;
  }

  const gpips = getKuadranGpipsIntervention(qid);
  const intervensiHtml = `
    <div class="rounded-2xl border p-4 sm:p-5 space-y-2 ${gpips.boxCls}">
      <div class="flex flex-wrap items-center justify-between gap-2">
        <h4 class="text-xs font-extrabold uppercase tracking-wider ${gpips.titleCls}">
          Upaya Intervensi
        </h4>
        <span class="px-2.5 py-0.5 rounded-full text-[10px] font-black border ${gpips.badgeCls}">${gpips.tag}</span>
      </div>
      <div class="flex items-start gap-2.5 text-xs sm:text-sm leading-relaxed text-slate-800 font-semibold pt-0.5">
        <span class="mt-2 w-1.5 h-1.5 rounded-full bg-slate-700 shrink-0"></span>
        <p>${gpips.text}</p>
      </div>
    </div>
  `;

  bodyEl.innerHTML = commSectionHtml + intervensiHtml;
  ensureKuadranModalInBody(modal);
  modal.classList.remove("hidden");
  modal.scrollTop = 0;
  syncKuadranModalScrollLock();
}

function closeKuadranCellModal() {
  const modal = document.getElementById("kuadranCellModal");
  if (modal) modal.classList.add("hidden");
  syncKuadranModalScrollLock();
}

function renderKuadranHeatmapDetail() {
  const detailEl = document.getElementById("kuadranDistCellDetail");
  if (detailEl) detailEl.innerHTML = "";
}

/**
 * Render Utama Tab Kuadran Pangan
 */
function renderKuadranPanganModule() {
  ensureKuadranControls();
  renderKuadranKpiCards();
  renderKuadranChartsGrid();
  renderKuadranDistributionHeatmap();

  if (window.renderMathInElement) {
    try {
      const root = document.getElementById("tabContent_kuadran");
      if (root) {
        renderMathInElement(root, {
          delimiters: [
            { left: "$$", right: "$$", display: true },
            { left: "\\(", right: "\\)", display: false },
            { left: "$", right: "$", display: false }
          ],
          throwOnError: false
        });
      }
    } catch (kErr) {
      console.warn("KaTeX Kuadran notice:", kErr);
    }
  }
}

if (typeof document !== "undefined") {
  document.addEventListener("keydown", function(e) {
    if (e.key === "Escape" || e.key === "Esc") {
      closeKuadranZoomModal();
      closeKuadranCellModal();
      hideKuadranDotTooltip();
    }
  });
}
