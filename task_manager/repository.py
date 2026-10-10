"""Capa de almacenamiento de tareas (patrón Repositorio).

El servicio solo depende de la interfaz ``TaskRepository``; así se puede
cambiar el mecanismo de almacenamiento (memoria, archivo, base de datos)
sin modificar la lógica de negocio.
"""

from __future__ import annotations

from abc import ABC, abstractmethod

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
