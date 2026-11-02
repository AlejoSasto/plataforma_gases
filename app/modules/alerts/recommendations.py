"""Recomendaciones por gas. La decisión operativa usa normative_thresholds (Plan 17/23)."""

from __future__ import annotations

# Recomendaciones editables por código de gas / tipo
GAS_RECOMMENDATIONS: dict[str, str] = {
    "CO": "Verificar ventilación y fuentes de combustión; limitar exposición.",
    "CO2": "Aumentar ventilación y revisar acumulación en espacios cerrados.",
    "NO2": "Evitar fuentes de combustión diesel; usar EPP respiratorio si aplica.",
    "H2S": "Evacuar zona si es necesario; verificar detectores y escape de gas.",
    "LEL": "Eliminar fuentes de ignición; ventilar y monitorear atmósfera explosiva.",
    "LEL(CH4)": "Eliminar fuentes de ignición; ventilar y monitorear metano.",
    "O2": "Evacuar zona, revisar suministro de aire y posible desplazamiento de oxígeno.",
    "DEFAULT": "Monitorear la zona, confirmar lectura con instrumento calibrado y aplicar protocolo del sitio.",
}


def recommendation_for_gas(gas_type: str | None) -> str:
    if not gas_type:
        return GAS_RECOMMENDATIONS["DEFAULT"]
    key = gas_type.strip().upper()
    # Normalizar nombres largos
    aliases = {
        "MONÓXIDO DE CARBONO": "CO",
        "MONOXIDO DE CARBONO": "CO",
        "DIÓXIDO DE CARBONO": "CO2",
        "DIOXIDO DE CARBONO": "CO2",
        "DIÓXIDO DE NITRÓGENO": "NO2",
        "DIOXIDO DE NITROGENO": "NO2",
        "SULFURO DE HIDRÓGENO": "H2S",
        "SULFURO DE HIDROGENO": "H2S",
        "OXÍGENO": "O2",
        "OXIGENO": "O2",
        "GAS COMBUSTIBLE": "LEL",
    }
    key = aliases.get(key, key)
    if key in GAS_RECOMMENDATIONS:
        return GAS_RECOMMENDATIONS[key]
    for code, text in GAS_RECOMMENDATIONS.items():
        if code != "DEFAULT" and code in key:
            return text
    return GAS_RECOMMENDATIONS["DEFAULT"]
