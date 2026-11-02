"""Exporta PNG de marca (isotipo, logo, imagen para compartir). Uso: python tools/export_brand.py http://localhost:8765"""
import sys, asyncio
from pathlib import Path
from playwright.async_api import async_playwright
BASE = sys.argv[1] if len(sys.argv) > 1 else "http://localhost:8765"
OUT = Path(__file__).resolve().parents[1] / "brand"
PAGES = {
 "isotipo-512": (512, 512, '<img src="assets/img/isotipo.svg" style="width:512px;height:512px;display:block">', "transparent"),
 "logo-horizontal-oscuro": (900, 260, '<div style="display:flex;align-items:center;gap:28px;padding:40px 56px;background:#1A1E24;height:260px;box-sizing:border-box"><img src="assets/img/isotipo.svg" style="width:150px"><div><div style="font:700 104px/1 Archivo;font-stretch:86%;color:#fff">Vigía</div><div style="font:400 26px Archivo;color:#9AA4B1;margin-top:10px">Gases en la mina</div></div></div>', "#1A1E24"),
 "logo-horizontal-claro": (900, 260, '<div style="display:flex;align-items:center;gap:28px;padding:40px 56px;background:#fff;height:260px;box-sizing:border-box"><img src="assets/img/isotipo.svg" style="width:150px"><div><div style="font:700 104px/1 Archivo;font-stretch:86%;color:#1A1E24">Vigía</div><div style="font:400 26px Archivo;color:#4A525E;margin-top:10px">Gases en la mina</div></div></div>', "#fff"),
 "imagen-compartir-1200x630": (1200, 630, '<div style="position:relative;width:1200px;height:630px;overflow:hidden;background:#13171C"><img src="assets/img/login-hero.svg" style="position:absolute;inset:0;width:100%;height:100%;object-fit:cover;object-position:center 30%"><div style="position:absolute;inset:0;background:linear-gradient(90deg,rgba(19,23,28,.96) 0,rgba(19,23,28,.85) 42%,rgba(19,23,28,0) 75%)"></div><div style="position:absolute;left:64px;bottom:64px;color:#fff"><div style="display:flex;gap:16px;align-items:center"><img src="assets/img/isotipo.svg" style="width:64px"><span style="font:700 44px Archivo;font-stretch:86%">Vigía</span></div><div style="font:650 58px/1.08 Archivo;font-stretch:84%;max-width:15ch;margin-top:28px">Saber a tiempo qué pasa con los gases en la mina</div></div></div>', "#13171C"),
}
async def main():
    OUT.mkdir(exist_ok=True)
    async with async_playwright() as p:
        b = await p.chromium.launch(executable_path="/usr/bin/google-chrome") if Path("/usr/bin/google-chrome").exists() else await p.chromium.launch()
        for name, (w, h, html, bg) in PAGES.items():
            pg = await b.new_page(viewport={"width": w, "height": h}, device_scale_factor=2 if w < 1000 else 1)
            await pg.goto(f"{BASE}/marca.html")
            await pg.evaluate("""([html, bg]) => { document.body.style.margin='0'; document.body.style.background=bg; document.body.innerHTML = html; }""", [html, bg])
            await pg.wait_for_timeout(400)
            await pg.screenshot(path=str(OUT / f"{name}.png"), omit_background=(bg == "transparent"))
            await pg.close(); print("ok", name)
        await b.close()
asyncio.run(main())
