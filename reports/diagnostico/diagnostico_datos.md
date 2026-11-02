# Diagnóstico de datos reales

Generado: `2026-11-01T23:21:16.812873+00:00`
Fuente: `csv:Procesamiento_de_Datos.csv`

## Resumen

- Filas reales: **13894**
- Pares sensor-gas: **50**
- Gases: CH4, CO, CO2, H2S, O2, UNKNOWN
- Rango: 2023-03-31T14:37:09+00:00 → 2025-12-11T14:17:44+00:00
- Duplicados exactos: 0
- Casi duplicados (≤60 s, mismo valor): 10

## Compuerta G0

- Δt mediana (máximo entre CH₄, CO, H₂S): **5.7708 min**
- Banda: `medium`
- Horizontes (minutos): `[6, 12, 18]`
- 2 < Δt ≤ 10 min (Δt=5.77). Horizontes = 1, 2 y 3 pasos. Solicitar al proveedor el export de datalog por intervalo.

Δt por gas prioritario:

| Gas | Δt p50 (min) |
|-----|-------------:|
| CH4 | 5.7708 |
| CO | 2.5375 |
| H2S | 1.0 |

Umbrales usados para episodios: semilla Plan 15 F4 (`verified=false`).
LIE CH₄ usado en conversión %LEL→%vol: 5.0 % vol.

## Episodios de inicio por gas y nivel

| Gas | Nivel | Dirección | Umbral | Inicios | Política de evaluación |
|-----|-------|-----------|-------:|--------:|------------------------|
| CH4 | vigilar | above | 0.5 | 1 | no_event_metrics |
| CH4 | actuar | above | 1.0 | 1 | no_event_metrics |
| CH4 | evacuar | above | 1.5 | 1 | no_event_metrics |
| CO | vigilar | above | 25.0 | 7 | no_event_metrics |
| CO | actuar | above | 50.0 | 4 | no_event_metrics |
| CO | evacuar | above | 100.0 | 3 | no_event_metrics |
| H2S | vigilar | above | 1.0 | 59 | bootstrap_ic |
| H2S | actuar | above | 5.0 | 7 | no_event_metrics |
| H2S | evacuar | above | 10.0 | 5 | no_event_metrics |
| O2 | vigilar | below | 19.5 | 53 | bootstrap_ic |
| O2 | actuar | below | 19.0 | 24 | wide_ic_warning |
| O2 | evacuar | below | 17.0 | 14 | wide_ic_warning |

## Densidad por mes y gas

| Mes | Gas | Filas |
|-----|-----|------:|
| 2023-03 | CH4 | 14 |
| 2023-03 | CO | 3 |
| 2023-03 | O2 | 15 |
| 2023-03 | UNKNOWN | 8 |
| 2024-09 | CH4 | 18 |
| 2024-09 | CO | 18 |
| 2024-09 | CO2 | 84 |
| 2024-09 | H2S | 247 |
| 2024-09 | O2 | 63 |
| 2024-09 | UNKNOWN | 83 |
| 2024-11 | CH4 | 39 |
| 2024-11 | CO | 2481 |
| 2024-11 | CO2 | 2950 |
| 2024-11 | H2S | 1524 |
| 2024-11 | O2 | 1470 |
| 2024-11 | UNKNOWN | 473 |
| 2024-12 | CH4 | 3 |
| 2024-12 | CO | 3 |
| 2024-12 | CO2 | 3 |
| 2024-12 | H2S | 3 |
| 2024-12 | O2 | 3 |
| 2024-12 | UNKNOWN | 3 |
| 2025-08 | CH4 | 3 |
| 2025-08 | CO | 37 |
| 2025-08 | CO2 | 46 |
| 2025-08 | H2S | 105 |
| 2025-08 | O2 | 42 |
| 2025-08 | UNKNOWN | 3 |
| 2025-09 | CH4 | 6 |
| 2025-09 | CO | 30 |
| 2025-09 | CO2 | 62 |
| 2025-09 | H2S | 155 |
| 2025-09 | O2 | 59 |
| 2025-09 | UNKNOWN | 10 |
| 2025-10 | CH4 | 25 |
| 2025-10 | CO | 27 |
| 2025-10 | CO2 | 52 |
| 2025-10 | H2S | 46 |
| 2025-10 | O2 | 28 |
| 2025-10 | UNKNOWN | 6 |
| 2025-11 | CH4 | 255 |
| 2025-11 | CO | 52 |
| 2025-11 | CO2 | 1010 |
| 2025-11 | H2S | 276 |
| 2025-11 | O2 | 635 |
| 2025-11 | UNKNOWN | 116 |
| 2025-12 | CH4 | 128 |
| 2025-12 | CO | 65 |
| 2025-12 | CO2 | 491 |
| 2025-12 | H2S | 191 |
| 2025-12 | O2 | 379 |
| 2025-12 | UNKNOWN | 46 |

## Unidades observadas

- **CH4**: %lel, %vol
- **CO**: ppm
- **CO2**: %vol
- **H2S**: ppm
- **O2**: %vol
- **UNKNOWN**: ppm

## Sensores (intervalo y tipo probable)

| Sensor | Gas | n | p10 | p50 | p90 | % huecos >3×med | Tipo |
|--------|-----|--:|----:|----:|----:|----------------:|------|
| `160541U005#S0001` | CO | 2484 | 0.1667 | 0.1667 | 0.6667 | 11.92 | portatil |
| `160541U005#S0002` | H2S | 1527 | 0.1667 | 0.1667 | 0.8333 | 12.78 | portatil |
| `161107V011#S0011` | CO2 | 9 | 1.0 | 2.0 | 6.66 | 12.5 | portatil |
| `17020PE013#S0011` | CO2 | 2953 | 0.1667 | 0.1667 | 1.1667 | 20.8 | portatil |
| `17030B6004#S0011` | CO2 | 6 | 1.1667 | 1.5333 | 6255.6633 | 20.0 | portatil |
| `1807482030#S0004` | UNKNOWN | 8 | 0.1667 | 0.1667 | 1.5533 | 42.86 | portatil |
| `19052Q1004#S0001` | CO | 3 | 5.6667 | 8.8667 | 12.0667 | 0.0 | desconocido |
| `19052Q1004#S0002` | H2S | 8 | 1.0 | 3.8667 | 8.7467 | 14.29 | portatil |
| `1908138189#S0021` | CH4 | 14 | 0.1667 | 0.1667 | 0.6067 | 15.38 | portatil |
| `20091E1013#S0004` | UNKNOWN | 13 | 1.1 | 31.5 | 11539.785 | 16.67 | portatil |
| `20100B2010#S0001` | CO | 67 | 1.0 | 1.0 | 18.0 | 31.82 | portatil |
| `20100B2010#S0002` | H2S | 260 | 1.0 | 1.0 | 4.0 | 12.74 | portatil |
| `20100MY003#S0011` | CO2 | 108 | 1.0 | 1.0 | 12.8933 | 20.56 | portatil |
| `21071TQ142#S0020` | O2 | 15 | 0.1667 | 0.1667 | 0.7833 | 21.43 | portatil |
| `210802X034#S0001` | CO | 5 | 1.7983 | 2.675 | 7297.785 | 25.0 | portatil |
| `210802X034#S0002` | H2S | 5 | 1.7983 | 2.675 | 7297.785 | 25.0 | portatil |
| `21080LJ005#S0004` | UNKNOWN | 5 | 1.7983 | 2.675 | 7297.785 | 25.0 | portatil |
| `22061PG059#S0001` | CO | 18 | 0.1667 | 0.6667 | 13.2267 | 29.41 | portatil |
| `22061PG059#S0002` | H2S | 32 | 0.1667 | 0.1667 | 5.15 | 25.81 | portatil |
| `2206309128#S0001` | CO | 3 | 2.08 | 2.4 | 2.72 | 0.0 | desconocido |
| `22081FT036#S0022` | CH4 | 16 | 0.2333 | 1.2167 | 13.3067 | 26.67 | portatil |
| `22081JU008#S0020` | O2 | 12 | 0.9 | 1.7667 | 13.4667 | 27.27 | portatil |
| `22082AR052#S0021` | CH4 | 383 | 1.0 | 2.0 | 19.0 | 20.16 | fijo |
| `22082AR056#S0021` | CH4 | 9 | 18.2483 | 40.0 | 14560.0217 | 25.0 | portatil |
| `22083AF012#S0004` | UNKNOWN | 83 | 0.1667 | 0.3333 | 6.905 | 37.8 | fijo |
| `220929G001#S0011` | CO2 | 36 | 0.1667 | 0.3333 | 6.66 | 22.86 | portatil |
| `2209364013#S0011` | CO2 | 84 | 0.1667 | 0.1667 | 10.3833 | 38.55 | fijo |
| `2209364017#S0011` | CO2 | 1501 | 1.0 | 1.0 | 2.0 | 6.0 | fijo |
| `2209366013#S0001` | CO | 18 | 1.2233 | 9.9167 | 1845.1333 | 35.29 | fijo |
| `2209366013#S0002` | H2S | 247 | 0.1667 | 0.1667 | 0.8333 | 11.38 | fijo |
| `2209366026#S0001` | CO | 117 | 1.0 | 3.0 | 1224.775 | 37.07 | fijo |
| `2209366026#S0002` | H2S | 467 | 1.0 | 1.0 | 10.5 | 19.31 | fijo |
| `2210031012#S0004` | UNKNOWN | 476 | 0.1667 | 0.1667 | 2.5 | 23.37 | portatil |
| `22101J7044#S0021` | CH4 | 18 | 1.2233 | 9.9167 | 1845.1333 | 35.29 | fijo |
| `22101YV009#S0020` | O2 | 63 | 0.1667 | 0.8333 | 20.4283 | 32.26 | fijo |
| `23050W8028#S0020` | O2 | 1473 | 0.1667 | 0.3333 | 2.3333 | 21.54 | portatil |
| `23081F0018#S0004` | UNKNOWN | 162 | 1.0 | 2.0 | 118.9667 | 36.02 | fijo |
| `231025H023#S0001` | CO | 1 | None | None | None | None | desconocido |
| `231025H023#S0002` | H2S | 1 | None | None | None | None | desconocido |
| `23110AS018#S0021` | CH4 | 1 | None | None | None | None | desconocido |
| `23110Z4010#S0004` | UNKNOWN | 1 | None | None | None | None | desconocido |
| `231215G022#S0021` | CH4 | 5 | 1.7983 | 2.675 | 7297.785 | 25.0 | portatil |
| `24011Y1009#S0011` | CO2 | 1 | None | None | None | None | desconocido |
| `24062BR010#S0021` | CH4 | 42 | 0.3333 | 30.65 | 2851.6 | 36.59 | portatil |
| `241033Q134#S0020` | O2 | 1014 | 1.0 | 1.0 | 5.0 | 15.5 | fijo |
| `2412083053#S0020` | O2 | 7 | 1.0 | 1.475 | 5213.0417 | 16.67 | portatil |
| `25031AY140#S0020` | O2 | 8 | 1.0 | 2.0 | 10.5467 | 28.57 | portatil |
| `25040J7141#S0020` | O2 | 101 | 1.0 | 2.5 | 16.3 | 23.0 | portatil |
| `25042V7005#S0021` | CH4 | 3 | 5.6667 | 8.8667 | 12.0667 | 0.0 | desconocido |
| `2510140176#S0020` | O2 | 1 | None | None | None | None | desconocido |
