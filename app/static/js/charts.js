/* Gráficos operativos. Nadie configura ECharts a mano en las pantallas. */
(function () {
  const PG = (window.PG = window.PG || {});

  function cssVar(name, fallback) {
    const v = getComputedStyle(document.documentElement).getPropertyValue(name);
    return (v && v.trim()) || fallback;
  }

  function fmtNum(v) {
    if (v == null || Number.isNaN(Number(v))) return "—";
    return Number(v).toLocaleString("es-CO", { maximumFractionDigits: 2 });
  }

  function asPair(p) {
    if (Array.isArray(p)) return p;
    return [p.t, p.v];
  }
  function asBand(p) {
    if (Array.isArray(p)) return p;
    return [p.t, p.lo, p.hi];
  }

  function fmtTime(iso) {
    if (!iso) return "";
    const d = new Date(iso);
    return d.toLocaleTimeString("es-CO", {
      hour: "2-digit",
      minute: "2-digit",
      hour12: false,
      timeZone: "America/Bogota",
    });
  }

  function baseOption() {
    const text = cssVar("--text-2", "#5A6472");
    const border = cssVar("--border", "#E3E5E8");
    const accent = cssVar("--chart-expected", cssVar("--accent", "#1C5A8E"));
    return {
      textStyle: { fontFamily: cssVar("--font-ui", "Archivo, sans-serif"), color: text },
      grid: { left: 48, right: 16, top: 24, bottom: 32 },
      tooltip: {
        trigger: "axis",
        formatter: function (params) {
          if (!params || !params.length) return "";
          const t = fmtTime(params[0].axisValue);
          const bits = params
            .filter((p) => p.seriesName !== "rango")
            .map((p) => {
              if (p.seriesName === "esperado") {
                return `A las ${t} se esperan ${fmtNum(p.data)} %`;
              }
              if (p.seriesName === "medido") {
                return `A las ${t} el sensor marca ${fmtNum(p.data)} %`;
              }
              return `${p.seriesName}: ${fmtNum(p.data)}`;
            });
          const band = params.find((p) => p.seriesName === "rango");
          if (band && Array.isArray(band.data)) {
            bits.push(`rango probable ${fmtNum(band.data[0])}–${fmtNum(band.data[1])} %`);
          }
          return bits.join("<br>");
        },
      },
      xAxis: {
        type: "time",
        axisLine: { lineStyle: { color: border } },
        axisLabel: { formatter: function (v) { return fmtTime(v); } },
        splitLine: { show: false },
      },
      yAxis: {
        type: "value",
        axisLabel: { formatter: function (v) { return fmtNum(v); } },
        splitLine: { lineStyle: { type: "dashed", color: border } },
      },
      color: [accent, cssVar("--st-vigilar", "#C98A04")],
    };
  }

  function nowAndNext(el, data) {
    if (!window.echarts || !el) return null;
    const chart = echarts.getInstanceByDom(el) || echarts.init(el, null, { renderer: "svg" });
    const measured = (data.measured || []).map(asPair);
    const expected = (data.expected || []).map(asPair);
    const band = (data.band || []).map(asBand);
    const markLine = {
      symbol: "none",
      lineStyle: { color: cssVar("--text-3", "#8A93A0") },
      data: [{ xAxis: data.now, label: { formatter: "Ahora" } }].concat(
        (data.thresholds || []).map((th) => ({
          yAxis: th.value,
          label: { formatter: th.label, position: "insideEndTop" },
        }))
      ),
    };
    const opt = Object.assign(baseOption(), {
      series: [
        {
          name: "rango",
          type: "line",
          data: band.map((b) => [b[0], b[1]]),
          lineStyle: { opacity: 0 },
          areaStyle: { opacity: 0 },
          stack: "band",
          symbol: "none",
          tooltip: { show: true },
          z: 1,
        },
        {
          name: "rango",
          type: "line",
          data: band.map((b) => [b[0], (b[2] != null && b[1] != null ? b[2] - b[1] : null)]),
          lineStyle: { opacity: 0 },
          areaStyle: { color: cssVar("--accent-soft", "#E8EEF6"), opacity: 0.9 },
          stack: "band",
          symbol: "none",
          z: 1,
        },
        {
          name: "medido",
          type: "line",
          data: measured,
          showSymbol: false,
          lineStyle: { width: 2.2, color: cssVar("--chart-measured", "#1A1E24") },
          markLine: markLine,
          z: 3,
        },
        {
          name: "esperado",
          type: "line",
          data: expected,
          showSymbol: false,
          lineStyle: {
            width: 2,
            type: "dashed",
            color: cssVar("--st-vigilar", "#C98A04"),
          },
          z: 4,
        },
      ],
    });
    chart.setOption(opt, true);
    return chart;
  }

  function history(el, data) {
    if (!window.echarts || !el) return null;
    const chart = echarts.getInstanceByDom(el) || echarts.init(el, null, { renderer: "svg" });
    const measured = (data.measured || []).map(asPair);
    const markArea = (data.alert_windows || []).map((w) => [
      { xAxis: w.start, itemStyle: { color: "rgba(217,96,26,0.12)" } },
      { xAxis: w.end },
    ]);
    const opt = Object.assign(baseOption(), {
      dataZoom: [{ type: "inside" }, { type: "slider", height: 18 }],
      series: [
        {
          name: "medido",
          type: "line",
          data: measured,
          showSymbol: false,
          markArea: { data: markArea, silent: true },
        },
      ],
    });
    chart.setOption(opt, true);
    return chart;
  }

  function reliability(el, data) {
    if (!window.echarts || !el) return null;
    const chart = echarts.getInstanceByDom(el) || echarts.init(el, null, { renderer: "svg" });
    const labels = (data.items || []).map((i) => i.label);
    const values = (data.items || []).map((i) => i.value);
    chart.setOption(
      {
        grid: { left: 120, right: 80, top: 8, bottom: 8 },
        xAxis: { type: "value", show: false },
        yAxis: { type: "category", data: labels, inverse: true, axisLine: { show: false }, axisTick: { show: false } },
        series: [
          {
            type: "bar",
            data: values,
            barWidth: 16,
            itemStyle: { color: cssVar("--accent", "#1E3A5F"), borderRadius: 6 },
            label: { show: true, position: "right", formatter: function (p) { return fmtNum(p.value); } },
          },
        ],
      },
      true
    );
    return chart;
  }

  PG.charts = { nowAndNext, history, reliability };

  function boot(root) {
    (root || document).querySelectorAll("[data-chart]").forEach((el) => {
      const kind = el.getAttribute("data-chart");
      let payload = {};
      const raw = el.getAttribute("data-payload");
      if (raw) {
        try { payload = JSON.parse(raw); } catch (_) { payload = {}; }
      }
      const url = el.getAttribute("data-url");
      const run = function (data) {
        if (kind === "now") PG.charts.nowAndNext(el, data);
        else if (kind === "history") PG.charts.history(el, data);
        else if (kind === "reliability") PG.charts.reliability(el, data);
      };
      if (url) {
        fetch(url, { credentials: "same-origin" })
          .then((r) => r.json())
          .then(run)
          .catch(function () {});
      } else {
        run(payload);
      }
    });
  }

  PG.charts.boot = boot;
  document.addEventListener("DOMContentLoaded", function () { boot(document); });
  window.addEventListener("resize", function () {
    document.querySelectorAll("[data-chart]").forEach((el) => {
      const c = window.echarts && echarts.getInstanceByDom(el);
      if (c) c.resize();
    });
  });
})();
