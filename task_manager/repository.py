"""Capa de almacenamiento de tareas (patrón Repositorio).

El servicio solo depende de la interfaz ``TaskRepository``; así se puede
cambiar el mecanismo de almacenamiento (memoria, archivo, base de datos)
sin modificar la lógica de negocio.
"""

from __future__ import annotations

import json
import os
import tempfile
from abc import ABC, abstractmethod
from pathlib import Path

from task_manager.exceptions import StorageError
from task_manager.models import Task


class TaskRepository(ABC):
    """Interfaz de almacenamiento: cargar y guardar la colección completa."""

    @abstractmethod
    def load(self) -> list[Task]:
        """Devuelve todas las tareas almacenadas."""

    @abstractmethod
    def save(self, tasks: list[Task]) -> None:
        """Persiste la colección completa de tareas."""


class InMemoryTaskRepository(TaskRepository):
    """Repositorio en memoria. Útil para pruebas y ejecuciones efímeras."""

    def __init__(self, tasks: list[Task] | None = None) -> None:
        self._tasks: list[Task] = list(tasks or [])

    def load(self) -> list[Task]:
        return list(self._tasks)

    def save(self, tasks: list[Task]) -> None:
        self._tasks = list(tasks)


class JsonTaskRepository(TaskRepository):
    """Repositorio que persiste las tareas en un archivo JSON.

    Formato del archivo::

        {
          "version": 1,
          "tasks": [
            {"id": 1, "name": "...", "description": "...",
             "due_date": "AAAA-MM-DD", "status": "pendiente"}
          ]
        }
    """

    FORMAT_VERSION = 1

    def __init__(self, path: str | Path) -> None:
        self.path = Path(path)

    def load(self) -> list[Task]:
        # Si el archivo aún no existe (primera ejecución) no hay tareas.
        if not self.path.exists():
            return []
        try:
            with self.path.open(encoding="utf-8") as fh:
                data = json.load(fh)
            return [Task.from_dict(item) for item in data["tasks"]]
        except (OSError, json.JSONDecodeError, KeyError, TypeError, ValueError) as exc:
            # No se sobrescribe un archivo dañado: se informa al usuario para
            # evitar pérdida de datos.
            raise StorageError(
                f"No se pudo leer el archivo de tareas '{self.path}': {exc}"
            ) from exc

    def save(self, tasks: list[Task]) -> None:
        payload = {
            "version": self.FORMAT_VERSION,
            "tasks": [task.to_dict() for task in tasks],
        }
        try:
            self.path.parent.mkdir(parents=True, exist_ok=True)
            # Escritura atómica: se escribe en un archivo temporal del mismo
            # directorio y luego se reemplaza el original. Si el proceso se
            # interrumpe a mitad de la escritura, el archivo previo sigue íntegro.
            fd, tmp_name = tempfile.mkstemp(
                dir=self.path.parent, prefix=f".{self.path.name}.", suffix=".tmp"
            )
            try:
                with os.fdopen(fd, "w", encoding="utf-8") as fh:
                    json.dump(payload, fh, ensure_ascii=False, indent=2)
                    fh.write("\n")
                os.replace(tmp_name, self.path)
            except BaseException:
                Path(tmp_name).unlink(missing_ok=True)
                raise
        except OSError as exc:
            raise StorageError(
                f"No se pudo guardar el archivo de tareas '{self.path}': {exc}"
            ) from exc
