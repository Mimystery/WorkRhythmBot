"""Entry point for deployment: run migrations then start bot."""
import subprocess
import sys


def run():
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
