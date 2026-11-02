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
  const modelField = document.getElementById("model-field");
  const modelPick = document.getElementById("model_pick");
  if (modelPick) {
    modelPick.addEventListener("change", () => {
      if (modelPick.value) document.getElementById("model_id").value = modelPick.value;
    });
  }
  function syncType() {
    const isModel = rtype.value === "modelo";
    periodFields.classList.toggle("hidden", isModel);
    modelField.classList.toggle("hidden", !isModel);
    document.getElementById("start").required = !isModel;
    document.getElementById("end").required = !isModel;
  }
  rtype.addEventListener("change", syncType);
  syncType();
  form.addEventListener("submit", async (e) => {
    e.preventDefault();
    const msg = document.getElementById("report-msg");
    msg.textContent = "Preparando el informe…";
    try {
      let url, body;
      if (rtype.value === "alertas") {
        url = "/api/reports/alertas";
        body = { start: document.getElementById("start").value, end: document.getElementById("end").value };
      } else if (rtype.value === "ejecutivo") {
        url = "/api/reports/ejecutivo";
        body = { start: document.getElementById("start").value, end: document.getElementById("end").value };
      } else {
        const id = document.getElementById("model_id").value;
        if (!id) throw new Error("Elige un registro del laboratorio");
        url = `/api/reports/modelo/${id}`;
        body = {};
      }
      const data = await PG.api(url, { method: "POST", body });
      const dl = data.report && data.report.download_url;
      msg.textContent = "Listo. Descargando…";
      if (dl) window.location.href = dl;
      else location.reload();
    } catch (err) {
      msg.textContent = err.message || "No se pudo generar";
    }
  });
})();
