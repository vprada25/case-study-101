"""Pruebas unitarias de la interfaz de línea de comandos (task_manager.cli).

Se inyecta un ``TaskService`` en memoria y flujos ``StringIO`` para capturar
la salida sin tocar el sistema de archivos.
"""

import io
import unittest
from contextlib import redirect_stderr, redirect_stdout
from datetime import date

from task_manager.cli import EXIT_ERROR, EXIT_OK, EXIT_USAGE, format_table, main
from task_manager.models import Task, TaskStatus
from task_manager.service import TaskService

FUTURE = "2099-12-31"


class CliTestCase(unittest.TestCase):
    def setUp(self):
        self.service = TaskService()

    def run_cli(self, *argv):
        """Ejecuta la CLI y devuelve (código, stdout, stderr)."""
        out, err = io.StringIO(), io.StringIO()
        with redirect_stderr(err):  # argparse escribe los errores de uso en sys.stderr
            code = main(list(argv), service=self.service, stdout=out, stderr=err)
        return code, out.getvalue(), err.getvalue()


class TestCrear(CliTestCase):
    def test_create_minimal(self):
        code, out, err = self.run_cli("crear", "-n", "Estudiar", "-f", FUTURE)
        self.assertEqual(code, EXIT_OK)
        self.assertIn("Tarea creada con id 1", out)
        self.assertEqual(err, "")
        task = self.service.get_task(1)
        self.assertEqual(task.name, "Estudiar")
        self.assertIs(task.status, TaskStatus.PENDING)

    def test_create_with_all_options(self):
        code, _, _ = self.run_cli(
            "crear", "--nombre", "Informe", "--fecha", FUTURE,
            "--descripcion", "Caso 101", "--estado", "en_progreso",
        )
        self.assertEqual(code, EXIT_OK)
        task = self.service.get_task(1)
        self.assertEqual(task.description, "Caso 101")
        self.assertIs(task.status, TaskStatus.IN_PROGRESS)

    def test_create_invalid_date(self):
        code, out, err = self.run_cli("crear", "-n", "X", "-f", "31/12/2099")
        self.assertEqual(code, EXIT_ERROR)
        self.assertIn("Fecha inválida", err)
        self.assertEqual(out, "")
        self.assertEqual(self.service.list_tasks(), [])

    def test_create_empty_name(self):
        code, _, err = self.run_cli("crear", "-n", "  ", "-f", FUTURE)
        self.assertEqual(code, EXIT_ERROR)
        self.assertIn("nombre", err)

    def test_create_missing_required_args(self):
        code, _, err = self.run_cli("crear", "-n", "Sin fecha")
        self.assertEqual(code, EXIT_USAGE)
        self.assertIn("--fecha", err)

    def test_create_invalid_status(self):
        code, _, err = self.run_cli("crear", "-n", "X", "-f", FUTURE, "-e", "hecha")
        self.assertEqual(code, EXIT_USAGE)
        self.assertIn("Estado inválido", err)


class TestEditar(CliTestCase):
    def setUp(self):
        super().setUp()
        self.service.create_task("Original", FUTURE, "desc")

    def test_edit_fields(self):
        code, out, _ = self.run_cli("editar", "1", "-n", "Nuevo", "-e", "completada")
        self.assertEqual(code, EXIT_OK)
        self.assertIn("Tarea 1 actualizada", out)
        task = self.service.get_task(1)
        self.assertEqual(task.name, "Nuevo")
        self.assertIs(task.status, TaskStatus.COMPLETED)
        self.assertEqual(task.description, "desc")

    def test_edit_clear_description(self):
        code, _, _ = self.run_cli("editar", "1", "-d", "")
        self.assertEqual(code, EXIT_OK)
        self.assertEqual(self.service.get_task(1).description, "")

    def test_edit_without_fields(self):
        code, _, err = self.run_cli("editar", "1")
        self.assertEqual(code, EXIT_ERROR)
        self.assertIn("al menos un campo", err)

    def test_edit_missing_task(self):
        code, _, err = self.run_cli("editar", "7", "-n", "x")
        self.assertEqual(code, EXIT_ERROR)
        self.assertIn("No existe una tarea con id 7", err)

    def test_edit_invalid_id(self):
        for bad in ("abc", "0", "-3"):
            with self.subTest(id=bad):
                code, _, _ = self.run_cli("editar", bad, "-n", "x")
                self.assertEqual(code, EXIT_USAGE)


class TestEliminar(CliTestCase):
    def test_delete(self):
        self.service.create_task("Borrar", FUTURE)
        code, out, _ = self.run_cli("eliminar", "1")
        self.assertEqual(code, EXIT_OK)
        self.assertIn("Tarea 1 ('Borrar') eliminada", out)
        self.assertEqual(self.service.list_tasks(), [])

    def test_delete_missing(self):
        code, _, err = self.run_cli("eliminar", "1")
        self.assertEqual(code, EXIT_ERROR)
        self.assertIn("No existe", err)


class TestListarFiltrarVer(CliTestCase):
    def setUp(self):
        super().setUp()
        self.service.create_task("Alfa", FUTURE)
        self.service.create_task("Beta", FUTURE, status="en progreso")
        self.service.create_task("Gamma", FUTURE, status="completada")

    def test_list_all(self):
        code, out, _ = self.run_cli("listar")
        self.assertEqual(code, EXIT_OK)
        for name in ("Alfa", "Beta", "Gamma"):
            self.assertIn(name, out)
        self.assertIn("Total: 3 tarea(s)", out)

    def test_list_with_status_option(self):
        _, out, _ = self.run_cli("listar", "-e", "completada")
        self.assertIn("Gamma", out)
        self.assertNotIn("Alfa", out)

    def test_filter(self):
        code, out, _ = self.run_cli("filtrar", "pendiente")
        self.assertEqual(code, EXIT_OK)
        self.assertIn("Alfa", out)
        self.assertNotIn("Beta", out)
        self.assertIn("Total: 1 tarea(s)", out)

    def test_filter_without_results(self):
        self.service.delete_task(1)
        _, out, _ = self.run_cli("filtrar", "pendiente")
        self.assertIn("No hay tareas para mostrar", out)

    def test_filter_invalid_status(self):
        code, _, _ = self.run_cli("filtrar", "archivada")
        self.assertEqual(code, EXIT_USAGE)

    def test_show(self):
        code, out, _ = self.run_cli("ver", "2")
        self.assertEqual(code, EXIT_OK)
        self.assertIn("Nombre:      Beta", out)
        self.assertIn("Estado:      en progreso", out)

    def test_show_missing(self):
        code, _, _ = self.run_cli("ver", "99")
        self.assertEqual(code, EXIT_ERROR)


class TestGeneral(CliTestCase):
    def test_no_command_opens_interactive_menu(self):
        out = io.StringIO()
        code = main([], service=self.service, stdout=out, input_fn=lambda _: "0")
        self.assertEqual(code, EXIT_OK)
        self.assertIn("GESTOR DE TAREAS", out.getvalue())

    def test_unknown_command_is_usage_error(self):
        code, _, _ = self.run_cli("borrar-todo")
        self.assertEqual(code, EXIT_USAGE)

    def test_help_exits_ok(self):
        out = io.StringIO()
        with redirect_stdout(out):
            code = main(["--help"], service=self.service)
        self.assertEqual(code, EXIT_OK)
        self.assertIn("crear", out.getvalue())


class TestFormatTable(unittest.TestCase):
    def test_empty(self):
        self.assertEqual(format_table([]), "No hay tareas para mostrar.")

    def test_marks_overdue_tasks(self):
        tasks = [
            Task(id=1, name="Vieja", due_date=date(2000, 1, 1)),
            Task(id=2, name="Hecha", due_date=date(2000, 1, 1), status=TaskStatus.COMPLETED),
        ]
        table = format_table(tasks)
        self.assertIn("pendiente (vencida)", table)
        self.assertNotIn("completada (vencida)", table)

    def test_columns_are_aligned(self):
        tasks = [
            Task(id=1, name="Corta", due_date=date(2099, 1, 1)),
            Task(id=10, name="Un nombre bastante largo", due_date=date(2099, 1, 1)),
        ]
        lines = format_table(tasks).splitlines()
        # La columna "Vence" empieza en la misma posición en todas las filas.
        positions = {line.index("2099") for line in lines[2:4]}
        self.assertEqual(len(positions), 1)


if __name__ == "__main__":
    unittest.main()
