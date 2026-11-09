(function () {
  var panel = document.getElementById("ask-panel");
  if (!panel) return;
  var log = document.getElementById("ask-log");
  var form = document.getElementById("ask-form");
  var input = document.getElementById("ask-input");
  var send = document.getElementById("ask-send");
  var opener = null;
  var history = [];
  var welcome = "Pregúntame por los gases, los avisos o cómo usar Vigía.";

  function csrf() {
    var match = document.cookie.match(/(?:^|; )csrf_token=([^;]+)/);
    return match ? decodeURIComponent(match[1]) : "";
  }

  function openPanel(from) {
    opener = from || document.activeElement;
    panel.hidden = false;
    input.focus();
  }

  function closePanel() {
    panel.hidden = true;
    if (opener && opener.focus) opener.focus();
  }

  document.querySelectorAll("[data-ask-open]").forEach(function (btn) {
    btn.addEventListener("click", function () { openPanel(btn); });
  });
  panel.querySelector("[data-ask-close]").addEventListener("click", closePanel);

  function addText(role, text) {
    var node = document.createElement("div");
    node.className = "ask__bubble" + (role === "user" ? " ask__bubble--user" : "");
    node.textContent = text;
    log.appendChild(node);
    log.scrollTop = log.scrollHeight;
    return node;
  }

  function addBlocks(blocks) {
    (blocks || []).forEach(function (block) {
      var node = document.createElement("div");
      node.className = "ask__bubble";
      if (block.type === "chart") {
        var chart = document.createElement("div");
        chart.className = "ask__block";
        chart.setAttribute("data-chart", "assistant");
        chart.setAttribute("data-url", block.data_url);
        node.appendChild(chart);
        if (window.PG && PG.charts && PG.charts.initCharts) PG.charts.initCharts(node);
      } else if (block.type === "table") {
        var table = document.createElement("table");
        var head = document.createElement("tr");
        (block.columns || []).forEach(function (col) {
          var th = document.createElement("th");
          th.textContent = col;
          head.appendChild(th);
        });
        table.appendChild(head);
        (block.rows || []).forEach(function (row) {
          var tr = document.createElement("tr");
          row.forEach(function (cell) {
            var td = document.createElement("td");
            td.textContent = cell == null ? "" : String(cell);
            tr.appendChild(td);
          });
          table.appendChild(tr);
        });
        node.appendChild(table);
      } else if (block.type === "report") {
        var link = document.createElement("a");
        link.className = "btn";
        link.href = block.download_url;
        link.textContent = block.title || "Descargar informe";
        node.appendChild(link);
      } else if (block.type === "link" || block.type === "manual") {
        var a = document.createElement("a");
        a.href = block.url;
        a.textContent = block.title || "Abrir";
        node.appendChild(a);
      }
      log.appendChild(node);
    });
  }

  function addSources(sources, turnId) {
    if (!sources || !sources.length) return;
    var details = document.createElement("details");
    details.className = "ask__sources";
    var summary = document.createElement("summary");
    summary.textContent = "De dónde sale esta respuesta";
    details.appendChild(summary);
    sources.forEach(function (source) {
      var line = document.createElement("p");
      line.textContent = source.tool + " · " + source.rows + " filas";
      details.appendChild(line);
    });
    var bar = document.createElement("p");
    var yes = document.createElement("button");
    yes.type = "button";
    yes.className = "btn";
    yes.textContent = "Sí";
    var no = document.createElement("button");
    no.type = "button";
    no.className = "btn";
    no.textContent = "No";
    bar.appendChild(document.createTextNode("¿Te sirvió? "));
    bar.appendChild(yes);
    bar.appendChild(no);
    function vote(util) {
      fetch("/api/asistente/" + turnId + "/valoracion", {
        method: "POST",
        credentials: "same-origin",
        headers: { "Content-Type": "application/json", "X-CSRF-Token": csrf() },
        body: JSON.stringify({ util: util })
      });
      bar.textContent = "Gracias.";
    }
    yes.addEventListener("click", function () { vote(true); });
    no.addEventListener("click", function () { vote(false); });
    details.appendChild(bar);
    log.appendChild(details);
  }

  fetch("/api/asistente/sugerencias", { credentials: "same-origin" })
    .then(function (res) { return res.ok ? res.json() : null; })
    .then(function (data) {
      if (!data) return;
      welcome = data.welcome || welcome;
      addText("assistant", welcome);
      (data.items || []).forEach(function (item) {
        var btn = document.createElement("button");
        btn.type = "button";
        btn.className = "btn";
        btn.textContent = item;
        btn.addEventListener("click", function () {
          input.value = item;
          form.requestSubmit();
        });
        log.appendChild(btn);
      });
    })
    .catch(function () {
      addText("assistant", "El asistente no está disponible sin conexión. Puedes usar los filtros de cada pantalla.");
    });

  form.addEventListener("submit", function (event) {
    event.preventDefault();
    var text = input.value.trim();
    if (!text) return;
    addText("user", text);
    history.push({ role: "user", content: text });
    if (history.length > 24) history = history.slice(-24);
    input.value = "";
    send.disabled = true;
    var pending = addText("assistant", "Consultando datos…");
    fetch("/api/asistente", {
      method: "POST",
      credentials: "same-origin",
      headers: { "Content-Type": "application/json", "X-CSRF-Token": csrf() },
      body: JSON.stringify({ messages: history.slice(-20) })
    })
      .then(function (res) {
        return res.json().then(function (body) { return { ok: res.ok, body: body }; });
      })
      .then(function (result) {
        pending.remove();
        if (!result.ok) {
          addText("assistant", (result.body && result.body.error) || "No pude completar la consulta. Intenta de nuevo.");
          history.pop();
          return;
        }
        addText("assistant", result.body.reply || "");
        addBlocks(result.body.blocks);
        addSources(result.body.sources, result.body.turn_id);
        history.push({ role: "assistant", content: result.body.reply || "" });
      })
      .catch(function () {
        pending.remove();
        addText("assistant", "El asistente no está disponible sin conexión. Puedes usar los filtros de cada pantalla.");
        history.pop();
      })
      .finally(function () { send.disabled = false; input.focus(); });
  });
})();
