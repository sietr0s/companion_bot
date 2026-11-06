"""Apply production migrations; safe mode initializes its own SQLite schema at startup."""

import subprocess

from src.core.config import settings


def main() -> None:
    if not settings.SAFE_MODE:
        subprocess.run(["alembic", "upgrade", "head"], check=True)


if __name__ == "__main__":
    main()
