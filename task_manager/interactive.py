"""Modo interactivo (menú) del sistema de gestión de tareas.

Se activa al ejecutar la aplicación sin subcomando::

    python3 main.py
    python3 -m task_manager

Muestra un menú numerado y solicita los datos paso a paso, validando cada
entrada antes de continuar. Igual que la CLI, delega toda la lógica de
negocio en ``TaskService``.
"""

from __future__ import annotations

import sys
from typing import Callable, TextIO

from task_manager.cli import format_detail, format_table
from task_manager.exceptions import TaskManagerError
from task_manager.models import TaskStatus, parse_date
from task_manager.service import TaskService

InputFn = Callable[[str], str]


class _Exit(Exception):
    """Señal interna para terminar el menú (opción salir, Ctrl+C o Ctrl+D)."""


class InteractiveApp:
    """Bucle de menú que interactúa con el usuario por consola.

    ``input_fn`` y ``output`` se pueden inyectar para automatizar las pruebas.
    """

    STATUSES = list(TaskStatus)

    def __init__(
        self,
        service: TaskService,
        input_fn: InputFn = input,
        output: TextIO | None = None,
    ) -> None:
        self.service = service
        self._input = input_fn
        self.out = output or sys.stdout
        # Cada opción del menú: (tecla, texto, acción)
        self.options: list[tuple[str, str, Callable[[], None]]] = [
            ("1", "Crear tarea", self.create),
            ("2", "Editar tarea", self.edit),
            ("3", "Eliminar tarea", self.delete),
            ("4", "Listar tareas", self.list_all),
            ("5", "Filtrar por estado", self.filter),
            ("6", "Ver detalle de una tarea", self.show),
            ("0", "Salir", self.quit),
        ]

    # ------------------------------------------------------------------ #
    # Bucle principal
    # ------------------------------------------------------------------ #
    def run(self) -> int:
        self.print("Bienvenido al Sistema de Gestión de Tareas")
        actions = {key: action for key, _, action in self.options}
        while True:
            try:
                self.print_menu()
                choice = self.ask("Seleccione una opción: ").strip()
                action = actions.get(choice)
                if action is None:
                    self.print("Opción no válida. Intente de nuevo.")
                    continue
                action()
            except _Exit:
                self.print("\n¡Hasta luego!")
                return 0
            except (TaskManagerError, ValueError) as exc:
                # Errores de negocio: se informan y se vuelve al menú.
                self.print(f"Error: {exc}")

    def print_menu(self) -> None:
        tasks = self.service.list_tasks()
        counts = {s: sum(t.status is s for t in tasks) for s in TaskStatus}
        summary = " | ".join(f"{s.value}: {counts[s]}" for s in TaskStatus)
        self.print("\n" + "=" * 44)
        self.print("  GESTOR DE TAREAS")
        self.print(f"  {len(tasks)} tarea(s) — {summary}")
        self.print("=" * 44)
        for key, label, _ in self.options:
            self.print(f"  {key}. {label}")

    # ------------------------------------------------------------------ #
    # Acciones del menú
    # ------------------------------------------------------------------ #
    def create(self) -> None:
        self.print("\n--- Nueva tarea ---")
        name = self.ask_required("Nombre: ")
        description = self.ask("Descripción (opcional): ").strip()
        due_date = self.ask_date("Fecha de vencimiento (AAAA-MM-DD): ")
        status = self.ask_status(default=TaskStatus.PENDING)
        task = self.service.create_task(name, due_date, description, status)
        self.print(f"\n✔ Tarea creada con id {task.id}.\n")
        self.print(format_detail(task))

    def edit(self) -> None:
        task = self.ask_existing_task("editar")
        if task is None:
            return
        self.print("\nPulse Enter para conservar el valor actual.")
        name = self.ask(f"Nombre [{task.name}]: ").strip() or None
        description = self.ask(
            f"Descripción [{task.description or '-'}] ('-' para borrarla): "
        ).strip()
        description = "" if description == "-" else (description or None)
        due_date = self.ask_date(
            f"Fecha de vencimiento [{task.due_date.isoformat()}]: ", optional=True
        )
        status = self.ask_status(default=task.status, keep_current=True)
        updated = self.service.update_task(
            task.id,
            name=name,
            description=description,
            due_date=due_date,
            status=status,
        )
        self.print(f"\n✔ Tarea {updated.id} actualizada.\n")
        self.print(format_detail(updated))

    def delete(self) -> None:
        task = self.ask_existing_task("eliminar")
        if task is None:
            return
        if self.confirm(f"¿Eliminar la tarea {task.id} ('{task.name}')? (s/n): "):
            self.service.delete_task(task.id)
            self.print(f"✔ Tarea {task.id} eliminada.")
        else:
            self.print("Operación cancelada.")

    def list_all(self) -> None:
        self.print()
        self.print(format_table(self.service.list_tasks()))

    def filter(self) -> None:
        status = self.ask_status()
        self.print()
        self.print(format_table(self.service.filter_by_status(status)))

    def show(self) -> None:
        task = self.ask_existing_task("ver")
        if task is not None:
            self.print()
            self.print(format_detail(task))

    def quit(self) -> None:
        raise _Exit

    # ------------------------------------------------------------------ #
    # Utilidades de entrada/salida con validación
    # ------------------------------------------------------------------ #
    def print(self, text: str = "") -> None:
        print(text, file=self.out)

    def ask(self, prompt: str) -> str:
        """Lee una línea; Ctrl+C o fin de entrada terminan el programa."""
        self.out.write(prompt)
        self.out.flush()
        try:
            return self._input("")
        except (EOFError, KeyboardInterrupt):
            raise _Exit from None

    def ask_required(self, prompt: str) -> str:
        while True:
            value = self.ask(prompt).strip()
            if value:
                return value
            self.print("Este campo es obligatorio.")

    def ask_date(self, prompt: str, optional: bool = False) -> str | None:
        """Pide una fecha válida; si ``optional`` y se deja vacía, devuelve None."""
        while True:
            value = self.ask(prompt).strip()
            if optional and not value:
                return None
            try:
                return parse_date(value).isoformat()
            except ValueError as exc:
                self.print(str(exc))

    def ask_status(
        self, default: TaskStatus | None = None, keep_current: bool = False
    ) -> TaskStatus | None:
        """Muestra los estados numerados y devuelve el elegido.

        Con ``default``, pulsar Enter lo selecciona. Si ``keep_current`` es
        verdadero, Enter devuelve ``None`` (sin cambios) en vez del valor.
        """
        self.print("Estados:")
        for i, status in enumerate(self.STATUSES, start=1):
            mark = " (actual)" if keep_current and status is default else ""
            self.print(f"  {i}. {status.value}{mark}")
        hint = f" [Enter = {default.value}]" if default else ""
        while True:
            value = self.ask(f"Seleccione un estado{hint}: ").strip()
            if not value and default is not None:
                return None if keep_current else default
            if value.isdigit() and 1 <= int(value) <= len(self.STATUSES):
                return self.STATUSES[int(value) - 1]
            try:
                return TaskStatus.from_string(value)
            except ValueError:
                self.print(f"Opción no válida. Elija un número del 1 al {len(self.STATUSES)}.")

    def ask_existing_task(self, verb: str):
        """Muestra las tareas y pide el id de una existente (None si no hay)."""
        tasks = self.service.list_tasks()
        if not tasks:
            self.print("\nNo hay tareas registradas.")
            return None
        self.print()
        self.print(format_table(tasks))
        while True:
            value = self.ask(f"\nId de la tarea a {verb} (Enter para volver): ").strip()
            if not value:
                return None
            if not value.isdigit():
                self.print("Ingrese un número de id válido.")
                continue
            try:
                return self.service.get_task(int(value))
            except TaskManagerError as exc:
                self.print(str(exc))

    def confirm(self, prompt: str) -> bool:
        return self.ask(prompt).strip().lower() in ("s", "si", "sí", "y", "yes")
