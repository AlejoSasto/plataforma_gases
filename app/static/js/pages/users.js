(function () {
  const invite = document.getElementById("invite-form");
  if (!invite) return;
  const roleForm = document.getElementById("role-form");
  const zoneForm = document.getElementById("zone-form");
  invite.addEventListener("submit", async (e) => {
    e.preventDefault();
    const roleIds = Array.from(document.getElementById("inv-roles").selectedOptions).map((o) => Number(o.value));
    const siteIds = Array.from(document.getElementById("inv-sites").selectedOptions).map((o) => Number(o.value));
    const res = await PG.api("/auth/invitar", {
      method: "POST",
      body: {
        full_name: document.getElementById("inv-name").value,
        email: document.getElementById("inv-email").value,
        role_ids: roleIds,
        site_ids: siteIds,
      },
    });
    document.getElementById("inv-msg").textContent =
      "Invitación enviada. Si no hay correo, el enlace quedó en el buzón local.";
    if (res.token) document.getElementById("inv-msg").textContent += " Enlace: /invitar?token=" + res.token;
  });
  document.querySelectorAll("[data-role]").forEach((btn) =>
    btn.addEventListener("click", () => {
      document.getElementById("role-uid").value = btn.getAttribute("data-role");
      roleForm.classList.remove("hidden");
      zoneForm.classList.add("hidden");
    })
  );
  document.querySelectorAll("[data-zones]").forEach((btn) =>
    btn.addEventListener("click", () => {
      document.getElementById("zone-uid").value = btn.getAttribute("data-zones");
      zoneForm.classList.remove("hidden");
      roleForm.classList.add("hidden");
    })
  );
  roleForm.addEventListener("submit", async (e) => {
    e.preventDefault();
    const ids = Array.from(document.getElementById("role-ids").selectedOptions).map((o) => Number(o.value));
    await PG.api(`/api/users/${document.getElementById("role-uid").value}/roles`, {
      method: "POST",
      body: { role_ids: ids },
    });
    location.reload();
  });
  zoneForm.addEventListener("submit", async (e) => {
    e.preventDefault();
    const ids = Array.from(document.getElementById("zone-ids").selectedOptions).map((o) => Number(o.value));
    await PG.api(`/api/users/${document.getElementById("zone-uid").value}/zonas`, {
      method: "POST",
      body: { site_ids: ids },
    });
    location.reload();
  });
  document.querySelectorAll("[data-unlock]").forEach((btn) =>
    btn.addEventListener("click", async () => {
      await PG.api(`/api/users/${btn.getAttribute("data-unlock")}/desbloquear`, { method: "POST", body: {} });
      location.reload();
    })
  );
  document.querySelectorAll("[data-force]").forEach((btn) =>
    btn.addEventListener("click", async () => {
      await PG.api(`/api/users/${btn.getAttribute("data-force")}/forzar-contrasena`, { method: "POST", body: {} });
      location.reload();
    })
  );
  document.querySelectorAll("[data-off]").forEach((btn) =>
    btn.addEventListener("click", async () => {
      await PG.api(`/api/users/${btn.getAttribute("data-off")}`, { method: "DELETE" });
      location.reload();
    })
  );
})();
