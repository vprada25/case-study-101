"""Punto de entrada rápido: ``python3 main.py`` abre el menú interactivo.

También acepta los mismos comandos que ``python3 -m task_manager``, por
ejemplo ``python3 main.py listar``.
"""

import sys

from task_manager.cli import main

if __name__ == "__main__":
    sys.exit(main())
