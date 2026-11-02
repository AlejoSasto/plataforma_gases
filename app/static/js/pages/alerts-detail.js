(function () {
  const dlg = document.getElementById("resolve-dialog");
  const openBtn = document.getElementById("open-resolve");
  const cancel = document.getElementById("cancel-resolve");
  if (openBtn && dlg) openBtn.addEventListener("click", () => dlg.showModal());
  if (cancel && dlg) cancel.addEventListener("click", () => dlg.close());
})();
