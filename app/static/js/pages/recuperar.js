(function () {
  const tokenEl = document.getElementById("reset-form");
  const token = tokenEl ? tokenEl.getAttribute("data-token") || "" : "";
  const ask = document.getElementById("ask-form");
  const reset = document.getElementById("reset-form");
  if (ask) {
    ask.addEventListener("submit", async (e) => {
      e.preventDefault();
      await PG.api("/auth/recuperar", { method: "POST", body: { email: document.getElementById("email").value } });
      document.getElementById("msg").textContent = "Si el correo está en el sistema, recibirás un enlace.";
    });
  }
  if (reset) {
    reset.addEventListener("submit", async (e) => {
      e.preventDefault();
      await PG.api("/auth/recuperar/confirmar", {
        method: "POST",
        body: { token, password: document.getElementById("password").value },
      });
      document.getElementById("msg").textContent = "Listo. Ya puedes ingresar.";
      setTimeout(() => {
        location.href = "/ingresar";
      }, 800);
    });
  }
})();
