/* Login: mostrar clave y TOTP. El envío nativo POST /ingresar no depende de este archivo. */
(function () {
  const form = document.getElementById("login-form");
  if (!form) return;
  const toggle = document.getElementById("toggle-pass");
  if (toggle) {
    toggle.addEventListener("click", () => {
      const el = document.getElementById("password");
      el.type = el.type === "password" ? "text" : "password";
    });
  }
})();
