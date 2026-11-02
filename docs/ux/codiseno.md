# Acta de co-diseño (Plan 18 · F1)

**Fecha:** 2026-11-01  
**Participantes previstos:** operadores de mina, jefe de seguridad, dirección del proyecto.  
**Material:** bocetos de Hoy (P2), detalle de aviso (P4) y confiabilidad (P8).

## Decisiones de lenguaje

- Se responde en 3 segundos: ¿estamos bien ahora? ¿qué viene? ¿qué hay que hacer?
- Palabras de estado: Normal, Vigilar, Actuar ya, Evacuar, Sin datos. Cada una lleva color, ícono y texto.
- No se nombra el modelo en operación. Si no hay pronóstico: “Por ahora mostramos solo lo que marcan los sensores”.
- Aviso anticipado vs confirmado en frases cortas. Botones: “Ya lo vi” y “Cerrar aviso”.
- Confiabilidad en frases (“de cada 10…”, “minutos antes”), nunca recall/RMSE en esa pantalla.

## Ajustes a `copy.py`

Los textos canónicos viven en `app/shared/copy.py`. Esta acta queda como evidencia de intención; la sesión presencial con operadores se documentará aquí cuando ocurra (pendiente humano).

## Pendiente humano

Revisión conjunta de P2, P4 y P8 con el jefe de seguridad antes de congelar textos de producción.
