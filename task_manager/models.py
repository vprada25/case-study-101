"""Modelo de dominio del sistema de gestión de tareas.

Define la entidad ``Task`` y la enumeración ``TaskStatus`` con los estados
permitidos. Este módulo no depende de ningún otro módulo del sistema.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import date
from enum import Enum


class TaskStatus(Enum):
    """Estados posibles de una tarea."""

    PENDING = "pendiente"
    IN_PROGRESS = "en progreso"
    COMPLETED = "completada"

    @classmethod
    def from_string(cls, value: str) -> "TaskStatus":
        """Convierte un texto ingresado por el usuario en un ``TaskStatus``.

        Es tolerante a mayúsculas, espacios extremos y guiones bajos, de modo
        que ``"En_Progreso"`` y ``"en progreso"`` son equivalentes.

        Raises:
            ValueError: si el texto no corresponde a ningún estado válido.
        """
        normalized = value.strip().lower().replace("_", " ").replace("-", " ")
        for status in cls:
            if status.value == normalized:
                return status
        valid = ", ".join(s.value for s in cls)
        raise ValueError(f"Estado inválido: '{value}'. Valores permitidos: {valid}")


def parse_date(value: str | date) -> date:
    """Convierte una fecha en formato ISO (AAAA-MM-DD) a ``datetime.date``.

    Raises:
        ValueError: si el formato de la fecha no es válido.
    """
    if isinstance(value, date):
        return value
    try:
        return date.fromisoformat(value.strip())
    except (ValueError, AttributeError) as exc:
        raise ValueError(
            f"Fecha inválida: '{value}'. Use el formato AAAA-MM-DD"
        ) from exc


@dataclass
class Task:
    """Representa una tarea del sistema.

    Attributes:
        id: identificador único asignado por el servicio.
        name: nombre corto de la tarea (obligatorio).
        description: descripción detallada (opcional).
        due_date: fecha de vencimiento.
        status: estado actual; por defecto ``PENDING``.
    """

    id: int
    name: str
    due_date: date
    description: str = ""
    status: TaskStatus = field(default=TaskStatus.PENDING)

    def __post_init__(self) -> None:
        # Normaliza y valida los datos al construir la instancia, para que
        # nunca exista una Task en estado inconsistente.
        self.name = self._validate_name(self.name)
        self.description = (self.description or "").strip()
        self.due_date = parse_date(self.due_date)
        if isinstance(self.status, str):
            self.status = TaskStatus.from_string(self.status)
        if not isinstance(self.status, TaskStatus):
            raise ValueError(f"Estado inválido: {self.status!r}")

    @staticmethod
    def _validate_name(name: str) -> str:
        if not isinstance(name, str) or not name.strip():
            raise ValueError("El nombre de la tarea no puede estar vacío")
        return name.strip()

    def is_overdue(self, today: date | None = None) -> bool:
        """Indica si la tarea está vencida y aún no se ha completado."""
        today = today or date.today()
        return self.status is not TaskStatus.COMPLETED and self.due_date < today

    def to_dict(self) -> dict:
        """Serializa la tarea a un diccionario compatible con JSON."""
        return {
            "id": self.id,
            "name": self.name,
            "description": self.description,
            "due_date": self.due_date.isoformat(),
            "status": self.status.value,
        }

    @classmethod
    def from_dict(cls, data: dict) -> "Task":
        """Reconstruye una tarea a partir de un diccionario (p. ej. JSON)."""
        return cls(
            id=int(data["id"]),
            name=data["name"],
            description=data.get("description", ""),
            due_date=parse_date(data["due_date"]),
            status=TaskStatus.from_string(data.get("status", TaskStatus.PENDING.value)),
        )
