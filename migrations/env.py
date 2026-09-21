"""Alembic environment — usa settings.database_url (no hardcodear)."""

from logging.config import fileConfig

from alembic import context
from sqlalchemy import engine_from_config, pool

from app.core.config import settings
from app.core.database import Base

# Importar modelos para que Base.metadata los registre (autogenerate).
from app.modules.alerts import models as alerts_models  # noqa: F401
from app.modules.audit import models as audit_models  # noqa: F401
from app.modules.ml_training import models as ml_models  # noqa: F401
from app.modules.predictions import models as predictions_models  # noqa: F401
from app.modules.roles_permissions import models as roles_models  # noqa: F401
from app.modules.sensors_ingestion import models as sensors_models  # noqa: F401
from app.modules.stakeholders import models as stakeholders_models  # noqa: F401
from app.modules.reports import models as reports_models  # noqa: F401
from app.modules.users import models as users_models  # noqa: F401
config = context.config
config.set_main_option("sqlalchemy.url", settings.database_url)

if config.config_file_name is not None:
    fileConfig(config.config_file_name)

target_metadata = Base.metadata


def run_migrations_offline() -> None:
    url = config.get_main_option("sqlalchemy.url")
    context.configure(
        url=url,
        target_metadata=target_metadata,
        literal_binds=True,
        dialect_opts={"paramstyle": "named"},
    )

    with context.begin_transaction():
        context.run_migrations()


def run_migrations_online() -> None:
    connectable = engine_from_config(
        config.get_section(config.config_ini_section, {}),
        prefix="sqlalchemy.",
        poolclass=pool.NullPool,
    )

    with connectable.connect() as connection:
        context.configure(connection=connection, target_metadata=target_metadata)

        with context.begin_transaction():
            context.run_migrations()


if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()
