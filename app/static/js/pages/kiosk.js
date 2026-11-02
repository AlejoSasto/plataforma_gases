(function () {
  const form = document.getElementById("kiosk-form");
  if (!form) return;
  form.addEventListener("submit", async (e) => {
    e.preventDefault();
    const siteIds = Array.from(document.getElementById("k-sites").selectedOptions).map((o) => Number(o.value));
    const res = await PG.api("/auth/kioscos", {
      method: "POST",
      body: { name: document.getElementById("k-name").value, site_ids: siteIds },
    });
    document.getElementById("k-msg").textContent = "Abre este enlace en la pantalla: " + res.pair_url;
  });
  document.querySelectorAll("[data-rev]").forEach((btn) =>
    btn.addEventListener("click", async () => {
      await PG.api(`/auth/kioscos/${btn.getAttribute("data-rev")}/revocar`, { method: "POST", body: {} });
      location.reload();
    })
  );
})();
