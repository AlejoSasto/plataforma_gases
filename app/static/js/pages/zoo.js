(function () {
  document.querySelectorAll("[data-promote]").forEach((btn) => {
    btn.addEventListener("click", async () => {
      await PG.api(`/api/ml/models/${btn.dataset.promote}/promote`, { method: "POST", body: {} });
      location.reload();
    });
  });
})();
