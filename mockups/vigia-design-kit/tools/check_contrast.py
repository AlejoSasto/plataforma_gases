"""Verifica contraste WCAG 2.2 de los pares de color del sistema. Uso: python tools/check_contrast.py"""
import re, sys
from pathlib import Path
css = (Path(__file__).resolve().parents[1] / "mockups/assets/css/tokens.css").read_text()
def block(sel):
    m = re.search(re.escape(sel) + r"\s*\{(.*?)\n\}", css, re.S); return dict(re.findall(r"(--[\w-]+):\s*(#[0-9A-Fa-f]{6})", m.group(1)))
def lum(h):
    c = [int(h[i:i+2], 16) / 255 for i in (1, 3, 5)]
    c = [x / 12.92 if x <= 0.03928 else ((x + 0.055) / 1.055) ** 2.4 for x in c]
    return 0.2126 * c[0] + 0.7152 * c[1] + 0.0722 * c[2]
def ratio(a, b):
    la, lb = sorted([lum(a), lum(b)], reverse=True); return (la + 0.05) / (lb + 0.05)
light = block(":root"); light.update({"--bg": "#EEF0EF", "--surface": "#FFFFFF", "--text": "#1A1E24", "--text-2": "#4A525E", "--text-3": "#5F6772", "--accent": "#1C5A8E"})
dark = {**light, **block('[data-theme="sala"]')}
pairs = []
for name, t in (("claro", light), ("sala", dark)):
    for st in ("normal", "vigilar", "actuar", "evacuar", "sindatos"):
        pairs.append((name, f"{st}: texto sobre fondo suave", t[f"--st-{st}-ink"], t[f"--st-{st}-soft"], 4.5))
        pairs.append((name, f"{st}: marca sobre superficie (gráfico)", t[f"--st-{st}"], t["--surface"], 3.0))
    for k in ("--text", "--text-2", "--text-3"):
        pairs.append((name, f"{k} sobre superficie", t[k], t["--surface"], 4.5))
        pairs.append((name, f"{k} sobre fondo", t[k], t["--bg"], 4.5))
    pairs.append((name, "botón principal", t.get("--accent-text", "#FFFFFF"), t["--accent"], 4.5))
pairs.append(("claro", "evacuar: texto blanco sobre sólido", "#FFFFFF", light["--st-evacuar"], 4.5))
fail = 0
for mode, label, fg, bg, need in pairs:
    r = ratio(fg, bg); ok = r >= need; fail += not ok
    print(f"{'OK ' if ok else 'NO '} [{mode}] {label:44s} {fg} / {bg}  {r:5.2f}:1 (mín {need})")
sys.exit(1 if fail else 0)
