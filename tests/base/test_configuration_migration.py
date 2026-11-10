"""New configuration tables migrate existing databases without touching business data."""

import importlib.util
from pathlib import Path

import pytest
import sqlalchemy as sa
from alembic.migration import MigrationContext
from alembic.operations import Operations


@pytest.mark.parametrize("preexisting", [False, True])
def test_all_module_configuration_tables_upgrade_and_downgrade(preexisting):
    path = Path(__file__).resolve().parents[2] / "alembic/versions/20261110_module_configuration.py"
    spec = importlib.util.spec_from_file_location("module_configuration_migration", path)
    migration = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(migration)
    engine = sa.create_engine("sqlite://")
    with engine.begin() as connection:
        connection.execute(sa.text("CREATE TABLE business_data (value TEXT)"))
        connection.execute(sa.text("INSERT INTO business_data VALUES ('preserved')"))
        migration.op = Operations(MigrationContext.configure(connection))
        migration.upgrade()
        if preexisting:
            connection.execute(
                sa.text(
                    "INSERT INTO memory_configuration (id,revision,overrides) VALUES (1,7,'{}')"
                )
            )
            migration.upgrade()
            assert (
                connection.execute(
                    sa.text("SELECT revision FROM memory_configuration")
                ).scalar_one()
                == 7
            )
        assert set(migration.TABLES) <= set(sa.inspect(connection).get_table_names())
        with pytest.raises(sa.exc.IntegrityError):
            connection.execute(
                sa.text("INSERT INTO users_configuration (id,revision,overrides) VALUES (2,0,'{}')")
            )
        migration.downgrade()
        assert not set(migration.TABLES) & set(sa.inspect(connection).get_table_names())
        assert (
            connection.execute(sa.text("SELECT value FROM business_data")).scalar_one()
            == "preserved"
        )
    engine.dispose()
