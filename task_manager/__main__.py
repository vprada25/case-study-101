"""Permite ejecutar el sistema con ``python -m task_manager``."""

import sys

from task_manager.cli import main

if __name__ == "__main__":
    sys.exit(main())
