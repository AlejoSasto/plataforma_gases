(function () {
  const btn = document.getElementById("etl-upload");
  if (!btn) return;
  let stages = {};
  try {
    stages = JSON.parse(btn.getAttribute("data-stages") || "{}");
  } catch (_) {
    stages = {};
  }
  btn.addEventListener("click", async () => {
    const files = document.getElementById("etl-files").files;
    const msg = document.getElementById("etl-msg");
    const prog = document.getElementById("etl-progress");
    if (!files.length) {
      msg.textContent = "Elige al menos un archivo";
      return;
    }
    const fd = new FormData();
    for (const f of files) fd.append("files", f);
    prog.classList.remove("hidden");
    msg.textContent = stages.E1 || "Leyendo archivo…";
    try {
      const res = await fetch("/api/ingestion/upload", {
        method: "POST",
        body: fd,
        credentials: "same-origin",
        headers: { "X-CSRF-Token": PG.csrf() },
      });
      const data = await res.json().catch(() => ({}));
      if (!res.ok) throw new Error(data.message || "No se pudo cargar");
      const rejected = data.rows_rejected || 0;
      msg.textContent = rejected
        ? `${stages.E4 || ""} ${rejected} lecturas con problemas.`
        : `${stages.E5 || ""} ${data.rows_ingested || 0} lecturas.`;
      setTimeout(() => location.reload(), 800);
    } catch (e) {
      msg.textContent = e.message;
    } finally {
      prog.classList.add("hidden");
    }
  });
})();
