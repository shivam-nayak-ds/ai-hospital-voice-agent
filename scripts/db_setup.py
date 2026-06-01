import subprocess
import sys

from src.utils.logger import custom_logger as logger


def run_command(command: list[str]):
    logger.info(f"Running: {' '.join(command)}")
    subprocess.run(command, check=True)


def setup_database():
    run_command([sys.executable, "-m", "alembic", "upgrade", "head"])
    run_command([sys.executable, "-m", "scripts.db_seed"])
    logger.success("Database setup completed: migrations applied and seed data loaded.")


if __name__ == "__main__":
    setup_database()

