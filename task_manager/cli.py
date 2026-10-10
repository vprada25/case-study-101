"""Interfaz de línea de comandos (CLI) del sistema de gestión de tareas.

Uso general::

    python -m task_manager [--archivo RUTA] [<comando> [opciones]]

Comandos disponibles: crear, editar, eliminar, listar, filtrar, ver.
Si no se indica ningún comando se abre el menú interactivo.
La CLI solo traduce argumentos a llamadas de ``TaskService`` y da formato a
la salida; no contiene lógica de negocio.
"""

from __future__ import annotations

import argparse
import os
import sys
from typing import Callable, Sequence, TextIO

from task_manager import __version__
from task_manager.exceptions import TaskManagerError
from task_manager.models import Task, TaskStatus
from task_manager.repository import JsonTaskRepository
from task_manager.service import TaskService

DEFAULT_FILE = "tasks.json"
ENV_FILE = "TASKS_FILE"

EXIT_OK = 0
EXIT_ERROR = 1
EXIT_USAGE = 2


# ---------------------------------------------------------------------- #
# Conversores de argumentos
# ---------------------------------------------------------------------- #
def _status_arg(value: str) -> TaskStatus:
    try:
        return TaskStatus.from_string(value)
    except ValueError as exc:
        raise argparse.ArgumentTypeError(str(exc)) from None


def _positive_int(value: str) -> int:
    try:
        number = int(value)
    except ValueError:
        raise argparse.ArgumentTypeError(f"'{value}' no es un id válido") from None
    if number <= 0:
        raise argparse.ArgumentTypeError("El id debe ser un entero positivo")
    return number


# ---------------------------------------------------------------------- #
# Formato de salida
# ---------------------------------------------------------------------- #
def format_status(task: Task) -> str:
    """Texto del estado, indicando si la tarea está vencida."""
    return f"{task.status.value} (vencida)" if task.is_overdue() else task.status.value


def format_table(tasks: list[Task]) -> str:
    """Devuelve las tareas como una tabla de texto con columnas alineadas."""
    if not tasks:
        return "No hay tareas para mostrar."
    headers = ("ID", "Nombre", "Vence", "Estado", "Descripción")
    rows = [
        (str(t.id), t.name, t.due_date.isoformat(), format_status(t), t.description)
        for t in tasks
    ]
    widths = [max(len(r[i]) for r in [headers, *rows]) for i in range(len(headers))]

    def fmt(row):
        return "  ".join(cell.ljust(w) for cell, w in zip(row, widths)).rstrip()

    lines = [fmt(headers), "  ".join("-" * w for w in widths)]
    lines.extend(fmt(r) for r in rows)
    lines.append(f"\nTotal: {len(tasks)} tarea(s)")
    return "\n".join(lines)


def format_detail(task: Task) -> str:
    """Devuelve el detalle de una tarea en formato clave: valor."""
    return "\n".join(
        [
            f"ID:          {task.id}",
            f"Nombre:      {task.name}",
            f"Descripción: {task.description or '-'}",
            f"Vence:       {task.due_date.isoformat()}",
            f"Estado:      {format_status(task)}",
        ]
    )


# ---------------------------------------------------------------------- #
# Definición de comandos
# ---------------------------------------------------------------------- #
def build_parser() -> argparse.ArgumentParser:
    """Construye el analizador de argumentos con todos los subcomandos."""
    states = ", ".join(s.value for s in TaskStatus)
    parser = argparse.ArgumentParser(
        prog="task_manager",
        description=(
            "Sistema de gestión de tareas por línea de comandos. "
            "Ejecútelo sin comando para abrir el menú interactivo."
        ),
        epilog=f"Estados válidos: {states}. Fechas en formato AAAA-MM-DD.",
    )
    parser.add_argument(
        "--archivo",
        default=None,
        help=f"archivo JSON de datos (por defecto ${ENV_FILE} o '{DEFAULT_FILE}')",
    )
    parser.add_argument("--version", action="version", version=f"%(prog)s {__version__}")
    sub = parser.add_subparsers(dest="command", metavar="<comando>")

    p = sub.add_parser("crear", help="crear una nueva tarea")
    p.add_argument("-n", "--nombre", required=True, help="nombre de la tarea")
    p.add_argument("-f", "--fecha", required=True, help="fecha de vencimiento AAAA-MM-DD")
    p.add_argument("-d", "--descripcion", default="", help="descripción de la tarea")
    p.add_argument(
        "-e", "--estado", type=_status_arg, default=TaskStatus.PENDING,
        help="estado inicial (por defecto: pendiente)",
    )
    p.set_defaults(handler=_cmd_create)

    p = sub.add_parser("editar", help="editar una tarea existente")
    p.add_argument("id", type=_positive_int, help="id de la tarea")
    p.add_argument("-n", "--nombre", help="nuevo nombre")
    p.add_argument("-f", "--fecha", help="nueva fecha de vencimiento AAAA-MM-DD")
    p.add_argument("-d", "--descripcion", help="nueva descripción ('' para borrarla)")
    p.add_argument("-e", "--estado", type=_status_arg, help="nuevo estado")
    p.set_defaults(handler=_cmd_edit)

    p = sub.add_parser("eliminar", help="eliminar una tarea")
    p.add_argument("id", type=_positive_int, help="id de la tarea")
    p.set_defaults(handler=_cmd_delete)

    p = sub.add_parser("listar", help="listar todas las tareas")
    p.add_argument("-e", "--estado", type=_status_arg, help="mostrar solo este estado")
    p.set_defaults(handler=_cmd_list)

    p = sub.add_parser("filtrar", help="filtrar tareas por estado")
    p.add_argument("estado", type=_status_arg, help=f"uno de: {states}")
    p.set_defaults(handler=_cmd_filter)

    p = sub.add_parser("ver", help="ver el detalle de una tarea")
    p.add_argument("id", type=_positive_int, help="id de la tarea")
    p.set_defaults(handler=_cmd_show)

    return parser


# ---------------------------------------------------------------------- #
# Manejadores: cada uno recibe los argumentos y el servicio, y devuelve el
# texto a imprimir.
# ---------------------------------------------------------------------- #
def _cmd_create(args: argparse.Namespace, service: TaskService) -> str:
    task = service.create_task(
        name=args.nombre,
        due_date=args.fecha,
        description=args.descripcion,
        status=args.estado,
    )
    return f"Tarea creada con id {task.id}.\n\n{format_detail(task)}"


def _cmd_edit(args: argparse.Namespace, service: TaskService) -> str:
    fields = {
        "name": args.nombre,
        "description": args.descripcion,
        "due_date": args.fecha,
        "status": args.estado,
    }
    if all(v is None for v in fields.values()):
        raise ValueError(
            "Indique al menos un campo a modificar "
            "(--nombre, --descripcion, --fecha o --estado)"
        )
    task = service.update_task(args.id, **fields)
    return f"Tarea {task.id} actualizada.\n\n{format_detail(task)}"


def _cmd_delete(args: argparse.Namespace, service: TaskService) -> str:
    task = service.delete_task(args.id)
    return f"Tarea {task.id} ('{task.name}') eliminada."


def _cmd_list(args: argparse.Namespace, service: TaskService) -> str:
    tasks = service.filter_by_status(args.estado) if args.estado else service.list_tasks()
    return format_table(tasks)


def _cmd_filter(args: argparse.Namespace, service: TaskService) -> str:
    return format_table(service.filter_by_status(args.estado))


def _cmd_show(args: argparse.Namespace, service: TaskService) -> str:
    return format_detail(service.get_task(args.id))


# ---------------------------------------------------------------------- #
# Punto de entrada
# ---------------------------------------------------------------------- #
def main(
    argv: Sequence[str] | None = None,
    service: TaskService | None = None,
    stdout: TextIO | None = None,
    stderr: TextIO | None = None,
    input_fn: Callable[[str], str] = input,
) -> int:
    """Ejecuta la CLI y devuelve el código de salida.

    ``service``, ``stdout``, ``stderr`` e ``input_fn`` se pueden inyectar para
    facilitar las pruebas; si no se indican, se usa el archivo JSON
    configurado y la entrada/salida estándar del proceso.
    """
    stdout = stdout or sys.stdout
    stderr = stderr or sys.stderr
    parser = build_parser()
    try:
        args = parser.parse_args(argv)
    except SystemExit as exc:  # argparse termina con --help, --version o error de uso
        return int(exc.code or 0)

    try:
        if service is None:
            path = args.archivo or os.environ.get(ENV_FILE) or DEFAULT_FILE
            service = TaskService(JsonTaskRepository(path))
        if args.command is None:
            # Sin subcomando: modo menú. Import diferido para evitar un
            # import circular (interactive reutiliza el formato de este módulo).
            from task_manager.interactive import InteractiveApp

            return InteractiveApp(service, input_fn=input_fn, output=stdout).run()
        output = args.handler(args, service)
    except (TaskManagerError, ValueError) as exc:
        print(f"Error: {exc}", file=stderr)
        return EXIT_ERROR

    print(output, file=stdout)
    return EXIT_OK
