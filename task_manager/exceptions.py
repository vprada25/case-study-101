"""Excepciones propias del sistema de gestión de tareas."""


class TaskManagerError(Exception):
    """Excepción base de la aplicación."""


class TaskNotFoundError(TaskManagerError):
    """Se lanza cuando no existe una tarea con el identificador solicitado."""

    def __init__(self, task_id: int) -> None:
        super().__init__(f"No existe una tarea con id {task_id}")
        self.task_id = task_id


class StorageError(TaskManagerError):
    """Se lanza cuando el archivo de datos no se puede leer o escribir."""
