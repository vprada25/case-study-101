"""Pruebas de integración del sistema de gestión de tareas.

A diferencia de las pruebas unitarias, aquí no se inyectan dobles en memoria:
se ejercitan juntas todas las capas reales

    CLI / menú  ->  TaskService  ->  JsonTaskRepository  ->  archivo JSON

Hay dos niveles:

* ``TestCliWithJsonFile``: invoca ``main()`` varias veces sobre el mismo
  archivo, simulando ejecuciones sucesivas del programa.
* ``TestEndToEndProcess``: lanza el programa como un proceso independiente
  (``python -m task_manager`` y ``python main.py``), exactamente como lo haría
  un usuario desde la terminal.
"""

import io
import json
import os
import subprocess
import sys
import tempfile
import unittest
from contextlib import redirect_stderr
from pathlib import Path

from task_manager.cli import EXIT_ERROR, EXIT_OK, main
from task_manager.models import TaskStatus
from task_manager.repository import JsonTaskRepository
from task_manager.service import TaskService

PROJECT_ROOT = Path(__file__).resolve().parent.parent
FUTURE = "2099-12-31"


class TempFileTestCase(unittest.TestCase):
    def setUp(self):
        self._tmp = tempfile.TemporaryDirectory()
        self.data_file = Path(self._tmp.name) / "tasks.json"

    def tearDown(self):
        self._tmp.cleanup()

    def read_file(self):
        return json.loads(self.data_file.read_text(encoding="utf-8"))


class TestServiceWithJsonRepository(TempFileTestCase):
    """Integración servicio + persistencia: los datos sobreviven a reinicios."""

    def test_state_survives_new_service_instances(self):
        first = TaskService(JsonTaskRepository(self.data_file))
        first.create_task("A", FUTURE)
        first.create_task("B", FUTURE)
        first.delete_task(2)

        second = TaskService(JsonTaskRepository(self.data_file))
        self.assertEqual([t.name for t in second.list_tasks()], ["A"])
        second.update_task(1, status="completada")
        # El id 2 se eliminó, pero el siguiente id se calcula sobre lo
        # persistido: nunca colisiona con una tarea existente.
        self.assertEqual(second.create_task("C", FUTURE).id, 2)

        third = TaskService(JsonTaskRepository(self.data_file))
        self.assertIs(third.get_task(1).status, TaskStatus.COMPLETED)
        self.assertEqual(len(third.filter_by_status("pendiente")), 1)


class TestCliWithJsonFile(TempFileTestCase):
    """Integración CLI + servicio + archivo, sin dobles de prueba."""

    def cli(self, *argv):
        out, err = io.StringIO(), io.StringIO()
        with redirect_stderr(err):
            code = main(["--archivo", str(self.data_file), *argv], stdout=out, stderr=err)
        return code, out.getvalue(), err.getvalue()

    def test_full_lifecycle(self):
        # 1. Crear tres tareas en ejecuciones independientes
        self.assertEqual(self.cli("crear", "-n", "Analizar", "-f", FUTURE)[0], EXIT_OK)
        self.assertEqual(
            self.cli("crear", "-n", "Diseñar", "-f", FUTURE, "-e", "en progreso")[0],
            EXIT_OK,
        )
        self.assertEqual(self.cli("crear", "-n", "Probar", "-f", FUTURE)[0], EXIT_OK)
        self.assertEqual(len(self.read_file()["tasks"]), 3)

        # 2. Editar: completar la primera
        self.assertEqual(self.cli("editar", "1", "-e", "completada")[0], EXIT_OK)

        # 3. Filtrar refleja el cambio persistido
        _, out, _ = self.cli("filtrar", "completada")
        self.assertIn("Analizar", out)
        self.assertIn("Total: 1 tarea(s)", out)

        # 4. Eliminar y verificar el archivo
        self.assertEqual(self.cli("eliminar", "2")[0], EXIT_OK)
        names = [t["name"] for t in self.read_file()["tasks"]]
        self.assertEqual(names, ["Analizar", "Probar"])

        # 5. Listar muestra el estado final
        _, out, _ = self.cli("listar")
        self.assertIn("Total: 2 tarea(s)", out)
        self.assertNotIn("Diseñar", out)

    def test_failed_operation_does_not_modify_file(self):
        self.cli("crear", "-n", "Estable", "-f", FUTURE)
        before = self.data_file.read_bytes()
        code, _, err = self.cli("editar", "1", "-f", "fecha-mala")
        self.assertEqual(code, EXIT_ERROR)
        self.assertIn("Fecha inválida", err)
        self.assertEqual(self.data_file.read_bytes(), before)

    def test_corrupt_file_reports_error_and_is_preserved(self):
        self.data_file.write_text("{ esto no es json", encoding="utf-8")
        code, _, err = self.cli("listar")
        self.assertEqual(code, EXIT_ERROR)
        self.assertIn("No se pudo leer el archivo de tareas", err)
        self.assertEqual(self.data_file.read_text(encoding="utf-8"), "{ esto no es json")

    def test_interactive_menu_persists_to_file(self):
        answers = iter(["1", "Desde el menú", "", FUTURE, "2", "0"])
        out = io.StringIO()
        code = main(
            ["--archivo", str(self.data_file)],
            stdout=out,
            input_fn=lambda _: next(answers),
        )
        self.assertEqual(code, EXIT_OK)
        task = self.read_file()["tasks"][0]
        self.assertEqual(task["name"], "Desde el menú")
        self.assertEqual(task["status"], "en progreso")


class TestEndToEndProcess(TempFileTestCase):
    """Ejecuta el programa como proceso del sistema operativo."""

    def run_program(self, *argv, entry=("-m", "task_manager"), stdin=None):
        env = {**os.environ, "TASKS_FILE": str(self.data_file), "PYTHONIOENCODING": "utf-8"}
        return subprocess.run(
            [sys.executable, *entry, *argv],
            cwd=PROJECT_ROOT,
            env=env,
            input=stdin,
            capture_output=True,
            text=True,
            encoding="utf-8",
            timeout=30,
        )

    def test_module_entry_point_commands(self):
        result = self.run_program("crear", "-n", "Proceso", "-f", FUTURE)
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertIn("Tarea creada con id 1", result.stdout)

        result = self.run_program("listar")
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertIn("Proceso", result.stdout)

    def test_main_py_interactive_mode(self):
        stdin = "\n".join(["1", "Interactiva", "Desde stdin", FUTURE, "", "4", "0"]) + "\n"
        result = self.run_program(entry=("main.py",), stdin=stdin)
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertIn("GESTOR DE TAREAS", result.stdout)
        self.assertIn("Tarea creada con id 1", result.stdout)
        self.assertIn("¡Hasta luego!", result.stdout)

        # Lo creado en modo menú es visible en modo comando
        result = self.run_program("ver", "1", entry=("main.py",))
        self.assertIn("Descripción: Desde stdin", result.stdout)

    def test_exit_codes(self):
        self.assertEqual(self.run_program("eliminar", "1").returncode, 1)
        self.assertEqual(self.run_program("comando-inexistente").returncode, 2)
        self.assertEqual(self.run_program("--version").returncode, 0)


if __name__ == "__main__":
    unittest.main()
