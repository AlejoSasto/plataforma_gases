(function () {
  const form = document.getElementById("stake-form");
  if (!form) return;
  let selectedId = null;
  form.addEventListener("submit", async (e) => {
    e.preventDefault();
    const body = {
      name: document.getElementById("name").value,
      type: document.getElementById("type").value,
      organization: document.getElementById("organization").value || null,
      email: document.getElementById("email").value || null,
      phone: document.getElementById("phone").value || null,
      notify_channels: document
        .getElementById("channels")
        .value.split(",")
        .map((s) => s.trim())
        .filter(Boolean),
    };
    const id = document.getElementById("stake-id").value;
    if (id) await PG.api(`/api/stakeholders/${id}`, { method: "PATCH", body });
    else await PG.api("/api/stakeholders", { method: "POST", body });
    location.reload();
  });
  async function loadSubs(id, name) {
    selectedId = id;
    document.getElementById("subs-box").classList.remove("hidden");
    document.getElementById("subs-name").textContent = name;
    const rows = await PG.api(`/api/stakeholders/${id}/subscriptions`);
    const ul = document.getElementById("subs-list");
    ul.innerHTML = rows.length
      ? rows
          .map(
            (s) =>
              `<li>zona ${s.site_id || "todas"} · desde ${s.min_level}
        <button class="btn btn-ghost" data-del="${s.id}" type="button">Quitar</button></li>`
          )
          .join("")
      : "<li>Sin avisos configurados</li>";
    ul.querySelectorAll("[data-del]").forEach((b) =>
      b.addEventListener("click", async () => {
        await PG.api(`/api/subscriptions/${b.dataset.del}`, { method: "DELETE" });
        loadSubs(id, name);
      })
    );
  }
  document.querySelectorAll("tr[data-sid]").forEach((tr) => {
    tr.addEventListener("click", () => {
      document.getElementById("stake-id").value = tr.dataset.sid;
      const tds = tr.children;
      document.getElementById("name").value = tds[0].textContent.trim();
      document.getElementById("type").value = tds[1].textContent.trim();
      document.getElementById("email").value = tds[2].textContent.trim() === "—" ? "" : tds[2].textContent.trim();
      loadSubs(tr.dataset.sid, tds[0].textContent.trim());
    });
  });
  const addSub = document.getElementById("add-sub");
  if (addSub) {
    addSub.addEventListener("click", async () => {
      if (!selectedId) return;
      const site = document.getElementById("sub-site").value;
      await PG.api(`/api/stakeholders/${selectedId}/subscriptions`, {
        method: "POST",
        body: { site_id: site ? Number(site) : null, min_level: document.getElementById("sub-level").value },
      });
      loadSubs(selectedId, document.getElementById("subs-name").textContent);
    });
  }
})();
