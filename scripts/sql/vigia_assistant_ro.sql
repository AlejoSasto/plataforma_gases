-- Usuario de PostgreSQL de solo lectura para el asistente (Plan 26).
-- Ejecutar como superusuario. La contraseña NO se guarda en este archivo:
-- cámbiala al crear el rol y pon la URL en ASSISTANT_DATABASE_URL, solo en .env.
-- generar_informe sigue usando el servicio de reportes (escritura de archivos), no este rol.

DO $$
BEGIN
  IF NOT EXISTS (SELECT 1 FROM pg_roles WHERE rolname = 'vigia_assistant_ro') THEN
    CREATE ROLE vigia_assistant_ro LOGIN;
  END IF;
END
$$;

GRANT USAGE ON SCHEMA public TO vigia_assistant_ro;
GRANT SELECT ON
  gas_readings,
  reading_grid,
  sensors,
  sites,
  instruments,
  alerts,
  alert_outcomes,
  threshold_events,
  gas_types,
  normative_thresholds,
  app_settings,
  benchmark_runs,
  forecasts,
  forecast_quantiles
TO vigia_assistant_ro;
