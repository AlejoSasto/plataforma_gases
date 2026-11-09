# Diagnóstico G1

Generado: `2026-11-08T01:57:07.754300+00:00`

## Segmentos

- Duración en pasos: p10 1.0, p50 2.0, p90 13.0
- `lookback_steps`: **12**

## Modelos que caben

- persistencia
- ets

## Modelos excluidos

- lgbm_q: contexto mínimo documentado 30 supera w=12
- lstm: contexto mínimo documentado 30 supera w=12
- tft: contexto mínimo documentado 48 supera w=12
- chronos: contexto mínimo documentado 64 supera w=12
- chronos2: contexto mínimo documentado 64 supera w=12
- timesfm: contexto mínimo documentado 32 supera w=12
- patchtst: contexto mínimo documentado 48 supera w=12; queda fuera de la ablación
- itransformer: contexto mínimo documentado 48 supera w=12; queda fuera de la ablación
- ttm: contexto mínimo documentado 32 supera w=12; queda fuera de la ablación

## Semántica de Leyendo

No hay STEL ni TWA del instrumento para comparar.

Conclusión: **instantáneo**.

## Pliegues

- validacion: 2023-03, 2024-09 (553 pasos)
- validacion: 2024-11 (8937 pasos)
- validacion: 2024-12, 2025-08, 2025-09 (576 pasos)
- validacion: 2025-10, 2025-11 (2528 pasos)
- final_test: 2025-12 (1300 pasos)
