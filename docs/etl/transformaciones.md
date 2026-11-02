# Transformaciones ETL v2

Contrato de etapas E1–E6 (Plan 15 F2). Conteos de la última corrida sobre el consolidado real (sin persistir).

Fuente: `Procesamiento_de_Datos.csv`

| Etapa | Filas in | Filas out | Rechazadas | Detalle |
|-------|--------:|---------:|-----------:|---------|
| E1 | 13894 | 13894 | 0 | `{"kind": "csv", "source": "Procesamiento_de_Datos.csv", "expected_columns": ["Descripción", "Sensor", "Número de Periodo", "Gas", "Leyendo", "Unidad", "STEL Máx", "TWA máximo", ...` |
| E2 | 13894 | 13894 | 0 | `{"rejected_sample": [], "rejected_total": 0}` |
| E3 | 13894 | 13894 | 0 | `{"conversions": 4714, "unidad_desconocida": 0}` |
| E4 | 13894 | 13894 | 0 | `{"issue_counts": {"fuera_de_rango_fisico": 2337, "hueco": 2335, "salto_imposible": 133, "valor_congelado": 32}, "n_issues": 4837}` |
| E6 | 13894 | 821205 | 0 | `{"imputed_steps": 31, "missing_steps": 821152, "step_minutes": 1}` |

## Etapas

- **E1 Extraer:** Excel `dls_report` (hoja Resumen, cabecera 24) o CSV consolidado.
- **E2 Validar:** 15 columnas canónicas, `Leyendo` numérico, fechas parseables.
- **E3 Estandarizar:** gas/sensor canónicos; CH₄ %LEL → % vol (LIE=5,0); CO₂ %vol → ppm.
- **E4 Calidad:** marca problemas; no borra (salvo exclusión de fuera de rango / unidad desconocida al cargar).
- **E5 Cargar:** idempotente por SHA-256 del archivo y (sensor, tiempo).
- **E6 Rejilla:** remuestreo regular; ffill ≤ 3 pasos; huecos largos como faltantes. Nunca interpola al futuro.
