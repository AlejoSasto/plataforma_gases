/* Utilidades compartidas del front (fetch con cookies, sidebar, avisos). */
(function () {
  window.PG = window.PG || {};

  PG.csrf = function () {
    const m = document.cookie.match(/(?:^|; )csrf_token=([^;]+)/);
    return m ? decodeURIComponent(m[1]) : "";
  };

  PG.api = async function (url, options) {
    const opts = Object.assign({ credentials: "same-origin" }, options || {});
    opts.headers = Object.assign(
      { Accept: "application/json", "X-CSRF-Token": PG.csrf() },
      opts.headers || {}
    );
    if (opts.body && typeof opts.body === "object" && !(opts.body instanceof FormData)) {
      opts.headers["Content-Type"] = "application/json";
      opts.body = JSON.stringify(opts.body);
    }
    const res = await fetch(url, opts);
    let data = null;
    const ct = res.headers.get("content-type") || "";
    if (ct.includes("application/json")) {
      data = await res.json().catch(() => null);
    }
    if (!res.ok) {
      const err = new Error((data && data.message) || "Error de solicitud");
      err.status = res.status;
      err.data = data;
      throw err;
    }
    return data;
  };

  PG.logout = async function () {
    try {
      await PG.api("/auth/logout", { method: "POST" });
    } catch (_) {
      /* ignore */
    }
    window.location.href = "/ingresar";
  };

  document.addEventListener("DOMContentLoaded", function () {
    const logoutBtn = document.getElementById("logout-btn");
    if (logoutBtn) {
      logoutBtn.addEventListener("click", function () {
        PG.logout();
      });
    }
    document.body.addEventListener("htmx:afterSwap", function () {
      if (window.PG && PG.charts) PG.charts.boot(document);
    });

    const toggle = document.getElementById("sidebar-toggle");
    const sidebar = document.getElementById("app-sidebar");
    function close() {
      sidebar && sidebar.classList.remove("is-open");
    }
    function open() {
      sidebar && sidebar.classList.add("is-open");
    }
    if (toggle && sidebar) {
      toggle.addEventListener("click", function () {
        if (sidebar.classList.contains("is-open")) close();
        else open();
      });
    }

    document.querySelectorAll("[data-ack]").forEach((btn) => {
      btn.addEventListener("click", async () => {
        const id = btn.getAttribute("data-ack");
        await PG.api(`/api/alerts/${id}/acknowledge`, { method: "POST", body: {} });
        location.reload();
      });
    });
    document.querySelectorAll("[data-resolve]").forEach((btn) => {
      btn.addEventListener("click", async () => {
        const id = btn.getAttribute("data-resolve");
        const noteEl = document.getElementById("resolve-note");
        const note = noteEl ? noteEl.value : null;
        await PG.api(`/api/alerts/${id}/resolve`, {
          method: "POST",
          body: { resolution_note: note },
        });
        location.reload();
      });
    });

    document.querySelectorAll("form").forEach((form) => {
      const method = (form.getAttribute("method") || "get").toLowerCase();
      if (method !== "post" && method !== "patch" && method !== "delete") return;
      if (form.querySelector("input[name=csrf_token]")) return;
      const i = document.createElement("input");
      i.type = "hidden";
      i.name = "csrf_token";
      i.value = PG.csrf();
      form.appendChild(i);
    });

    document.body.addEventListener("htmx:configRequest", function (event) {
      event.detail.headers["X-CSRF-Token"] = PG.csrf();
    });

    if (document.documentElement.getAttribute("data-theme") !== "sala") {
      let last = Date.now();
      const ping = () => {
        last = Date.now();
      };
      ["click", "keydown", "mousemove"].forEach((ev) =>
        document.addEventListener(ev, ping, { passive: true })
      );
      setInterval(async () => {
        if (Date.now() - last <= 30 * 60 * 1000) return;
        last = Date.now();
        const stay = window.confirm("¿Sigues ahí? Si no respondes, cerraremos la sesión.");
        if (!stay) {
          await PG.logout();
          return;
        }
        const t = setTimeout(() => PG.logout(), 60000);
        const keep = () => {
          clearTimeout(t);
          document.removeEventListener("click", keep);
        };
        document.addEventListener("click", keep);
      }, 30000);
    }
  });
})();
