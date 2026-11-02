"""Genera los mockups HTML estáticos de Vigía a partir de un shell común.

Uso:  python tools/build_mockups.py   (desde la raíz del kit)
Salida: mockups/*.html  — cada página es la referencia visual de un template Jinja2.
"""
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "mockups"

HEAD = """<!doctype html>
<html lang="es-CO"{theme}>
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>{title} | Vigía</title>
<link rel="icon" href="assets/img/favicon.svg" type="image/svg+xml">
<link rel="stylesheet" href="assets/css/tokens.css">
<link rel="stylesheet" href="assets/css/app.css">
</head>
<body{body_theme}>
"""
FOOT = """
<script src="assets/js/echarts.min.js"></script>
<script src="assets/js/vigia.js"></script>
</body>
</html>
"""

NAV = [
    ("Operación", [
        ("hoy", "Hoy", "house", None),
        ("avisos", "Avisos", "bell", "2"),
        ("zonas", "Zonas y sensores", "map-pinned", None),
        ("historial", "Historial", "history", None),
    ]),
    ("Seguimiento", [
        ("informes", "Informes", "file-text", None),
        ("confiabilidad", "Confiabilidad", "gauge", None),
    ]),
    ("Administración", [
        ("equipo", "Equipo", "users", None),
        ("limites", "Límites de seguridad", "sliders-horizontal", None),
        ("cargar", "Cargar datos", "upload", None),
        ("laboratorio", "Laboratorio", "flask-conical", "tech"),
    ]),
]


def rail(active: str, user=("AR", "Ana Rojas", "Supervisora de seguridad")) -> str:
    groups = []
    for title, items in NAV:
        links = []
        for key, label, ico, extra in items:
            cur = ' aria-current="page"' if key == active else ""
            href = f"{key}.html" if key in PAGES else "#"
            tail = ""
            if extra == "tech":
                tail = '<span class="rail__tech">Técnico</span>'
            elif extra:
                tail = f'<span class="rail__count" aria-label="{extra} avisos abiertos">{extra}</span>'
            links.append(f'<a class="rail__link" href="{href}"{cur}><i data-icon="{ico}"></i>{label}{tail}</a>')
        groups.append(f'<div class="rail__group"><div class="rail__group-title">{title}</div>{"".join(links)}</div>')
    ini, name, role = user
    return f"""
<nav class="rail" aria-label="Navegación principal">
  <a class="rail__brand" href="hoy.html"><img src="assets/img/isotipo.svg" alt=""><div><strong>Vigía</strong><span>Gases en la mina</span></div></a>
  <div class="rail__strata" aria-hidden="true"></div>
  {''.join(groups)}
  <div class="rail__foot"><div class="avatar">{ini}</div><div class="rail__who"><strong>{name}</strong><span>{role}</span></div></div>
</nav>"""


TOPBAR = """
<header class="topbar">
  <div class="topbar__site"><i data-icon="map-pinned" class="ico ico-sm"></i>Mina caso de estudio, Cundinamarca</div>
  <div class="topbar__live"><span class="dot-live" aria-hidden="true"></span>Datos al día, última lectura hace 40 s</div>
  <div class="topbar__spacer"></div>
  <button class="icon-btn" aria-label="Buscar"><i data-icon="search"></i></button>
  <button class="icon-btn" aria-label="2 avisos abiertos"><i data-icon="bell"></i><span class="badge-dot"></span></button>
  <button class="icon-btn" aria-label="Salir"><i data-icon="log-out"></i></button>
</header>"""

MOBILE_NAV = """
<nav class="mobile-nav" aria-label="Navegación">
  <a href="hoy.html"{a1}><i data-icon="house"></i>Hoy</a>
  <a href="avisos.html"{a2}><i data-icon="bell"></i>Avisos</a>
  <a href="#"><i data-icon="map-pinned"></i>Zonas</a>
  <a href="#"><i data-icon="users"></i>Más</a>
</nav>"""


def app_page(key, title, content, user=None):
    r = rail(key, user) if user else rail(key)
    mn = MOBILE_NAV.format(a1=' aria-current="page"' if key == "hoy" else "", a2=' aria-current="page"' if key in ("avisos", "aviso") else "")
    return HEAD.format(title=title, theme="", body_theme="") + f"""<div class="app">{r}
<div class="main">{TOPBAR}
<main class="content" id="contenido">
{content}
</main></div></div>{mn}""" + FOOT


# ----------------------------------------------------------------- páginas
def p_ingresar():
    return HEAD.format(title="Ingresar", theme="", body_theme="") + """
<main class="login">
  <section class="login__art" aria-label="Vigía">
    <img class="hero" src="assets/img/login-hero.svg" alt="">
    <div class="login__brand"><img src="assets/img/isotipo.svg" alt=""><strong>Vigía</strong></div>
    <p class="login__claim">Saber a tiempo qué está pasando con los gases en la mina.</p>
    <div class="login__status"><span class="dot-live" aria-hidden="true"></span>El sistema está funcionando y recibe datos</div>
  </section>
  <section class="login__form">
    <form class="login__box" onsubmit="return false">
      <div>
        <h1>Ingresar</h1>
        <p class="muted" style="margin-top:6px">Usa el correo con el que te invitaron.</p>
      </div>
      <div class="form-error" role="alert"><i data-icon="info" class="ico"></i><span>El correo o la contraseña no coinciden. Revisa e intenta de nuevo.</span></div>
      <div class="field"><label for="correo">Correo</label><input class="input" id="correo" type="email" autocomplete="username" value="ana.rojas@mina.co"></div>
      <div class="field"><label for="clave">Contraseña</label>
        <div class="field__pw"><input class="input" id="clave" type="password" autocomplete="current-password" value="contraseña segura"><button type="button" class="btn btn--quiet">Mostrar</button></div>
      </div>
      <label class="check"><input type="checkbox" checked> Mantener la sesión durante mi turno</label>
      <button class="btn btn--primary btn--lg btn--block" type="submit">Ingresar</button>
      <a href="#" style="justify-self:center">¿Olvidaste tu contraseña?</a>
      <p class="micro" style="text-align:center">Si necesitas acceso, pídeselo al administrador de la plataforma.</p>
    </form>
  </section>
</main>""" + FOOT


def p_hoy():
    gas_rows = """
      <tr class="is-hot"><td class="gas-name"><strong>Metano</strong><span>Frente 3 Sur</span></td>
        <td class="reading-cell">0,72<small>%</small></td><td class="reading-cell">1,05<small>%</small></td>
        <td class="hide-sm"><div data-spark data-state="actuar" data-values="0.38,0.4,0.37,0.42,0.45,0.5,0.56,0.63,0.68,0.72"></div></td>
        <td><span class="status status--actuar"><i data-icon="triangle-alert"></i>Actuar ya</span></td></tr>
      <tr><td class="gas-name"><strong>Monóxido de carbono</strong><span>Frente 3 Sur</span></td>
        <td class="reading-cell">11<small>ppm</small></td><td class="reading-cell">14<small>ppm</small></td>
        <td class="hide-sm"><div data-spark data-values="9,10,9,10,11,10,11,12,11,11"></div></td>
        <td><span class="status status--normal"><i data-icon="circle-check"></i>Normal</span></td></tr>
      <tr><td class="gas-name"><strong>Oxígeno</strong><span>Frente 3 Sur</span></td>
        <td class="reading-cell">20,6<small>%</small></td><td class="reading-cell">20,5<small>%</small></td>
        <td class="hide-sm"><div data-spark data-values="20.8,20.8,20.7,20.7,20.7,20.6,20.6,20.6,20.6,20.6"></div></td>
        <td><span class="status status--normal"><i data-icon="circle-check"></i>Normal</span></td></tr>
      <tr><td class="gas-name"><strong>Ácido sulfhídrico</strong><span>Frente 3 Sur</span></td>
        <td class="reading-cell">0,4<small>ppm</small></td><td class="reading-cell">0,4<small>ppm</small></td>
        <td class="hide-sm"><div data-spark data-values="0.3,0.4,0.4,0.3,0.4,0.4,0.4,0.5,0.4,0.4"></div></td>
        <td><span class="status status--normal"><i data-icon="circle-check"></i>Normal</span></td></tr>"""
    content = f"""
<section class="state-line" aria-live="polite">
  <div class="state-line__icon"><i data-icon="triangle-alert"></i></div>
  <div>
    <h1>Dos zonas necesitan atención</h1>
    <p>En el Frente 3 Sur el metano podría llegar al límite en unos 7 minutos. El resto de la mina está normal.</p>
  </div>
  <div class="state-line__meta"><strong>10:35</strong>Domingo 1 de noviembre</div>
</section>

<div class="home-grid">
  <div class="stack">
    <section class="panel" aria-labelledby="t-mapa">
      <div class="panel__head"><h2 id="t-mapa">La mina ahora</h2><span class="faint">Toca una zona para ver sus gases</span></div>
      <div class="mine" data-mine></div>
      <ul class="zone-list" data-zone-list aria-label="Zonas ordenadas por prioridad"></ul>
      <div class="mine-legend">
        <span><i style="background:var(--st-normal)"></i>Normal</span>
        <span><i style="background:var(--st-vigilar)"></i>Vigilar</span>
        <span><i style="background:var(--st-actuar)"></i>Actuar ya</span>
        <span><i style="background:var(--st-evacuar)"></i>Evacuar</span>
        <span><i style="background:transparent;border:2px dashed var(--st-sindatos)"></i>Sin datos</span>
        <span style="margin-left:auto"><i data-icon="wind" class="ico ico-sm" style="color:var(--accent)"></i>Entrada de aire fresco</span>
      </div>
    </section>

    <section class="panel" aria-labelledby="t-f3">
      <div class="panel__head"><h2 id="t-f3">Frente 3 Sur: ahora y en los próximos 10 minutos</h2>
        <span class="status status--actuar"><i data-icon="triangle-alert"></i>Actuar ya</span></div>
      <div class="chart" data-chart="now-next" style="height:300px"></div>
      <div class="chart-note">
        <span><i class="key-line"></i>Lo que marcó el sensor</span>
        <span><i class="key-line key-line--dash"></i>Lo que se espera</span>
        <span><i class="key-band"></i>Rango probable</span>
      </div>
      <div class="panel--flush" style="border-top:1px solid var(--border)">
        <table class="gas-table">
          <thead><tr><th>Gas</th><th>Ahora</th><th>En 10 min</th><th class="hide-sm">Última hora</th><th>Estado</th></tr></thead>
          <tbody>{gas_rows}</tbody>
        </table>
      </div>
    </section>
  </div>

  <aside class="stack">
    <section class="panel panel--flush" aria-labelledby="t-avisos">
      <div class="panel__head"><h2 id="t-avisos">Avisos abiertos</h2><a href="avisos.html" class="faint">Ver todos</a></div>
      <div class="alert-list">
        <article class="alert-item alert-item--actuar">
          <div class="alert-item__top"><span class="status status--actuar"><i data-icon="triangle-alert"></i>Actuar ya</span><span class="kind"><i data-icon="clock"></i>Anticipado</span><time datetime="10:33">hace 2 min</time></div>
          <h3>Metano en Frente 3 Sur</h3>
          <p>Se espera que llegue al límite en unos 7 minutos.</p>
          <div class="alert-item__actions"><a class="btn btn--primary" href="aviso.html">Ver qué hacer</a><button class="btn">Ya lo vi</button></div>
        </article>
        <article class="alert-item alert-item--vigilar">
          <div class="alert-item__top"><span class="status status--vigilar"><i data-icon="eye"></i>Vigilar</span><span class="kind"><i data-icon="clock"></i>Anticipado</span><time datetime="10:21">hace 14 min</time></div>
          <h3>Monóxido en Frente 1 Norte</h3>
          <p>Subió a 28 ppm y podría seguir subiendo. Visto por Carlos Pinzón.</p>
          <div class="alert-item__actions"><a class="btn" href="aviso.html">Ver detalle</a></div>
        </article>
        <article class="alert-item">
          <div class="alert-item__top"><span class="status status--sindatos"><i data-icon="circle-dashed"></i>Sin datos</span><time datetime="10:21">hace 14 min</time></div>
          <h3>Frente 4 Sur sin señal</h3>
          <p>El sensor de oxígeno no envía datos. Revisa la conexión o la batería.</p>
        </article>
      </div>
    </section>

    <section class="panel">
      <div class="panel__body" style="display:grid;gap:12px">
        <h3>Turno de la mañana</h3>
        <dl class="readings" style="grid-template-columns:1fr 1fr">
          <div><dt>Avisos hoy</dt><dd>3</dd></div>
          <div><dt>Atendidos</dt><dd>1</dd></div>
        </dl>
        <p class="faint">Tiempo medio para marcar un aviso como visto: 3 min.</p>
      </div>
    </section>
  </aside>
</div>"""
    return app_page("hoy", "Hoy", content)


def p_aviso():
    content = """
<div class="page-head">
  <div class="page-head__text">
    <a href="avisos.html" class="faint">Avisos</a>
    <h1 style="margin-top:4px">Metano en Frente 3 Sur</h1>
  </div>
  <div class="page-head__actions"><button class="btn">Ya lo vi</button><button class="btn btn--primary"><i data-icon="check"></i>Cerrar aviso</button></div>
</div>

<div class="home-grid">
  <div class="stack">
    <article class="alert-card">
      <div class="alert-card__head"><i data-icon="triangle-alert"></i><strong>Actuar ya</strong><span class="kind" style="color:inherit"><i data-icon="clock"></i>Aviso anticipado</span><time>Creado a las 10:33</time></div>
      <div class="alert-card__body">
        <p class="alert-card__lead">Se espera que el metano llegue al límite en unos 7 minutos, hacia las 10:42.</p>
        <dl class="readings">
          <div><dt>Ahora</dt><dd>0,72 <small>%</small></dd></div>
          <div><dt>Esperado en 10 min</dt><dd>1,05 <small>%</small></dd></div>
          <div class="is-limit"><dt>Límite para actuar</dt><dd>1,0 <small>%</small></dd></div>
        </dl>
        <div class="why"><div class="why__icon"><i data-icon="lightbulb"></i></div><div>
          <h3>Por qué avisamos</h3>
          <p>El metano viene subiendo sin pausa desde hace 20 minutos y el monóxido en la misma zona también aumentó. Estimación confiable por ahora.</p></div></div>
        <div class="todo"><div class="todo__icon"><i data-icon="shield-check"></i></div><div>
          <h3>Qué hacer</h3>
          <ol><li>Verificar que la ventilación del Frente 3 Sur esté funcionando.</li>
          <li>Suspender trabajos con equipos que puedan generar chispa.</li>
          <li>Preparar la salida del personal del frente si sigue subiendo.</li></ol></div></div>
      </div>
    </article>

    <section class="panel">
      <div class="panel__head"><h2>Ahora y lo que viene</h2><span class="faint">Última hora y próximos 10 minutos</span></div>
      <div class="chart" data-chart="now-next"></div>
      <div class="chart-note">
        <span><i class="key-line"></i>Lo que marcó el sensor</span>
        <span><i class="key-line key-line--dash"></i>Lo que se espera</span>
        <span><i class="key-band"></i>Rango probable</span>
      </div>
    </section>
  </div>

  <aside class="stack">
    <section class="panel">
      <div class="panel__head"><h3>Seguimiento</h3></div>
      <div class="panel__body">
        <ol class="timeline">
          <li><span class="tl-dot is-done"></span><div><strong>El sistema emitió el aviso</strong><span>10:33</span></div></li>
          <li><span class="tl-dot is-done"></span><div><strong>Se notificó a 3 contactos</strong><span>10:33 por correo y en la sala de control</span></div></li>
          <li><span class="tl-dot is-pending"></span><div><strong>Pendiente: alguien debe marcarlo como visto</strong><span>Hace 2 min</span></div></li>
          <li><span class="tl-dot is-pending"></span><div><strong>Cierre con nota</strong><span>Cuando la zona vuelva a la normalidad</span></div></li>
        </ol>
      </div>
    </section>
    <section class="panel">
      <div class="panel__head"><h3>Sobre esta zona</h3></div>
      <div class="panel__body" style="display:grid;gap:10px">
        <p><strong>Frente 3 Sur</strong><br><span class="muted">Manto 2, nivel inferior</span></p>
        <p class="muted">4 sensores activos. Último aviso en esta zona: hace 6 días, también por metano.</p>
        <a href="#">Ver historial de la zona</a>
      </div>
    </section>
  </aside>
</div>"""
    return app_page("avisos", "Aviso", content)


def p_avisos():
    def item(st, word, ico, title, text, when, kind="Anticipado", who=""):
        k = f'<span class="kind"><i data-icon="clock"></i>{kind}</span>' if kind else ""
        return f"""<article class="alert-item alert-item--{st}">
        <div class="alert-item__top"><span class="status status--{st}"><i data-icon="{ico}"></i>{word}</span>{k}<time>{when}</time></div>
        <h3>{title}</h3><p>{text}{who}</p>
        <div class="alert-item__actions"><a class="btn btn--primary" href="aviso.html">Ver qué hacer</a><button class="btn">Ya lo vi</button></div></article>"""
    content = f"""
<div class="page-head">
  <div class="page-head__text"><h1>Avisos</h1><p>Aquí aparecen los avisos que el sistema emite antes de que un gas llegue a su límite y cuando un sensor ya lo superó.</p></div>
  <div class="page-head__actions"><button class="btn"><i data-icon="download"></i>Descargar</button></div>
</div>
<div class="tabs" role="tablist">
  <button class="tab" role="tab" aria-selected="true">Abiertos <span class="count">3</span></button>
  <button class="tab" role="tab" aria-selected="false">Vistos <span class="count">5</span></button>
  <button class="tab" role="tab" aria-selected="false">Cerrados <span class="count">41</span></button>
</div>
<div class="filters">
  <select class="select" aria-label="Zona"><option>Todas las zonas</option></select>
  <select class="select" aria-label="Gas"><option>Todos los gases</option></select>
  <select class="select" aria-label="Nivel"><option>Todos los niveles</option></select>
</div>
<section class="panel panel--flush"><div class="alert-list">
  {item("actuar","Actuar ya","triangle-alert","Metano en Frente 3 Sur","Se espera que llegue al límite en unos 7 minutos. Ahora 0,72 %, límite 1,0 %.","hace 2 min")}
  {item("vigilar","Vigilar","eye","Monóxido en Frente 1 Norte","Subió a 28 ppm y podría seguir subiendo durante la próxima media hora.","hace 14 min", who=" Visto por Carlos Pinzón.")}
  <article class="alert-item"><div class="alert-item__top"><span class="status status--sindatos"><i data-icon="circle-dashed"></i>Sin datos</span><time>hace 14 min</time></div>
    <h3>Frente 4 Sur sin señal</h3><p>El sensor de oxígeno no envía datos desde las 10:21. Revisa la conexión o la batería.</p></article>
</div></section>"""
    return app_page("avisos", "Avisos", content)


def p_confiabilidad():
    content = f"""
<div class="page-head">
  <div class="page-head__text"><h1>¿Qué tan confiable es el sistema?</h1>
  <p>Comparamos cada aviso con lo que los sensores marcaron después. Así sabemos si el sistema avisó a tiempo, cuánto antes lo hizo y cuántas veces avisó sin necesidad.</p></div>
  <div class="page-head__actions"><select class="select" aria-label="Periodo"><option>Últimos 3 meses</option></select><button class="btn"><i data-icon="download"></i>Informe para gerencia</button></div>
</div>

<div class="trust-grid">
  <section class="panel trust">
    <p class="trust__q">¿Avisó a tiempo cuando hubo peligro?</p>
    <p class="trust__a">De cada 10 situaciones de riesgo, avisó a tiempo en <span class="reading">9</span></p>
    <div class="of-ten" data-of-ten="9" role="img" aria-label="9 de cada 10"></div>
    <p class="faint">Basado en 34 situaciones en las que un gas llegó al límite para actuar.</p>
  </section>
  <section class="panel trust">
    <p class="trust__q">¿Con cuánta anticipación?</p>
    <p class="trust__a">Avisa, en la mitad de los casos, <span class="reading">7</span> minutos antes o más</p>
    <div><div class="lead-bar"><span style="width:70%"></span></div><div class="lead-scale"><span>0 min</span><span>5</span><span>10 min</span></div></div>
    <p class="faint">En el 10 % de los casos con menos margen, avisó con 3 minutos.</p>
  </section>
  <section class="panel trust">
    <p class="trust__q">¿Cuántas veces avisa sin necesidad?</p>
    <p class="trust__a">Menos de <span class="reading">1</span> aviso innecesario por turno</p>
    <dl class="readings" style="grid-template-columns:1fr 1fr"><div><dt>Por turno</dt><dd>0,6</dd></div><div><dt>Meta</dt><dd>1,0</dd></div></dl>
    <p class="faint">Un aviso es innecesario si el gas no llegó al límite en los 15 minutos siguientes.</p>
  </section>
</div>

<div class="home-grid" style="margin-top:24px">
  <section class="panel">
    <div class="panel__head"><h2>Avisos a tiempo, mes a mes</h2><span class="faint">De cada 10 situaciones</span></div>
    <div class="chart chart--sm" data-chart="monthly"></div>
  </section>
  <section class="honest">
    <div class="why__icon"><i data-icon="info"></i></div>
    <div><h3>Lo que el sistema no avisó</h3>
      <p class="muted" style="margin-top:4px">Hubo 3 situaciones sin aviso previo, las tres en Frente 2 Norte durante cambios de turno. El equipo técnico las está revisando.</p>
      <p class="faint" style="margin-top:10px">Estas cifras se calculan solo con lecturas reales de los sensores de la mina.</p></div>
  </section>
</div>"""
    return app_page("confiabilidad", "Confiabilidad", content, user=("GM", "Gloria Moreno", "Gerencia"))


def p_equipo():
    rows = [
        ("AR", "Ana Rojas", "ana.rojas@mina.co", "Supervisora de seguridad", ["Todas"], "Hoy 06:02", "normal", "Activa"),
        ("CP", "Carlos Pinzón", "carlos.pinzon@mina.co", "Operador de sala", ["Frente 1 Norte", "Frente 2 Norte"], "Hoy 05:58", "normal", "Activo"),
        ("LM", "Luisa Mahecha", "luisa.mahecha@mina.co", "Operadora de sala", ["Frente 3 Sur", "Frente 4 Sur"], "Ayer 21:40", "normal", "Activa"),
        ("GM", "Gloria Moreno", "gloria.moreno@mina.co", "Gerencia", ["Todas"], "Hace 3 días", "normal", "Activa"),
        ("FS", "Fabio Sastoque", "fabio.sastoque@mina.co", "Analista de datos", ["Todas"], "Hoy 08:15", "normal", "Activo"),
        ("JD", "Juan Díaz", "juan.diaz@mina.co", "Administrador", ["Todas"], "Hoy 07:30", "normal", "Activo"),
        ("MT", "Mario Torres", "mario.torres@mina.co", "Operador de sala", ["Bocamina"], "—", "vigilar", "Invitado"),
        ("PR", "Pedro Ruiz", "pedro.ruiz@mina.co", "Auditor", ["Todas"], "Hace 2 semanas", "sindatos", "Bloqueado 15 min"),
    ]
    trs = ""
    for ini, n, e, role, zones, last, st, word in rows:
        tags = "".join(f'<span class="tag">{z}</span>' for z in zones)
        badge = f'<span class="status status--{st}">{word}</span>' if st != "normal" else f'<span class="faint">{word}</span>'
        trs += f'<tr><td><div class="person"><div class="avatar">{ini}</div><div><strong>{n}</strong><span>{e}</span></div></div></td><td><span class="tag tag--role">{role}</span></td><td>{tags}</td><td class="faint">{last}</td><td>{badge}</td><td><button class="btn btn--quiet" aria-label="Opciones de {n}">Editar</button></td></tr>'
    content = f"""
<div class="page-head">
  <div class="page-head__text"><h1>Equipo</h1><p>Quién puede entrar a Vigía, qué puede hacer y qué zonas ve. Las personas se invitan por correo y crean su propia contraseña.</p></div>
  <div class="page-head__actions"><button class="btn"><i data-icon="monitor"></i>Pantallas de sala</button><button class="btn btn--primary"><i data-icon="user-plus"></i>Invitar persona</button></div>
</div>
<div class="filters"><input class="input" placeholder="Buscar por nombre o correo" aria-label="Buscar"><select class="select" aria-label="Rol"><option>Todos los roles</option></select></div>
<section class="panel panel--flush" style="overflow-x:auto">
  <table class="table"><thead><tr><th>Persona</th><th>Rol</th><th>Zonas que ve</th><th>Último ingreso</th><th>Estado</th><th><span class="sr-only">Acciones</span></th></tr></thead><tbody>{trs}</tbody></table>
</section>
<div class="toast" role="status"><i data-icon="check"></i>Invitación enviada a mario.torres@mina.co</div>"""
    return app_page("equipo", "Equipo", content, user=("JD", "Juan Díaz", "Administrador"))


def p_laboratorio():
    models = [
        ("tft", "Transformer", "0,74", "0,031", "0,94", "0,91", "0,6", "7,2", "ok", "no", True),
        ("chronos2", "Fundacional", "0,77", "0,034", "0,91", "0,89", "0,8", "6,5", "no", "no", False),
        ("patchtst", "Transformer", "0,79", "0,036", "0,88", "0,90", "0,7", "6,1", "no", "no", False),
        ("timesfm", "Fundacional", "0,80", "0,037", "0,88", "0,86", "0,9", "6,0", "no", "no", False),
        ("itransformer", "Transformer", "0,81", "0,037", "0,85", "0,87", "0,8", "5,8", "no", "no", False),
        ("ttm", "Fundacional", "0,82", "0,038", "0,85", "0,84", "1,1", "5,4", "no", "no", False),
        ("lgbm_q", "Tabular", "0,84", "0,040", "0,82", "0,85", "0,9", "4,9", "no", "no", False),
        ("lstm", "Recurrente", "0,86", "0,041", "0,79", "0,83", "1,2", "4,6", "no", "no", False),
        ("ets", "Referencia", "0,97", "0,049", "0,62", "0,74", "1,8", "2,9", "no", "no", False),
        ("persistencia", "Referencia", "1,00", "0,052", "0,41", "0,68", "2,4", "1,5", "no", "no", False),
    ]
    trs = ""
    for k, fam, mase, rmse, rec, prec, fa, lead, g1, g2, prod in models:
        rg = "ok" if float(rec.replace(",", ".")) >= 0.95 else "no"
        pg = "ok" if float(prec.replace(",", ".")) >= 0.90 else "no"
        rmg = "ok" if float(rmse.replace(",", ".")) <= 0.05 else "no"
        mark = ' <span class="prod-mark">Activo</span>' if prod else ""
        trs += f'<tr><td><strong class="reading" style="font-size:.9rem">{k}</strong>{mark}</td><td class="faint">{fam}</td><td class="num">{mase}</td><td class="num"><span class="gate gate--{rmg}">{rmse}</span></td><td class="num"><span class="gate gate--{rg}">{rec}</span></td><td class="num"><span class="gate gate--{pg}">{prec}</span></td><td class="num">{fa}</td><td class="num">{lead}</td></tr>'
    content = f"""
<div class="tech-banner"><i data-icon="flask-conical" class="ico ico-sm"></i>Área técnica. Lo que se ve aquí no aparece en las vistas de operación ni de gerencia.</div>
<div class="page-head">
  <div class="page-head__text"><h1>Laboratorio de modelos</h1><p>Validación walk-forward con purga y embargo, 5 pliegues, solo datos reales. Metano, horizonte de 10 min, nivel Actuar ya.</p></div>
  <div class="page-head__actions"><button class="btn"><i data-icon="database"></i>Calidad de los datos</button><button class="btn btn--primary">Correr comparación</button></div>
</div>
<div class="stack">
  <section class="panel panel--flush" style="overflow-x:auto">
    <div class="panel__head"><h2>Comparación del zoo</h2><span class="faint">Media de los pliegues</span></div>
    <table class="table"><thead><tr><th>Modelo</th><th>Familia</th><th class="num">MASE</th><th class="num">RMSE % vol</th><th class="num">Recall evento</th><th class="num">Precisión evento</th><th class="num">Falsas / turno</th><th class="num">Anticipación p50</th></tr></thead><tbody>{trs}</tbody></table>
  </section>
  <aside class="lab-aside">
    <section class="panel"><div class="panel__head"><h3>MASE frente a persistencia</h3></div><div class="chart" data-chart="lab" style="height:340px"></div></section>
    <section class="panel"><div class="panel__body" style="display:grid;gap:8px"><h3>Metas de la tesis</h3>
      <ul class="faint" style="margin:0;padding-left:1.1em"><li>Recall por evento ≥ 0,95</li><li>Precisión por evento ≥ 0,90</li><li>RMSE CH₄ ≤ 0,05 % vol</li><li>Anticipación p50 ≥ 5 min</li></ul>
      <p class="muted">Ningún modelo cumple todas las metas todavía. Se reporta tal cual en la tesis.</p></div></section>
  </aside>
</div>"""
    return app_page("laboratorio", "Laboratorio", content, user=("FS", "Fabio Sastoque", "Analista de datos"))


def p_sala():
    def tile(st, name, gases, note=""):
        g = "".join(f"<div><span>{a}</span><b>{b}</b></div>" for a, b in gases)
        ico = {"normal": "circle-check", "vigilar": "eye", "actuar": "triangle-alert", "sindatos": "circle-dashed"}[st]
        word = {"normal": "Normal", "vigilar": "Vigilar", "actuar": "Actuar ya", "sindatos": "Sin datos"}[st]
        return f'<section class="zone-tile zone-tile--{st}"><div style="display:flex;align-items:center;gap:10px;justify-content:space-between"><h2>{name}</h2><span class="status status--{st}"><i data-icon="{ico}"></i>{word}</span></div><div class="zone-tile__gases">{g}</div>{note}</section>'
    return HEAD.format(title="Sala de control", theme=' data-theme="sala"', body_theme="") + f"""
<main class="sala">
  <header class="sala__top"><img src="assets/img/isotipo.svg" alt=""><strong>Vigía, sala de control</strong>
    <span class="topbar__live" style="margin-left:24px"><span class="dot-live"></span>Datos al día</span>
    <span class="sala__clock" data-clock>10:35</span></header>
  <section class="sala__alert" role="alert">
    <i data-icon="triangle-alert" class="ico" style="width:56px;height:56px;color:var(--st-actuar)"></i>
    <div><div class="big">Frente 3 Sur: actuar ya</div><p>El metano podría llegar al límite hacia las 10:42. Verificar ventilación y preparar la salida del personal.</p></div>
    <div class="reading">0,72 %<small>Límite 1,0 %</small></div>
  </section>
  <div style="display:grid;grid-template-columns:1.25fr 1fr;gap:24px;align-items:start">
    <section class="panel"><div class="panel__head"><h2>Metano en Frente 3 Sur</h2></div><div class="chart chart--fill" data-chart="now-next" data-big="1"></div></section>
    <div class="sala__zones" style="grid-template-columns:1fr 1fr">
      {tile("vigilar","Frente 1 Norte",[("Metano","0,31 %"),("Monóxido","28 ppm")])}
      {tile("normal","Frente 2 Norte",[("Metano","0,21 %"),("Monóxido","6 ppm")])}
      {tile("sindatos","Frente 4 Sur",[("Oxígeno","—"),("Metano","0,19 %")], '<p class="faint">Sin señal desde las 10:21</p>')}
      {tile("normal","Galería principal",[("Metano","0,18 %"),("Monóxido","4 ppm")])}
    </div>
  </div>
</main>""" + FOOT


def p_componentes():
    content = """
<div class="page-head"><div class="page-head__text"><h1>Componentes</h1><p>Catálogo vivo. En la app vive en /_componentes (solo entorno local) y es la base de las capturas de regresión visual.</p></div></div>
<div class="stack">
<section class="panel"><div class="panel__head"><h2>Estados</h2></div><div class="panel__body" style="display:flex;gap:10px;flex-wrap:wrap">
  <span class="status status--normal"><i data-icon="circle-check"></i>Normal</span>
  <span class="status status--vigilar"><i data-icon="eye"></i>Vigilar</span>
  <span class="status status--actuar"><i data-icon="triangle-alert"></i>Actuar ya</span>
  <span class="status status--evacuar"><i data-icon="siren"></i>Evacuar</span>
  <span class="status status--sindatos"><i data-icon="circle-dashed"></i>Sin datos</span>
  <span class="status status--actuar status--lg"><i data-icon="triangle-alert"></i>Actuar ya</span>
</div></section>
<section class="panel"><div class="panel__head"><h2>Botones</h2></div><div class="panel__body" style="display:flex;gap:10px;flex-wrap:wrap">
  <button class="btn btn--primary">Cerrar aviso</button><button class="btn">Ya lo vi</button><button class="btn btn--quiet">Cancelar</button><button class="btn btn--danger">Evacuar zona</button><button class="btn btn--primary btn--lg">Ingresar</button>
</div></section>
<section class="panel"><div class="panel__head"><h2>Lecturas</h2></div><div class="panel__body">
  <dl class="readings"><div><dt>Ahora</dt><dd>0,72 <small>%</small></dd></div><div><dt>Esperado en 10 min</dt><dd>1,05 <small>%</small></dd></div><div class="is-limit"><dt>Límite para actuar</dt><dd>1,0 <small>%</small></dd></div></dl>
</div></section>
<section class="panel"><div class="panel__head"><h2>Estados vacíos e ilustraciones</h2></div><div class="panel__body" style="display:grid;grid-template-columns:repeat(3,1fr);gap:16px">
  <div class="empty"><img src="assets/img/vacio-despejado.svg" alt=""><h3>No hay avisos abiertos</h3><p>Todas las zonas están normales. Te avisaremos aquí si algo cambia.</p></div>
  <div class="empty"><img src="assets/img/sensor-sin-datos.svg" alt=""><h3>Este sensor no envía datos</h3><p>Última lectura hace 14 min. Revisa la conexión o la batería.</p><button class="btn">Ver último dato</button></div>
  <div class="empty"><img src="assets/img/error-galeria.svg" alt=""><h3>Esta página no existe</h3><p>Puede que el enlace esté mal escrito o que la página se haya movido.</p><a class="btn btn--primary" href="hoy.html">Volver a Hoy</a></div>
</div></section>
</div>"""
    return app_page("hoy", "Componentes", content)


PAGES = {
    "ingresar": p_ingresar, "hoy": p_hoy, "avisos": p_avisos, "aviso": p_aviso,
    "confiabilidad": p_confiabilidad, "equipo": p_equipo, "laboratorio": p_laboratorio,
    "sala": p_sala, "componentes": p_componentes,
}

if __name__ == "__main__":
    for name, fn in PAGES.items():
        (OUT / f"{name}.html").write_text(fn(), encoding="utf-8")
        print("ok", name)
