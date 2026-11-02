"""Regenera assets/icons/sprite.svg desde los SVG de Lucide en assets/icons/. Uso: python tools/build_sprite.py"""
import re
from pathlib import Path
d = Path(__file__).resolve().parents[1] / "mockups/assets/icons"
out = ['<svg xmlns="http://www.w3.org/2000/svg" style="display:none">']
for f in sorted(d.glob("*.svg")):
    if f.name == "sprite.svg": continue
    inner = re.search(r"<svg[^>]*>(.*)</svg>", f.read_text(), re.S).group(1).strip()
    out.append(f'<symbol id="i-{f.stem}" viewBox="0 0 24 24">{inner}</symbol>')
out.append("</svg>")
(d / "sprite.svg").write_text("\n".join(out)); print(len(out) - 2, "íconos")
