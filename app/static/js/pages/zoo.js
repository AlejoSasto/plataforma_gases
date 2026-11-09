(function () {
  document.querySelectorAll("[data-report]").forEach((btn) => {
    btn.addEventListener("click", async () => {
      const data = await PG.api(`/api/reports/modelo/${btn.dataset.report}`, { method: "POST", body: {} });
      const dl = data.report && data.report.download_url;
      if (dl) window.location.href = dl;
    });
  });
  document.querySelectorAll("[data-promote]").forEach((btn) => {
    btn.addEventListener("click", async () => {
      await PG.api(`/api/ml/models/${btn.dataset.promote}/promote`, { method: "POST", body: {} });
      location.reload();
    });
  });
})();
