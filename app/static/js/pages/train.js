(function () {
  const form = document.getElementById("train-form");
  if (!form) return;
  form.addEventListener("submit", async (e) => {
    e.preventDefault();
    const algos = Array.from(document.querySelectorAll(".algo:checked")).map((x) => x.value);
    const msg = document.getElementById("train-msg");
    msg.textContent = "Encolando…";
    try {
      await PG.api("/api/ml/train", {
        method: "POST",
        body: {
          dataset_version: document.getElementById("dataset_version").value,
          scope: document.getElementById("scope").value,
          task: document.getElementById("task").value,
          algorithms: algos,
        },
      });
      window.location.href = "/laboratorio";
    } catch (err) {
      msg.textContent = err.message || "No se pudo entrenar";
    }
  });
})();
