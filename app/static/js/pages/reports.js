(function () {
  const form = document.getElementById("report-form");
  if (!form) return;
  const today = new Date().toISOString().slice(0, 10);
  const monthAgo = new Date(Date.now() - 30 * 864e5).toISOString().slice(0, 10);
  const start = document.getElementById("start");
  const end = document.getElementById("end");
  if (end) end.value = today;
  if (start) start.value = monthAgo;
  const rtype = document.getElementById("rtype");
  const periodFields = document.getElementById("period-fields");
  const xlsxBtn = document.getElementById("report-xlsx");

  function syncType() {
    const needsPeriod = rtype.value !== "confiabilidad";
    periodFields.classList.toggle("hidden", !needsPeriod);
    document.getElementById("start").required = needsPeriod;
    document.getElementById("end").required = needsPeriod;
    if (xlsxBtn) xlsxBtn.classList.toggle("hidden", rtype.value !== "ejecutivo");
  }
  rtype.addEventListener("change", syncType);
  syncType();

  async function generate(formato) {
    const msg = document.getElementById("report-msg");
    msg.textContent = "Preparando el informe…";
    let url;
    let body = {};
    if (rtype.value === "alertas") {
      url = "/api/reports/alertas";
      body = { start: start.value, end: end.value };
    } else if (rtype.value === "ejecutivo") {
      url = "/api/reports/ejecutivo";
      body = { start: start.value, end: end.value, formato: formato || "pdf" };
    } else {
      url = "/api/reports/confiabilidad";
    }
    const data = await PG.api(url, { method: "POST", body });
    const dl = data.report && data.report.download_url;
    msg.textContent = "Listo. Descargando…";
    if (dl) window.location.href = dl;
    else location.reload();
  }

  form.addEventListener("submit", async (event) => {
    event.preventDefault();
    const msg = document.getElementById("report-msg");
    try {
      await generate("pdf");
    } catch (err) {
      msg.textContent = err.message || "No se pudo generar";
    }
  });
  if (xlsxBtn) {
    xlsxBtn.addEventListener("click", async () => {
      const msg = document.getElementById("report-msg");
      try {
        await generate("xlsx");
      } catch (err) {
        msg.textContent = err.message || "No se pudo generar";
      }
    });
  }
})();
