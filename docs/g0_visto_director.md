# Visto del director — Compuerta G0

**Estado técnico:** implementada y en producción local.  
**Estado académico:** falta la firma de la persona directora de tesis. Esta IA no puede firmar en su nombre.

## Decisión (evidencia)

Fuente: `reports/diagnostico/g0_decision.json` y bitácora Plan 15 F0.

| Dato | Valor |
|------|--------|
| Δt p50 CH₄ | 5,77 min |
| Banda | medium (2 < Δt ≤ 10) |
| Horizontes prometidos | **6, 12 y 18 min** (1, 2 y 3 pasos de rejilla) |
| Lo que ya no se promete | 5 y 10 min del anteproyecto |
| Acción de datos | solicitar al proveedor el datalog crudo iNet por intervalo |

La plataforma usa estos horizontes en `app_settings.forecast_horizons_min` y en `ProblemSpec`.

## Firma

| Campo | Completar a mano |
|-------|------------------|
| Nombre del director/a | |
| Fecha | |
| Decisión | Apruebo G0 6/12/18 / Pido otro horizonte |
| Firma | |

Cuando esté firmado, anotar la fecha en `planes/BITACORA_BUCLE.md`.
