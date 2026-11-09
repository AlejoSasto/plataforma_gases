# Solicitud de datos y de uso del asistente

## Proveedor externo

El asistente puede usar Gemini. A ese servicio solo salen la pregunta y el resumen que devuelven las herramientas. No salen correos, nombres de personas ni rutas internas de archivos.

Antes de poner `ASSISTANT_PROVIDER=gemini` con datos de la mina hace falta la **autorización escrita de la empresa**. Hasta esa autorización, el valor por defecto es `ASSISTANT_PROVIDER=off` o un modelo local (`ollama`) en el equipo de la mina.

La clave `GEMINI_API_KEY` vive solo en `.env` del servidor.

## Qué se pide a la mina

- Confirmar los artículos del Decreto 1886 que ya están cargados con `verified=false`.
- Autorizar, o no, el envío de resúmenes al proveedor externo.
- Si no hay autorización, indicar si el equipo de bocamina puede correr un modelo local.
