"""Textos de la operación. Los templates no escriben jerga suelta (Plan 18)."""

from __future__ import annotations

from typing import Any

FORBIDDEN_TERMS: tuple[str, ...] = (
    "modelo",
    "algoritmo",
    "prediccion",
    "probabilidad",
    "inferencia",
    "cuantil",
    "percentil",
    "recall",
    "precision",
    "f1",
    "rmse",
    "mae",
    "mase",
    "dataset",
    "entrenamiento",
    "staging",
    "production",
    "threshold",
    "lead time",
    "ml",
    "machine learning",
    "ia",
    "transformer",
    "lstm",
    "tft",
    "etl",
    "json",
    "api",
    "id",
)

STATUS_WORD = {
    "normal": "Normal",
    "vigilar": "Vigilar",
    "actuar": "Actuar ya",
    "evacuar": "Evacuar",
    "sin_datos": "Sin datos",
    "NORMAL": "Normal",
    "PRECAUCION": "Vigilar",
    "ALERTA": "Actuar ya",
    "CRITICO": "Evacuar",
}

STATUS_ICON = {
    "normal": "circle-check",
    "vigilar": "eye",
    "actuar": "triangle-alert",
    "evacuar": "siren",
    "sin_datos": "circle-dashed",
}

NAV = {
    "hoy": "Hoy",
    "avisos": "Avisos",
    "zonas": "Equipos",
    "historial": "Historial",
    "informes": "Informes",
    "confiabilidad": "Confiabilidad",
    "equipo": "Equipo",
    "ajustes": "Ajustes",
    "laboratorio": "Laboratorio",
    "contactos": "Contactos",
    "bitacora": "Bitácora",
    "cuenta": "Mi cuenta",
    "cargar": "Cargar datos",
    "calidad": "Calidad de los datos",
    "ayuda": "Ayuda",
}

BRAND = "Vigía"
BRAND_SUB = "Gases en la mina"
ASK = "Preguntar"
ASK_WELCOME = "Pregúntame por los gases, los avisos o cómo usar Vigía. Los datos llegan hasta el {fecha}."
ASK_OFFLINE = "El asistente no está disponible sin conexión. Puedes usar los filtros de cada pantalla."
ASK_EMERGENCY = (
    "Si hay una emergencia, activa ya el protocolo de la mina y avisa al supervisor de turno. "
    "Este asistente no reemplaza la comunicación de emergencia."
)
ASK_OFF_TOPIC = (
    "Solo puedo ayudarte con información de los gases, los avisos, los informes y el uso de Vigía. "
    "¿Qué necesitas consultar?"
)
ASK_SAFETY = (
    "No puedo decidir si es seguro entrar. Esa decisión es del supervisor de turno con la medición en sitio."
)
ASK_PROTOCOL = "Sigue el protocolo de seguridad de la mina."
ASK_SOURCES = "De dónde sale esta respuesta"
ASK_WORKING = "Consultando datos…"
ASK_USEFUL = "¿Te sirvió?"
ASK_HISTORIC = "Es una revisión histórica, no la situación en vivo."
ASK_LIVE = "Esto corresponde a los datos en vivo."
ASK_DENIED = "No puedes consultar eso con tu rol."
NO_MODEL = "Por ahora mostramos solo lo que marcan los sensores"
NO_FORECAST = NO_MODEL
CHART_EMPTY = "Este sensor no tiene lecturas en este periodo"
CHART_ERROR = "No pudimos cargar el gráfico. Intenta de nuevo"
CHART_RETRY = "Reintentar"
LAB_BADGE = "Área técnica"
LOGIN_TITLE = "Ingresar"
LOGIN_SUB = "Saber a tiempo qué está pasando con los gases en la mina."
LOGIN_HINT = "Usa el correo con el que te invitaron."
LOGIN_STATUS = "El sistema está funcionando y recibe datos"
MINE_LABEL = "Caso de estudio · Cundinamarca"
LOGIN_CTA = "Ingresar"
FORGOT = "¿Olvidaste tu contraseña?"
LOGIN_BAD = "El correo o la contraseña no coinciden. Revisa e intenta de nuevo."
LOGIN_LOCKED = "Por seguridad bloqueamos el acceso por 15 minutos. Si necesitas entrar ya, contacta al administrador."
LOGIN_TOTP = "Escribe el código de 6 dígitos de tu aplicación de autenticación"
KEEP_SESSION = "Mantener la sesión durante mi turno"
SHOW_PASSWORD = "Mostrar"
EMPTY_SENSORS_TITLE = "Aún no hay equipos con lecturas"
EMPTY_SENSORS_TEXT = "Cuando lleguen lecturas de un detector, aquí veremos cada gas de ese equipo."
EMPTY_ALERTS_TITLE = "No hay avisos abiertos"
EMPTY_ALERTS_TEXT = "Si algo cambia, aparecerá aquí con qué hacer."
ACK = "Ya lo vi"
RESOLVE = "Cerrar aviso"
BACK_HOME = "Volver al inicio"
TECHNICAL_NOTE = "Esta pantalla es del área técnica."


def status_word(level: str | None) -> str:
    if not level:
        return STATUS_WORD["sin_datos"]
    return STATUS_WORD.get(level, STATUS_WORD.get(str(level).lower(), str(level)))


def status_key(level: str | None) -> str:
    raw = (level or "sin_datos").lower()
    mapping = {
        "normal": "normal",
        "vigilar": "vigilar",
        "precaucion": "vigilar",
        "precaución": "vigilar",
        "actuar": "actuar",
        "alerta": "actuar",
        "evacuar": "evacuar",
        "critico": "evacuar",
        "crítico": "evacuar",
        "sin_datos": "sin_datos",
    }
    return mapping.get(raw, "sin_datos" if raw in {"", "none"} else raw)


def status_icon(level: str | None) -> str:
    return STATUS_ICON.get(status_key(level), "circle-dashed")


def number_es(value: float | int | None, decimals: int = 2) -> str:
    if value is None:
        return "—"
    try:
        num = float(value)
    except (TypeError, ValueError):
        return "—"
    q = f"{num:.{decimals}f}"
    whole, frac = q.split(".")
    sign = ""
    if whole.startswith("-"):
        sign = "-"
        whole = whole[1:]
    grouped = ""
    while len(whole) > 3:
        grouped = "." + whole[-3:] + grouped
        whole = whole[:-3]
    grouped = whole + grouped
    frac = frac.rstrip("0")
    if not frac:
        return sign + grouped
    return f"{sign}{grouped},{frac}"


def possibility(p: float | None, pi: float = 0.55) -> str:
    if p is None:
        return "Sin dato"
    if p >= pi:
        return "Alta"
    if p >= pi / 2:
        return "Media"
    return "Baja"


def confidence_phrase(level: str | None) -> str:
    key = (level or "").lower()
    if key in {"alta", "high"}:
        return "Estimación muy confiable por ahora"
    if key in {"media", "medium"}:
        return "Estimación confiable por ahora"
    if key in {"baja", "low"}:
        return "Estimación poco confiable por ahora"
    return "Estimación en revisión"


def missing_since(minutes: int) -> str:
    return f"Este sensor no ha enviado datos desde hace {minutes} min"


def expected_around(value: float, unit: str = "%") -> str:
    return f"Se espera alrededor de {number_es(value)} {unit}".strip()


def range_phrase(lo: float, hi: float, unit: str = "%") -> str:
    return f"Podría estar entre {number_es(lo)} {unit} y {number_es(hi)} {unit}".strip()


def ahead_minutes(n: int) -> str:
    return f"En los próximos {n} minutos"


def alert_card(
    *,
    level: str,
    gas: str,
    zone: str,
    minutes: int | None,
    now_value: str,
    expected: str,
    limit: str,
    why: str,
    action: str,
    kind: str = "anticipado",
) -> dict[str, str]:
    word = status_word(level)
    if kind == "confirmado":
        headline = "El sensor ya marca un nivel por encima del límite"
    elif minutes is not None:
        headline = f"Se espera que llegue al límite en unos {minutes} minutos."
    else:
        headline = "El sistema espera un cambio en los próximos minutos."
    return {
        "title": f"{word} · {gas} · {zone}",
        "headline": headline,
        "now": f"Ahora: {now_value}",
        "expected": f"Esperado: {expected}",
        "limit": f"Límite: {limit}",
        "why": f"Por qué avisamos: {why}",
        "action": f"Qué hacer: {action}",
        "ack": ACK,
        "detail": "Ver detalle",
    }


def reliability_recall(ok: int, total: int = 10) -> str:
    return f"De cada {total} situaciones peligrosas, el sistema avisó a tiempo {ok}"


def reliability_lead(minutes: int) -> str:
    return f"Avisa en promedio {minutes} minutos antes"


def reliability_fa(n: float) -> str:
    pretty = number_es(n, 1)
    return f"{pretty} aviso innecesario por turno"


def banner_summary(n_attention: int) -> str:
    if n_attention <= 0:
        return "Todo normal"
    if n_attention == 1:
        return "1 zona requiere atención"
    return f"{n_attention} zonas requieren atención"


def audit_phrase(who: str, action: str, when: str, details: str | None = None) -> str:
    mapping = {
        "alert.acknowledge": "marcó como visto el aviso",
        "alert.resolve": "cerró el aviso",
        "ml.promote": "activó un cambio en el laboratorio",
        "ingestion.upload": "cargó datos",
        "auth.login_ok": "ingresó",
        "auth.login_fail": "intentó ingresar sin éxito",
        "auth.locked": "quedó bloqueado por intentos fallidos",
        "auth.logout": "cerró la sesión",
        "auth.password_reset_requested": "pidió restablecer la contraseña",
        "auth.password_reset_done": "cambió la contraseña con un enlace",
        "auth.totp_enabled": "activó la verificación en dos pasos",
        "auth.session_revoked": "cerró una sesión",
        "user.invited": "invitó a una persona",
        "user.invitation_accepted": "aceptó la invitación",
        "user.role_changed": "cambió el rol de una persona",
        "user.scope_changed": "cambió las zonas de una persona",
        "user.unlocked": "desbloqueó a una persona",
        "user.create": "añadió a una persona al equipo",
        "kiosk.created": "creó una pantalla de sala",
        "kiosk.revoked": "revocó una pantalla de sala",
        "threshold.changed": "cambió un límite",
    }
    if details:
        return f"{who} {details} a las {when}"
    verb = mapping.get(action, "hizo un cambio")
    return f"{who} {verb} a las {when}"


def stage_label(code: str) -> str:
    return {
        "E1": "Leyendo archivo…",
        "E2": "Revisando datos…",
        "E3": "Pasando a unidades de la mina…",
        "E4": "Marcando lecturas con problemas…",
        "E5": "Guardando lecturas…",
        "E6": "Armando la línea de tiempo…",
    }.get(code, "Trabajando…")


def g0_note(horizons: list[int]) -> str:
    hs = ", ".join(str(h) for h in horizons)
    return (
        f"Con las lecturas actuales el sistema puede mirar {hs} minutos hacia adelante. "
        "No prometemos avisos a 5 minutos hasta tener datos más seguidos."
    )


def operative_strings() -> list[str]:
    """Todas las cadenas que ve la operación (para el verificador)."""
    bag: list[str] = [
        BRAND,
        NO_MODEL,
        LOGIN_TITLE,
        LOGIN_SUB,
        LOGIN_CTA,
        FORGOT,
        LOGIN_BAD,
        LOGIN_LOCKED,
        LOGIN_TOTP,
        KEEP_SESSION,
        EMPTY_SENSORS_TITLE,
        EMPTY_SENSORS_TEXT,
        EMPTY_ALERTS_TITLE,
        EMPTY_ALERTS_TEXT,
        ACK,
        RESOLVE,
        BACK_HOME,
        *NAV.values(),
        *STATUS_WORD.values(),
        banner_summary(0),
        banner_summary(2),
        reliability_recall(9),
        reliability_lead(7),
        reliability_fa(1),
        missing_since(15),
        expected_around(0.8),
        range_phrase(0.6, 1.0),
        ahead_minutes(10),
        confidence_phrase("alta"),
        confidence_phrase("media"),
        confidence_phrase("baja"),
        g0_note([6, 12, 18]),
        "Por ahora mostramos solo lo que marcan los sensores",
        ASK,
        ASK_WELCOME,
        ASK_OFFLINE,
        ASK_EMERGENCY,
        ASK_OFF_TOPIC,
        ASK_SAFETY,
        ASK_PROTOCOL,
        ASK_SOURCES,
        ASK_WORKING,
        ASK_USEFUL,
        ASK_HISTORIC,
        ASK_LIVE,
        "Cargar datos",
        "Ya lo vi",
        "Cerrar aviso",
        "Qué hacer",
        "Por qué avisamos",
        "Zona",
        "Sensor",
        "Ahora",
        "Lo que viene",
    ]
    sample = alert_card(
        level="actuar",
        gas="Metano",
        zone="Zona",
        minutes=7,
        now_value="—",
        expected="—",
        limit="—",
        why="viene subiendo sin pausa desde hace 20 minutos",
        action="revisar la ventilación y preparar la salida del personal",
    )
    bag.extend(sample.values())
    bag.extend(stage_label(f"E{i}") for i in range(1, 7))
    return bag
