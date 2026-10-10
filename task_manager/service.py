"""Lógica de negocio: operaciones sobre las tareas.

``TaskService`` mantiene las tareas en un diccionario indexado por id, lo que
permite búsquedas, ediciones y eliminaciones en O(1). Después de cada
operación que modifica datos, persiste la colección mediante el repositorio.
"""

from __future__ import annotations

from dataclasses import replace
from datetime import date

from task_manager.exceptions import TaskNotFoundError
from task_manager.models import Task, TaskStatus, parse_date
from task_manager.repository import InMemoryTaskRepository, TaskRepository


class TaskService:
    """Casos de uso del sistema: crear, editar, eliminar, listar y filtrar."""

    def __init__(self, repository: TaskRepository | None = None) -> None:
        self._repository = repository or InMemoryTaskRepository()
        self._tasks: dict[int, Task] = {t.id: t for t in self._repository.load()}
        # El siguiente id continúa a partir del mayor existente, de modo que
        # nunca se reutiliza el id de una tarea eliminada en la misma sesión.
        self._next_id = max(self._tasks, default=0) + 1

    # ------------------------------------------------------------------ #
    # Operaciones de escritura
    # ------------------------------------------------------------------ #
    def create_task(
        self,
        name: str,
        due_date: str | date,
        description: str = "",
        status: str | TaskStatus = TaskStatus.PENDING,
    ) -> Task:
        """Crea una tarea nueva y la devuelve con su id asignado."""
        task = Task(
            id=self._next_id,
            name=name,
            description=description,
            due_date=parse_date(due_date),
            status=status,
        )
        self._tasks[task.id] = task
        self._next_id += 1
        self._persist()
        return task

    def update_task(
        self,
        task_id: int,
        *,
        name: str | None = None,
        description: str | None = None,
        due_date: str | date | None = None,
        status: str | TaskStatus | None = None,
    ) -> Task:
        """Edita los campos indicados de una tarea existente.

        Solo se modifican los argumentos distintos de ``None``. La nueva
        versión se valida completa antes de reemplazar a la anterior, por lo
        que si algún valor es inválido la tarea original queda intacta.
        """
        current = self.get_task(task_id)
        changes = {
            key: value
            for key, value in {
                "name": name,
                "description": description,
                "due_date": due_date,
                "status": status,
            }.items()
            if value is not None
        }
        updated = replace(current, **changes)  # dispara __post_init__ (validación)
        self._tasks[task_id] = updated
        self._persist()
        return updated

    def delete_task(self, task_id: int) -> Task:
        """Elimina una tarea y devuelve la tarea eliminada."""
        task = self.get_task(task_id)
        del self._tasks[task_id]
        self._persist()
        return task

    # ------------------------------------------------------------------ #
    # Operaciones de lectura
    # ------------------------------------------------------------------ #
    def get_task(self, task_id: int) -> Task:
        """Devuelve la tarea con el id indicado o lanza ``TaskNotFoundError``."""
        try:
            return self._tasks[task_id]
        except KeyError:
            raise TaskNotFoundError(task_id) from None

    def list_tasks(self) -> list[Task]:
        """Devuelve todas las tareas ordenadas por id."""
        return [self._tasks[k] for k in sorted(self._tasks)]

    def filter_by_status(self, status: str | TaskStatus) -> list[Task]:
        """Devuelve las tareas cuyo estado coincide con ``status``."""
        if isinstance(status, str):
            status = TaskStatus.from_string(status)
        return [t for t in self.list_tasks() if t.status is status]

    # ------------------------------------------------------------------ #
    def _persist(self) -> None:
        self._repository.save(self.list_tasks())
