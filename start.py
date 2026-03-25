"""Entry point for deployment: run migrations then start bot."""
import subprocess
import sys


def _reset_alembic_version():
    """Drop alembic_version table if it references a deleted revision."""
    try:
        from bot.config import settings
        import asyncio
        import asyncpg

        async def _drop():
            conn = await asyncpg.connect(settings.database_url.replace(
                "postgresql+asyncpg://", "postgresql://", 1
            ))
            await conn.execute("DROP TABLE IF EXISTS alembic_version")
            await conn.close()

        asyncio.run(_drop())
        print("Reset alembic_version table.")
    except Exception as e:
        print(f"Warning: could not reset alembic_version: {e}")


def run():
    _reset_alembic_version()

    print("Running migrations...")
    result = subprocess.run(
        [sys.executable, "-m", "alembic", "upgrade", "head"],
        capture_output=True,
        text=True,
    )
    print(result.stdout)
    if result.returncode != 0:
        print(result.stderr)
        sys.exit(1)

    print("Starting bot...")
    from main import main
    main()


if __name__ == "__main__":
    run()
