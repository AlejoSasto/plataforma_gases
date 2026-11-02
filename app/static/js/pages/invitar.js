(function () {
  const form = document.getElementById("inv-form");
  if (!form) return;
  const token = form.getAttribute("data-token") || "";
  form.addEventListener("submit", async (e) => {
    e.preventDefault();
    try {
      await PG.api("/auth/invitar/aceptar", {
        method: "POST",
        body: { token, password: document.getElementById("password").value },
      });
      window.location.href = "/";
    } catch (err) {
      document.getElementById("msg").textContent = (err.data && err.data.message) || "El enlace ya no es válido.";
    }
  });
})();
