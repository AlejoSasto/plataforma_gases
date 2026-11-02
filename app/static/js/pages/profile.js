(function () {
  const logoutBtn = document.getElementById("logout-btn");
  if (logoutBtn) {
    logoutBtn.addEventListener("click", function () {
      PG.logout();
    });
  }
  const ul = document.getElementById("sessions");
  if (!ul) return;
  async function loadSessions() {
    const data = await PG.api("/auth/sesiones");
    ul.innerHTML = "";
    (data.items || []).forEach((s) => {
      if (s.revoked) return;
      const li = document.createElement("li");
      li.textContent =
        (s.user_agent || "Dispositivo") + " · " + (s.ip || "IP no disponible") + " · " + (s.last_used_at || "");
      const b = document.createElement("button");
      b.className = "btn btn-ghost";
      b.type = "button";
      b.textContent = "Cerrar esta sesión";
      b.addEventListener("click", async () => {
        await PG.api(`/auth/sesiones/${s.id}/cerrar`, { method: "POST", body: {} });
        loadSessions();
      });
      li.appendChild(b);
      ul.appendChild(li);
    });
  }
  loadSessions().catch(() => {});
  const start = document.getElementById("totp-start");
  let secret = "";
  if (start) {
    start.addEventListener("click", async () => {
      const data = await PG.api("/auth/totp/iniciar", { method: "POST", body: {} });
      secret = data.secret;
      document.getElementById("totp-uri").textContent = "Añade esta cuenta en tu aplicación: " + data.uri;
      document.getElementById("totp-box").classList.remove("hidden");
    });
    document.getElementById("totp-ok").addEventListener("click", async () => {
      try {
        const data = await PG.api("/auth/totp/activar", {
          method: "POST",
          body: { secret, code: document.getElementById("totp-code").value },
        });
        document.getElementById("backup-codes").textContent = (data.backup_codes || []).join("\n");
        document.getElementById("backup-box").classList.remove("hidden");
        document.getElementById("totp-msg").textContent = "Listo. Guarda estos códigos.";
      } catch (err) {
        document.getElementById("totp-msg").textContent = (err.data && err.data.message) || "Ese código no coincide.";
      }
    });
  }
  const closeAll = document.getElementById("close-all");
  if (closeAll) {
    closeAll.addEventListener("click", async () => {
      await PG.api("/auth/sesiones/cerrar-todas", { method: "POST", body: {} });
      window.location.href = "/ingresar";
    });
  }
})();
