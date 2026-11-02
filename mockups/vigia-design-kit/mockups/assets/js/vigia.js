/* =====================================================================
   VIGÍA — JS de los mockups
   - Datos de ejemplo (FICTICIOS, solo para el diseño)
   - Corte esquemático de la mina (componente distintivo)
   - Gráfico "Ahora y lo que viene" (ECharts)
   - Minigráficos de tendencia
   En la app: app/static/js/charts.js + app/static/js/mine-map.js
   ===================================================================== */
(function () {
  "use strict";

  /* ---------- Utilidades ---------- */
  const css = (name) => getComputedStyle(document.documentElement).getPropertyValue(name).trim()
    || getComputedStyle(document.body).getPropertyValue(name).trim();
  const nf = (v, d = 2) => new Intl.NumberFormat("es-CO", { minimumFractionDigits: d, maximumFractionDigits: d }).format(v);
  const hhmm = (d) => d.toLocaleTimeString("es-CO", { hour: "2-digit", minute: "2-digit", hour12: false });
  const STATE = {
    normal:   { word: "Normal",    icon: "circle-check" },
    vigilar:  { word: "Vigilar",   icon: "eye" },
    actuar:   { word: "Actuar ya", icon: "triangle-alert" },
    evacuar:  { word: "Evacuar",   icon: "siren" },
    sindatos: { word: "Sin datos", icon: "circle-dashed" },
  };
  const stColor = (s) => css(`--st-${s}`);

  /* ---------- Datos de ejemplo ---------- */
  const NOW = new Date(2026, 10, 1, 10, 35, 0);
  const ZONES = [
    { id: "bocamina", name: "Bocamina",          state: "normal",   x: 80,  y: 46,  label: "CH₄ 0,02 %",  anchor: "start", dx: 18, dy: -14 },
    { id: "principal", name: "Galería principal", state: "normal",   x: 262, y: 150, label: "CH₄ 0,18 %",  anchor: "start", dx: 16, dy: -16 },
    { id: "f2n", name: "Frente 2 Norte",         state: "normal",   x: 118, y: 150, label: "CH₄ 0,21 %",  anchor: "middle", dx: 0, dy: 34 },
    { id: "f1n", name: "Frente 1 Norte",         state: "vigilar",  x: 802, y: 150, label: "CO 28 ppm",   anchor: "end", dx: -18, dy: -16 },
    { id: "f4s", name: "Frente 4 Sur",           state: "sindatos", x: 118, y: 272, label: "Sin señal hace 14 min", anchor: "middle", dx: 0, dy: 36 },
    { id: "f3s", name: "Frente 3 Sur",           state: "actuar",   x: 802, y: 272, label: "CH₄ 0,72 % y subiendo", anchor: "end", dx: -18, dy: -16 },
  ];

  function seededNoise(seed) { let s = seed; return () => { s = (s * 9301 + 49297) % 233280; return s / 233280 - 0.5; }; }

  function methaneSeries() {
    const r = seededNoise(7), measured = [];
    for (let i = 60; i >= 0; i--) {
      const t = new Date(NOW.getTime() - i * 60000);
      const k = (60 - i) / 60;
      const base = 0.36 + 0.06 * Math.sin(k * 5) + (k > 0.55 ? Math.pow((k - 0.55) / 0.45, 1.6) * 0.3 : 0);
      measured.push([t, +(base + r() * 0.03).toFixed(3)]);
    }
    measured[measured.length - 1][1] = 0.72;
    const last = 0.72, exp = [], lo = [], hi = [];
    for (let m = 0; m <= 10; m++) {
      const t = new Date(NOW.getTime() + m * 60000);
      const q50 = last + (1.05 - last) * (m / 10) + 0.02 * Math.sin(m);
      const w = 0.025 * m;
      exp.push([t, +q50.toFixed(3)]); lo.push([t, +(q50 - w * 1.0).toFixed(3)]); hi.push([t, +(q50 + w * 1.4).toFixed(3)]);
    }
    return { measured, exp, lo, hi };
  }

  /* ---------- Íconos ---------- */
  const SPRITE = document.currentScript ? document.currentScript.src.replace(/js\/vigia\.js.*$/, "icons/sprite.svg") : "assets/icons/sprite.svg";
  const icon = (name, cls = "ico") => `<svg class="${cls}" aria-hidden="true"><use href="${SPRITE}#i-${name}"></use></svg>`;
  window.VG_icon = icon;
  function hydrateIcons(root = document) {
    root.querySelectorAll("[data-icon]").forEach((el) => {
      const st = el.getAttribute("style"); el.outerHTML = icon(el.dataset.icon, el.getAttribute("class") || "ico").replace("<svg ", st ? `<svg style="${st}" ` : "<svg ");
    });
  }

  /* ---------- Corte esquemático de la mina ---------- */
  function renderMine(el) {
    const surface = css("--surface"), sunk = css("--surface-sunk"), text3 = css("--text-3");
    const seam = document.documentElement.dataset.theme === "sala" || document.body.dataset.theme === "sala" ? "#05070A" : "#2A2F36";
    const gallery = css("--border-strong");
    const W = 900, H = 340;
    const nodes = ZONES.map((z) => {
      const c = stColor(z.state);
      const isAlert = z.state === "actuar" || z.state === "evacuar";
      const dashed = z.state === "sindatos" ? 'stroke-dasharray="4 4"' : "";
      return `
        <g class="mine-node" tabindex="0" role="button" aria-label="${z.name}: ${STATE[z.state].word}. ${z.label}">
          ${isAlert ? `<circle class="pulse" cx="${z.x}" cy="${z.y}" r="13" fill="${c}"/>` : ""}
          <circle cx="${z.x}" cy="${z.y}" r="13" fill="${surface}" stroke="${c}" stroke-width="4" ${dashed}/>
          <circle cx="${z.x}" cy="${z.y}" r="${z.state === "sindatos" ? 0 : 5.5}" fill="${c}"/>
          <text class="node-label" x="${z.x + z.dx}" y="${z.y + z.dy}" text-anchor="${z.anchor}">${z.name}</text>
          <text class="${z.state === "sindatos" ? "node-sub" : "node-read"}" x="${z.x + z.dx}" y="${z.y + z.dy + 17}" text-anchor="${z.anchor}">${z.label}</text>
        </g>`;
    }).join("");
    el.innerHTML = `
      <svg viewBox="0 0 ${W} ${H}" role="img" aria-labelledby="mine-title">
        <title id="mine-title">Corte esquemático de la mina con el estado de cada zona</title>
        <defs>
          <pattern id="hatch" width="8" height="8" patternUnits="userSpaceOnUse" patternTransform="rotate(45)">
            <line x1="0" y1="0" x2="0" y2="8" stroke="${gallery}" stroke-width="1.2"/></pattern>
        </defs>
        <!-- superficie -->
        <rect x="0" y="34" width="${W}" height="12" fill="url(#hatch)"/>
        <line x1="0" y1="46" x2="${W}" y2="46" stroke="${gallery}" stroke-width="1.5"/>
        <text x="${W - 8}" y="26" text-anchor="end" class="node-sub" fill="${text3}">Superficie</text>
        <!-- mantos de carbón -->
        <rect x="0" y="133" width="${W}" height="34" fill="${seam}" opacity=".12"/>
        <rect x="0" y="255" width="${W}" height="34" fill="${seam}" opacity=".12"/>
        <text x="8" y="128" class="node-sub" fill="${text3}">Manto 1</text>
        <text x="8" y="250" class="node-sub" fill="${text3}">Manto 2</text>
        <!-- galerías -->
        <g fill="none" stroke="${sunk}" stroke-width="16" stroke-linecap="round" stroke-linejoin="round">
          <path d="M80 46 L262 150 L440 272"/><path d="M118 150 H802"/><path d="M118 272 H802"/>
        </g>
        <g fill="none" stroke="${gallery}" stroke-width="2" stroke-linecap="round" stroke-dasharray="1 7">
          <path d="M80 46 L262 150 L440 272"/><path d="M118 150 H802"/><path d="M118 272 H802"/>
        </g>
        <!-- aire fresco -->
        <g stroke="${css("--accent")}" stroke-width="2.2" fill="none" stroke-linecap="round" opacity=".8">
          <path d="M150 86 l12 7 l-13 3"/><path d="M340 203 l12 8 l-14 2"/>
          <path d="M470 150 l10 0 m-6 -5 l6 5 l-6 5"/><path d="M560 272 l10 0 m-6 -5 l6 5 l-6 5"/>
        </g>
        ${nodes}
      </svg>`;
  }

  /* ---------- Lista de zonas (versión móvil del corte de la mina) ---------- */
  function renderZoneList(el) {
    const order = { evacuar: 0, actuar: 1, vigilar: 2, sindatos: 3, normal: 4 };
    el.innerHTML = ZONES.slice().sort((a, b) => order[a.state] - order[b.state]).map((z) => `
      <li class="zone-row"><div><strong>${z.name}</strong><span>${z.label}</span></div>
      <span class="status status--${z.state}">${icon(STATE[z.state].icon)}${STATE[z.state].word}</span></li>`).join("");
  }

  /* ---------- Gráfico "Ahora y lo que viene" ---------- */
  function chartNowNext(el, opts = {}) {
    if (!window.echarts) return;
    const s = methaneSeries();
    const ch = echarts.init(el, null, { renderer: "svg" });
    const text2 = css("--text-2"), text3 = css("--text-3"), grid = css("--chart-grid");
    const thresholds = [
      { v: 0.5, name: "Vigilar", st: "vigilar" },
      { v: 1.0, name: "Actuar ya", st: "actuar" },
      { v: 1.5, name: "Evacuar", st: "evacuar" },
    ];
    const font = { fontFamily: "Archivo, system-ui", fontSize: opts.big ? 15 : 12.5 };
    ch.setOption({
      animation: false,
      textStyle: font,
      grid: { left: 52, right: 120, top: 24, bottom: 36 },
      tooltip: {
        trigger: "axis", backgroundColor: css("--surface"), borderColor: css("--border"), textStyle: { color: css("--text"), ...font },
        formatter: (p) => {
          const t = hhmm(new Date(p[0].value[0]));
          const m = p.find((x) => x.seriesName === "Medido");
          const e = p.find((x) => x.seriesName === "Esperado");
          if (m) return `A las ${t} el sensor marcó <b>${nf(m.value[1])} %</b> de metano`;
          if (e) {
            const i = s.exp.findIndex((d) => +d[0] === +new Date(e.value[0]));
            return `A las ${t} se espera alrededor de <b>${nf(e.value[1])} %</b><br>Podría estar entre ${nf(s.lo[i][1])} % y ${nf(s.hi[i][1])} %`;
          }
          return t;
        },
      },
      xAxis: {
        type: "time", min: s.measured[0][0], max: s.exp[s.exp.length - 1][0],
        axisLine: { lineStyle: { color: grid } }, axisTick: { show: false },
        axisLabel: { color: text3, formatter: (v) => hhmm(new Date(v)), hideOverlap: true, ...font }, splitLine: { show: false },
      },
      yAxis: {
        type: "value", min: 0, max: 1.7, interval: 0.5,
        axisLabel: { color: text3, formatter: (v) => `${nf(v, 1)} %`, ...font },
        splitLine: { lineStyle: { color: grid, type: [3, 4] } },
      },
      series: [
        { name: "banda-base", type: "line", data: s.lo, stack: "banda", symbol: "none", lineStyle: { opacity: 0 }, silent: true, tooltip: { show: false } },
        { name: "Rango probable", type: "line", data: s.hi.map((d, i) => [d[0], +(d[1] - s.lo[i][1]).toFixed(3)]), stack: "banda", symbol: "none",
          lineStyle: { opacity: 0 }, areaStyle: { color: css("--chart-band") }, silent: true, tooltip: { show: false } },
        { name: "Medido", type: "line", data: s.measured, symbol: "none", lineStyle: { color: css("--chart-measured"), width: opts.big ? 3 : 2.2 },
          markLine: {
            symbol: "none", silent: true,
            data: [
              ...thresholds.map((t) => ({ yAxis: t.v, lineStyle: { color: stColor(t.st), width: 1.5, type: "solid" },
                label: { formatter: `${t.name}  ${nf(t.v, 1)} %`, position: "end", color: stColor(t.st), fontWeight: 600, ...font, distance: 8 } })),
              { xAxis: +NOW, lineStyle: { color: text2, type: [4, 4], width: 1.2 }, label: { formatter: "Ahora", position: "end", color: text2, ...font } },
            ],
          } },
        { name: "Esperado", type: "line", data: s.exp, symbol: "circle", symbolSize: (v, p) => (p.dataIndex === s.exp.length - 1 ? 9 : 0),
          itemStyle: { color: css("--chart-expected") }, lineStyle: { color: css("--chart-expected"), width: opts.big ? 3 : 2.4, type: [6, 5] },
          markPoint: opts.noPoint ? undefined : { symbol: "none", data: [{ coord: s.exp[7], value: "Llega al límite hacia las 10:42", label: { formatter: "{c}", color: css("--st-actuar-ink"), fontWeight: 600, offset: [-70, -18], ...font } }] } },
      ],
    });
    new ResizeObserver(() => ch.resize()).observe(el);
    return ch;
  }

  /* ---------- Minigráfico ---------- */
  function sparkline(el) {
    const vals = el.dataset.values.split(",").map(Number);
    const st = el.dataset.state || "normal";
    const w = 96, h = 28, min = Math.min(...vals), max = Math.max(...vals), span = max - min || 1;
    const pts = vals.map((v, i) => `${(i / (vals.length - 1)) * (w - 4) + 2},${h - 3 - ((v - min) / span) * (h - 6)}`).join(" ");
    const c = st === "normal" ? css("--text-2") : stColor(st);
    const last = pts.split(" ").pop().split(",");
    el.innerHTML = `<svg class="spark" viewBox="0 0 ${w} ${h}" aria-hidden="true"><polyline points="${pts}" fill="none" stroke="${c}" stroke-width="2" stroke-linejoin="round" stroke-linecap="round"/><circle cx="${last[0]}" cy="${last[1]}" r="3" fill="${c}"/></svg>`;
  }

  /* ---------- Gráficos simples (confiabilidad / laboratorio) ---------- */
  function chartMonthly(el) {
    if (!window.echarts) return;
    const ch = echarts.init(el, null, { renderer: "svg" });
    const font = { fontFamily: "Archivo, system-ui", fontSize: 12.5 };
    const months = ["Jun", "Jul", "Ago", "Sep", "Oct", "Nov"];
    const ok = [7, 8, 8, 9, 9, 9];
    ch.setOption({
      animation: false, textStyle: font, grid: { left: 8, right: 8, top: 24, bottom: 28, containLabel: true },
      xAxis: { type: "category", data: months, axisTick: { show: false }, axisLine: { lineStyle: { color: css("--chart-grid") } }, axisLabel: { color: css("--text-3"), ...font } },
      yAxis: { type: "value", min: 0, max: 10, interval: 5, axisLabel: { color: css("--text-3"), ...font }, splitLine: { lineStyle: { color: css("--chart-grid"), type: [3, 4] } } },
      series: [{ type: "bar", data: ok, barWidth: 26, itemStyle: { color: css("--accent"), borderRadius: [4, 4, 0, 0] },
        label: { show: true, position: "top", color: css("--text"), fontWeight: 600, formatter: "{c} de 10", ...font } }],
      tooltip: { trigger: "axis", formatter: (p) => `${p[0].name}: avisó a tiempo ${p[0].value} de cada 10 situaciones` },
    });
    new ResizeObserver(() => ch.resize()).observe(el);
  }

  function chartLab(el) {
    if (!window.echarts) return;
    const ch = echarts.init(el, null, { renderer: "svg" });
    const font = { fontFamily: "IBM Plex Mono, monospace", fontSize: 12 };
    const models = ["persistencia", "ets", "lgbm_q", "lstm", "patchtst", "itransformer", "chronos2", "timesfm", "ttm", "tft"];
    const mase = [1.0, 0.97, 0.84, 0.86, 0.79, 0.81, 0.77, 0.8, 0.82, 0.74];
    ch.setOption({
      animation: false, textStyle: font, grid: { left: 8, right: 40, top: 8, bottom: 8, containLabel: true },
      xAxis: { type: "value", min: 0, max: 1.1, axisLabel: { color: css("--text-3"), ...font }, splitLine: { lineStyle: { color: css("--chart-grid"), type: [3, 4] } } },
      yAxis: { type: "category", data: models, inverse: true, axisTick: { show: false }, axisLabel: { color: css("--text-2"), ...font } },
      series: [{ type: "bar", data: mase.map((v, i) => ({ value: v, itemStyle: { color: i === 9 ? css("--accent") : i === 0 ? css("--text-3") : css("--border-strong"), borderRadius: [0, 3, 3, 0] } })),
        barWidth: 14, label: { show: true, position: "right", color: css("--text"), ...font, formatter: (p) => nf(p.value, 2) },
        markLine: { symbol: "none", data: [{ xAxis: 1, label: { formatter: "Igual a persistencia", position: "insideEndTop", color: css("--text-3"), ...font }, lineStyle: { color: css("--text-3"), type: [4, 4] } }] } }],
    });
    new ResizeObserver(() => ch.resize()).observe(el);
  }

  /* ---------- "De cada 10" con cascos ---------- */
  function ofTen(el) {
    const n = +el.dataset.ofTen;
    const helmet = (off) => `<svg viewBox="0 0 28 24" class="${off ? "off" : ""}" aria-hidden="true"><path d="M4 17a10 10 0 0 1 20 0z" fill="currentColor"/><rect x="1" y="17" width="26" height="4" rx="2" fill="currentColor"/><circle cx="14" cy="10.5" r="2.6" fill="var(--surface)"/></svg>`;
    el.innerHTML = Array.from({ length: 10 }, (_, i) => helmet(i >= n)).join("");
  }

  /* ---------- Reloj de sala ---------- */
  function clock(el) { el.textContent = hhmm(NOW); }

  /* ---------- Arranque ---------- */
  function boot() {
    hydrateIcons();
    document.querySelectorAll("[data-mine]").forEach(renderMine);
    document.querySelectorAll("[data-zone-list]").forEach(renderZoneList);
    document.querySelectorAll("[data-chart='now-next']").forEach((el) => chartNowNext(el, { big: el.dataset.big === "1", noPoint: el.dataset.nopoint === "1" }));
    document.querySelectorAll("[data-chart='monthly']").forEach(chartMonthly);
    document.querySelectorAll("[data-chart='lab']").forEach(chartLab);
    document.querySelectorAll("[data-spark]").forEach(sparkline);
    document.querySelectorAll("[data-clock]").forEach(clock);
    document.querySelectorAll("[data-of-ten]").forEach(ofTen);
    document.querySelectorAll(".field__pw button").forEach((b) => b.addEventListener("click", () => {
      const i = b.parentElement.querySelector("input"); const show = i.type === "password";
      i.type = show ? "text" : "password"; b.textContent = show ? "Ocultar" : "Mostrar";
    }));
    document.body.classList.add("is-ready");
  }
  if (document.readyState === "loading") document.addEventListener("DOMContentLoaded", boot); else boot();
})();
