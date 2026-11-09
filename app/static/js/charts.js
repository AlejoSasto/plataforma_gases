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

  function dispose(el) {
    if (!window.echarts || !el) return;
    const prev = echarts.getInstanceByDom(el);
    if (prev) prev.dispose();
  }

  function showMessage(el, text, retryUrl) {
    dispose(el);
    el.classList.add("chart--empty");
    el.innerHTML = "";
    const box = document.createElement("div");
    box.className = "chart-empty";
    box.setAttribute("role", "status");
    const p = document.createElement("p");
    p.textContent = text || "Este sensor no tiene lecturas en este periodo";
    box.appendChild(p);
    if (retryUrl) {
      const btn = document.createElement("button");
      btn.type = "button";
      btn.className = "btn btn--ghost";
      btn.textContent = "Reintentar";
      btn.addEventListener("click", function () {
        el.removeAttribute("data-booted");
        initCharts(el.parentElement || document);
      });
      box.appendChild(btn);
    }
    el.appendChild(box);
  }

  function clearMessage(el) {
    el.classList.remove("chart--empty");
    if (el.querySelector(".chart-empty")) {
      el.innerHTML = "";
    }
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
    clearMessage(el);
    const measured = (data.measured || []).map(asPair);
    const expected = (data.expected || []).map(asPair);
    if (!measured.length && !expected.length) {
      showMessage(el, data.empty_message || "Este sensor no tiene lecturas en este periodo");
      return null;
    }
    dispose(el);
    const chart = echarts.init(el, null, { renderer: "svg" });
    const band = (data.band || []).map(asBand);
    const markLine = {
      symbol: "none",
      lineStyle: { color: cssVar("--text-3", "#8A93A0") },
      data: [{ xAxis: data.now || data.reference_time, label: { formatter: "Ahora" } }].concat(
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
    clearMessage(el);
    const measured = (data.measured || data.points || []).map(function (p) {
      if (Array.isArray(p)) return p;
      if (p.t != null) return [p.t, p.v != null ? p.v : p.leyendo];
      return p;
    });
    if (!measured.length) {
      showMessage(el, data.empty_message || "Este sensor no tiene lecturas en este periodo");
      return null;
    }
    dispose(el);
    const chart = echarts.init(el, null, { renderer: "svg" });
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
          lineStyle: { width: 2.2, color: cssVar("--chart-measured", "#1A1E24") },
          markArea: { data: markArea, silent: true },
        },
      ],
    });
    chart.setOption(opt, true);
    return chart;
  }

  function reliability(el, data) {
    if (!window.echarts || !el) return null;
    clearMessage(el);
    const items = data.items || data.trend || [];
    if (!items.length) {
      showMessage(el, data.empty_message || "Aún no hay cifras de anticipación para graficar");
      return null;
    }
    dispose(el);
    const chart = echarts.init(el, null, { renderer: "svg" });
    const labels = items.map((i) => i.label);
    const values = items.map((i) => i.value);
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
            itemStyle: { color: cssVar("--accent", "#1C5A8E"), borderRadius: 6 },
            label: { show: true, position: "right", formatter: function (p) { return fmtNum(p.value); } },
          },
        ],
      },
      true
    );
    return chart;
  }

  function assistant(el, data) {
    if (!data) return null;
    if (data.kind === "serie") return history(el, data);
    if (data.kind === "confiabilidad") {
      return reliability(el, { items: data.items || [], empty_message: data.empty_message });
    }
    const categories = data.categories || [];
    const values = data.values || [];
    if (!categories.length) {
      showMessage(el, data.empty_message || "No hay datos para este gráfico");
      return null;
    }
    dispose(el);
    const chart = echarts.init(el, null, { renderer: "svg" });
    chart.setOption(Object.assign(baseOption(), {
      xAxis: { type: "category", data: categories, axisLabel: { color: cssVar("--chart-axis", "#5C6770") } },
      yAxis: { type: "value", axisLabel: { color: cssVar("--chart-axis", "#5C6770") }, splitLine: { lineStyle: { color: cssVar("--chart-grid", "#E6E1D8") } } },
      series: [{
        type: "bar",
        data: values,
        itemStyle: { color: cssVar("--accent", "#1E3A5F") },
      }],
    }), true);
    return chart;
  }

  PG.charts = { nowAndNext, history, reliability, assistant, dispose };

  function runKind(el, kind, data) {
    if (kind === "now") return PG.charts.nowAndNext(el, data);
    if (kind === "history") return PG.charts.history(el, data);
    if (kind === "reliability") return PG.charts.reliability(el, data);
    if (kind === "assistant") return PG.charts.assistant(el, data);
    return null;
  }

  function initCharts(root) {
    const scope = root && root.querySelectorAll ? root : document;
    const nodes = scope.querySelectorAll
      ? scope.querySelectorAll("[data-chart]")
      : [];
    nodes.forEach((el) => {
      const kind = el.getAttribute("data-chart");
      let payload = {};
      const raw = el.getAttribute("data-payload");
      if (raw) {
        try {
          payload = JSON.parse(raw);
        } catch (_) {
          payload = {};
        }
      }
      const url = el.getAttribute("data-url");
      if (url) {
        fetch(url, { credentials: "same-origin" })
          .then((r) => {
            if (!r.ok) throw new Error("http " + r.status);
            return r.json();
          })
          .then((data) => runKind(el, kind, data))
          .catch(function () {
            showMessage(el, "No pudimos cargar el gráfico. Intenta de nuevo", url);
          });
      } else {
        runKind(el, kind, payload);
      }
    });
  }

  PG.charts.initCharts = initCharts;
  PG.charts.boot = initCharts;

  document.addEventListener("DOMContentLoaded", function () {
    initCharts(document);
  });
  document.body &&
    document.body.addEventListener("htmx:afterSwap", function (e) {
      initCharts(e.detail && e.detail.target ? e.detail.target : document);
    });
  document.addEventListener("htmx:beforeSwap", function (e) {
    const target = e.detail && e.detail.target;
    if (!target || !target.querySelectorAll) return;
    target.querySelectorAll("[data-chart]").forEach(dispose);
  });
  window.addEventListener("resize", function () {
    document.querySelectorAll("[data-chart]").forEach((el) => {
      const c = window.echarts && echarts.getInstanceByDom(el);
      if (c) c.resize();
    });
  });
  if (window.ResizeObserver) {
    const ro = new ResizeObserver(function (entries) {
      entries.forEach(function (entry) {
        const c = window.echarts && echarts.getInstanceByDom(entry.target);
        if (c) c.resize();
      });
    });
    document.addEventListener("DOMContentLoaded", function () {
      document.querySelectorAll("[data-chart]").forEach(function (el) {
        ro.observe(el);
      });
    });
  }
})();
