"""A failed migration must prevent the application from starting."""

import os
import subprocess
import sys
from pathlib import Path

import pytest

ENTRYPOINT = Path(__file__).resolve().parents[1] / "scripts/docker-entrypoint.sh"


@pytest.mark.parametrize("migration_status", [0, 7])
@pytest.mark.parametrize("safe_mode", [False, True])
def test_migrations_run_before_application_and_fail_closed(tmp_path, migration_status, safe_mode):
    alembic = tmp_path / "alembic"
    alembic.write_text(
        f'#!/bin/sh\nprintf "%s\\n" "$*" > "$MIGRATION_LOG"\nexit {migration_status}\n'
    )
    alembic.chmod(0o755)
    migration_log = tmp_path / "migration.log"
    application_log = tmp_path / "application.log"
    result = subprocess.run(
        ["sh", str(ENTRYPOINT), "sh", "-c", 'printf started > "$APPLICATION_LOG"'],
        env={
            **os.environ,
            "PATH": f"{tmp_path}:{Path(sys.executable).parent}:{os.environ['PATH']}",
            "SAFE_MODE": str(safe_mode),
            "MIGRATION_LOG": str(migration_log),
            "APPLICATION_LOG": str(application_log),
        },
        check=False,
    )
    if safe_mode:
        assert not migration_log.exists()
    else:
        assert migration_log.read_text() == "upgrade head\n"
    should_start = safe_mode or migration_status == 0
    assert (result.returncode == 0) == should_start
    assert application_log.exists() == should_start
