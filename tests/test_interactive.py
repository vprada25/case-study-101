"""Pruebas unitarias del modo interactivo (task_manager.interactive).

Las respuestas del usuario se simulan con una lista de entradas; la salida se
captura en un ``StringIO``.
"""

import io
import unittest

from task_manager.interactive import InteractiveApp
from task_manager.models import TaskStatus
from task_manager.service import TaskService

FUTURE = "2099-12-31"


class InteractiveTestCase(unittest.TestCase):
    def setUp(self):
        self.service = TaskService()

    def run_app(self, *inputs):
        """Ejecuta el menú con las entradas dadas y devuelve (código, salida).

        Si las entradas se agotan se simula Ctrl+D (EOFError), que cierra
        el programa de forma ordenada.
        """
        answers = iter(inputs)

        def fake_input(_prompt):
            try:
                return next(answers)
            except StopIteration:
                raise EOFError from None

        out = io.StringIO()
        code = InteractiveApp(self.service, input_fn=fake_input, output=out).run()
        return code, out.getvalue()


class TestMenu(InteractiveTestCase):
    def test_shows_menu_and_exits(self):
        code, out = self.run_app("0")
        self.assertEqual(code, 0)
        for label in ("Crear tarea", "Editar tarea", "Eliminar tarea",
                      "Listar tareas", "Filtrar por estado", "Salir"):
            self.assertIn(label, out)
        self.assertIn("¡Hasta luego!", out)

    def test_menu_shows_status_summary(self):
        self.service.create_task("A", FUTURE)
        self.service.create_task("B", FUTURE, status="completada")
        _, out = self.run_app("0")
        self.assertIn("2 tarea(s) — pendiente: 1 | en progreso: 0 | completada: 1", out)

    def test_invalid_option(self):
        _, out = self.run_app("9", "0")
        self.assertIn("Opción no válida", out)

    def test_eof_exits_gracefully(self):
        code, out = self.run_app()
        self.assertEqual(code, 0)
        self.assertIn("¡Hasta luego!", out)

    def test_keyboard_interrupt_exits_gracefully(self):
        def ctrl_c(_):
            raise KeyboardInterrupt

        out = io.StringIO()
        code = InteractiveApp(self.service, input_fn=ctrl_c, output=out).run()
        self.assertEqual(code, 0)


class TestCreate(InteractiveTestCase):
    def test_create_with_defaults(self):
        # opción 1, nombre, descripción vacía, fecha, Enter = pendiente
        _, out = self.run_app("1", "Estudiar", "", FUTURE, "", "0")
        self.assertIn("Tarea creada con id 1", out)
        task = self.service.get_task(1)
        self.assertEqual(task.name, "Estudiar")
        self.assertIs(task.status, TaskStatus.PENDING)

    def test_create_reasks_invalid_values(self):
        _, out = self.run_app(
            "1",
            "", "Informe",                # nombre vacío -> se vuelve a pedir
            "Caso 101",
            "31/12/2099", FUTURE,         # fecha inválida -> se vuelve a pedir
            "7", "2",                     # estado inválido -> se vuelve a pedir
            "0",
        )
        self.assertIn("Este campo es obligatorio", out)
        self.assertIn("Fecha inválida", out)
        self.assertIn("Opción no válida. Elija un número", out)
        task = self.service.get_task(1)
        self.assertEqual(task.description, "Caso 101")
        self.assertIs(task.status, TaskStatus.IN_PROGRESS)


class TestEdit(InteractiveTestCase):
    def setUp(self):
        super().setUp()
        self.service.create_task("Original", FUTURE, "desc")

    def test_enter_keeps_current_values(self):
        _, out = self.run_app("2", "1", "", "", "", "", "0")
        self.assertIn("Tarea 1 actualizada", out)
        task = self.service.get_task(1)
        self.assertEqual((task.name, task.description), ("Original", "desc"))
        self.assertIs(task.status, TaskStatus.PENDING)

    def test_edit_values(self):
        self.run_app("2", "1", "Nuevo", "-", "2099-01-01", "3", "0")
        task = self.service.get_task(1)
        self.assertEqual(task.name, "Nuevo")
        self.assertEqual(task.description, "")
        self.assertEqual(task.due_date.isoformat(), "2099-01-01")
        self.assertIs(task.status, TaskStatus.COMPLETED)

    def test_edit_unknown_id_then_back(self):
        _, out = self.run_app("2", "5", "", "0")
        self.assertIn("No existe una tarea con id 5", out)
        self.assertEqual(self.service.get_task(1).name, "Original")

    def test_edit_without_tasks(self):
        self.service.delete_task(1)
        _, out = self.run_app("2", "0")
        self.assertIn("No hay tareas registradas", out)


class TestDelete(InteractiveTestCase):
    def setUp(self):
        super().setUp()
        self.service.create_task("Borrar", FUTURE)

    def test_delete_confirmed(self):
        _, out = self.run_app("3", "1", "s", "0")
        self.assertIn("Tarea 1 eliminada", out)
        self.assertEqual(self.service.list_tasks(), [])

    def test_delete_cancelled(self):
        _, out = self.run_app("3", "1", "n", "0")
        self.assertIn("Operación cancelada", out)
        self.assertEqual(len(self.service.list_tasks()), 1)


class TestListFilterShow(InteractiveTestCase):
    def setUp(self):
        super().setUp()
        self.service.create_task("Alfa", FUTURE)
        self.service.create_task("Beta", FUTURE, status="completada")

    def test_list(self):
        _, out = self.run_app("4", "0")
        self.assertIn("Alfa", out)
        self.assertIn("Beta", out)
        self.assertIn("Total: 2 tarea(s)", out)

    def test_filter_by_number(self):
        _, out = self.run_app("5", "3", "0")
        self.assertIn("Total: 1 tarea(s)", out)
        table = out.split("Seleccione un estado")[-1]
        self.assertIn("Beta", table)
        self.assertNotIn("Alfa", table)

    def test_show(self):
        _, out = self.run_app("6", "2", "0")
        self.assertIn("Nombre:      Beta", out)


if __name__ == "__main__":
    unittest.main()
