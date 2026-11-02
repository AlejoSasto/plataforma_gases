# Prueba de aceptación (OE4 / Plan 20 F6)

Protocolo para validar la plataforma con 3–5 personas de la mina (operador de sala, supervisor de seguridad y gerencia).

**Campo pendiente:** las 3–5 sesiones con personas reales y el SUS ≥ 75 no se pueden cerrar desde el código. El 2026-11-01 se corrió un **ensayo técnico** (admin, Playwright + navegador) de las cinco tareas; no es SUS ni sustituye el visto de campo.

## Meta

- Éxito por tarea ≥ 90 %.
- SUS (System Usability Scale) ≥ 75.

## Tareas guiadas (máx. 5 min cada una)

| # | Consigna | Pantalla | Éxito |
|---|----------|----------|--------|
| 1 | ¿Está todo bien ahora? | Hoy `/` | Identifica el banner (Todo normal / zonas en atención) |
| 2 | ¿Qué zona necesita atención y por qué? | Hoy o Avisos | Nombra zona, gas y la frase de por qué |
| 3 | Marca que viste el aviso | Avisos | Pulsa «Ya lo vi» y ve el cambio de estado |
| 4 | ¿Qué tan seguido acierta el sistema? | Confiabilidad | Lee la frase de aciertos a tiempo, no un porcentaje crudo |
| 5 | Descarga el informe de la semana | Informes | Genera y descarga el archivo |

Se registran: éxito (sí/no), tiempo, errores, comentarios.

## Cuestionario SUS (10 ítems, 1–5)

1. Creo que me gustaría usar este sistema con frecuencia.
2. El sistema es innecesariamente complejo.
3. El sistema es fácil de usar.
4. Necesitaría apoyo técnico para usar el sistema.
5. Las funciones están bien integradas.
6. Hay demasiada inconsistencia.
7. La mayoría de la gente aprendería a usarlo muy rápido.
8. El sistema es engorroso.
9. Me sentí seguro usándolo.
10. Tuve que aprender muchas cosas antes de poder usarlo.

Puntaje: para ítems impares `(x-1)`, para pares `(5-x)`; suma × 2,5. Rango 0–100.

## Registro de sesiones

| Fecha | Perfil | T1 | T2 | T3 | T4 | T5 | SUS | Notas |
|-------|--------|----|----|----|----|----|-----|-------|
| 2026-11-01 | ensayo técnico (admin DEV) | sí | sí | sí | sí | sí | n/a | Banner «2 zonas requieren atención»; aviso Mina Norte CO Evacuar; «Ya lo vi» pasó a Vistos (18 abiertos → 2 vistos); Confiabilidad muestra frase honesta sin % crudo; informe de avisos 200 OK / 2405 B. **No es sesión en mina.** |
| — | operador | | | | | | | Pendiente de campo |
| — | supervisor | | | | | | | Pendiente de campo |
| — | gerencia | | | | | | | Pendiente de campo |

Hallazgos → cambios → repetir las tareas fallidas. Cada ronda se anota en `planes/BITACORA_BUCLE.md`.
