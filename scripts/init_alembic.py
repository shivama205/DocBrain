import sys
import os
import subprocess
from pathlib import Path

def init_alembic():
    """Initialize Alembic and create the first migration"""
    try:
        # Get the project root directory
        project_root = Path(__file__).parent.parent
        alembic_dir = project_root / "alembic"

        # Create alembic directory if it doesn't exist
        if not alembic_dir.exists():
            os.makedirs(alembic_dir)
            print("Created alembic directory")

        # Initialize alembic
        subprocess.run(["alembic", "init", "alembic"], cwd=project_root, check=True)
        print("Initialized Alembic")

        # Create the first migration
        subprocess.run(
            ["alembic", "revision", "--autogenerate", "-m", "Initial migration"],
            cwd=project_root,
            check=True
        )
        print("Created initial migration")

        # Apply the migration
        subprocess.run(["alembic", "upgrade", "head"], cwd=project_root, check=True)
        print("Applied initial migration")

    except subprocess.CalledProcessError as e:
        print(f"Error running Alembic command: {e}")
        sys.exit(1)
    except Exception as e:
        print(f"Error initializing Alembic: {e}")
        sys.exit(1)

if __name__ == "__main__":
    init_alembic() 