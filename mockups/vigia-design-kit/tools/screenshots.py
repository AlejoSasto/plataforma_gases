"""Captura PNG de cada mockup (escritorio y móvil). Requiere: pip install playwright && playwright install chromium"""
import sys, asyncio
from pathlib import Path
from playwright.async_api import async_playwright
BASE = sys.argv[1] if len(sys.argv) > 1 else "http://localhost:8765"
OUT = Path(__file__).resolve().parents[1] / "screenshots"
SHOTS = [
    ("01-ingresar", "ingresar.html", 1440, 900, False),
    ("02-hoy", "hoy.html", 1440, 1180, True),
    ("03-avisos", "avisos.html", 1440, 900, False),
    ("04-aviso-detalle", "aviso.html", 1440, 1120, True),
    ("05-confiabilidad", "confiabilidad.html", 1440, 1000, True),
    ("06-sala-de-control", "sala.html", 1920, 1080, False),
    ("07-equipo", "equipo.html", 1440, 900, False),
    ("08-laboratorio", "laboratorio.html", 1440, 1000, True),
    ("09-componentes", "componentes.html", 1440, 1100, True),
    ("10-hoy-movil", "hoy.html", 390, 844, True),
    ("11-ingresar-movil", "ingresar.html", 390, 844, True),
    ("00-hoja-de-marca", "marca.html", 1376, 900, True),
]
async def main():
    OUT.mkdir(exist_ok=True)
    async with async_playwright() as p:
        b = await p.chromium.launch(executable_path="/usr/bin/google-chrome") if Path("/usr/bin/google-chrome").exists() else await p.chromium.launch()
        for name, url, w, h, full in SHOTS:
            pg = await b.new_page(viewport={"width": w, "height": h}, device_scale_factor=2 if w < 500 else 1)
            await pg.goto(f"{BASE}/{url}"); await pg.wait_for_timeout(700)
            await pg.screenshot(path=str(OUT / f"{name}.png"), full_page=full)
            await pg.close(); print("ok", name)
        await b.close()
asyncio.run(main())
