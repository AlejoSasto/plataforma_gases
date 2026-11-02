SELECT 'CREATE DATABASE proyecto_gases_test'
WHERE NOT EXISTS (SELECT FROM pg_database WHERE datname = 'proyecto_gases_test')\gexec
GRANT ALL PRIVILEGES ON DATABASE proyecto_gases_test TO postgres;
