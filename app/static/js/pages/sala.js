(function () {
  const cards = Array.from(document.querySelectorAll("#sala-zones .card, #sala-zones a.card"));
  let i = 0;
  if (cards.length > 4) {
    setInterval(() => {
      cards.forEach((c, idx) => {
        c.style.outline = idx === i ? "2px solid var(--accent)" : "none";
      });
      i = (i + 1) % cards.length;
    }, 20000);
  }
  let soundOn = false;
  const btn = document.getElementById("sound-toggle");
  if (btn) {
    btn.addEventListener("click", () => {
      soundOn = !soundOn;
      btn.textContent = soundOn ? "Sonido activo" : "Sonido para Evacuar (opcional)";
    });
  }
  const hasEvac = btn && btn.getAttribute("data-sala-evacuar") === "true";
  if (hasEvac) {
    setInterval(() => {
      if (!soundOn) return;
      const ctx = new (window.AudioContext || window.webkitAudioContext)();
      const o = ctx.createOscillator();
      o.frequency.value = 880;
      o.connect(ctx.destination);
      o.start();
      setTimeout(() => {
        o.stop();
        ctx.close();
      }, 180);
    }, 4000);
  }
})();
