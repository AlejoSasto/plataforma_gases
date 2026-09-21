/* Utilidades compartidas del front (fetch con cookies, sidebar móvil). */
(function () {
  window.PG = window.PG || {};

  PG.api = async function (url, options) {
    const opts = Object.assign({ credentials: "same-origin" }, options || {});
    opts.headers = Object.assign(
      { Accept: "application/json" },
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
    window.location.href = "/login";
  };

  document.addEventListener("DOMContentLoaded", function () {
    const toggle = document.getElementById("sidebar-toggle");
    const sidebar = document.getElementById("app-sidebar");
    const backdrop = document.getElementById("sidebar-backdrop");
    function close() {
      sidebar && sidebar.classList.remove("is-open");
      backdrop && backdrop.classList.remove("is-visible");
    }
    function open() {
      sidebar && sidebar.classList.add("is-open");
      backdrop && backdrop.classList.add("is-visible");
    }
    if (toggle && sidebar) {
      toggle.addEventListener("click", function () {
        if (sidebar.classList.contains("is-open")) close();
        else open();
      });
    }
    if (backdrop) backdrop.addEventListener("click", close);
  });
})();
