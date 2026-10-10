"""Pruebas unitarias del servicio de tareas (task_manager.service)."""

import unittest
from datetime import date

from task_manager.exceptions import TaskNotFoundError
from task_manager.models import Task, TaskStatus
from task_manager.repository import InMemoryTaskRepository
from task_manager.service import TaskService


class TaskServiceTestCase(unittest.TestCase):
    def setUp(self):
        self.repo = InMemoryTaskRepository()
        self.service = TaskService(self.repo)


class TestCreateTask(TaskServiceTestCase):
    def test_creates_task_with_incremental_ids(self):
        t1 = self.service.create_task("Tarea 1", "2026-10-20")
        t2 = self.service.create_task("Tarea 2", "2026-10-21", "detalle")
        self.assertEqual((t1.id, t2.id), (1, 2))
        self.assertEqual(t2.description, "detalle")
        self.assertIs(t1.status, TaskStatus.PENDING)

    def test_accepts_initial_status(self):
        task = self.service.create_task("Tarea", "2026-10-20", status="en progreso")
        self.assertIs(task.status, TaskStatus.IN_PROGRESS)

    def test_persists_after_create(self):
        self.service.create_task("Tarea", "2026-10-20")
        self.assertEqual(len(self.repo.load()), 1)

    def test_invalid_data_does_not_consume_id_or_persist(self):
        with self.assertRaises(ValueError):
            self.service.create_task("", "2026-10-20")
        with self.assertRaises(ValueError):
            self.service.create_task("Tarea", "20/10/2026")
        self.assertEqual(self.repo.load(), [])
        self.assertEqual(self.service.create_task("Ok", "2026-10-20").id, 1)


class TestUpdateTask(TaskServiceTestCase):
    def setUp(self):
        super().setUp()
        self.task = self.service.create_task("Original", "2026-10-20", "desc")

    def test_updates_only_given_fields(self):
        updated = self.service.update_task(self.task.id, status="completada")
        self.assertIs(updated.status, TaskStatus.COMPLETED)
        self.assertEqual(updated.name, "Original")
        self.assertEqual(updated.description, "desc")

    def test_updates_all_fields(self):
        updated = self.service.update_task(
            self.task.id,
            name="Nuevo",
            description="nueva desc",
            due_date="2026-12-01",
            status=TaskStatus.IN_PROGRESS,
        )
        self.assertEqual(updated.name, "Nuevo")
        self.assertEqual(updated.description, "nueva desc")
        self.assertEqual(updated.due_date, date(2026, 12, 1))
        self.assertIs(updated.status, TaskStatus.IN_PROGRESS)
        self.assertEqual(self.service.get_task(self.task.id), updated)

    def test_allows_clearing_description(self):
        updated = self.service.update_task(self.task.id, description="")
        self.assertEqual(updated.description, "")

    def test_invalid_update_keeps_original(self):
        with self.assertRaises(ValueError):
            self.service.update_task(self.task.id, name="  ")
        with self.assertRaises(ValueError):
            self.service.update_task(self.task.id, status="desconocido")
        self.assertEqual(self.service.get_task(self.task.id), self.task)

    def test_update_missing_task_raises(self):
        with self.assertRaises(TaskNotFoundError):
            self.service.update_task(99, name="x")

    def test_persists_after_update(self):
        self.service.update_task(self.task.id, name="Persistida")
        self.assertEqual(self.repo.load()[0].name, "Persistida")


class TestDeleteTask(TaskServiceTestCase):
    def test_deletes_and_returns_task(self):
        task = self.service.create_task("Borrar", "2026-10-20")
        deleted = self.service.delete_task(task.id)
        self.assertEqual(deleted, task)
        self.assertEqual(self.service.list_tasks(), [])
        self.assertEqual(self.repo.load(), [])

    def test_delete_missing_task_raises(self):
        with self.assertRaises(TaskNotFoundError):
            self.service.delete_task(1)

    def test_ids_are_not_reused_after_delete(self):
        t1 = self.service.create_task("A", "2026-10-20")
        self.service.delete_task(t1.id)
        self.assertEqual(self.service.create_task("B", "2026-10-20").id, 2)


class TestListAndFilter(TaskServiceTestCase):
    def setUp(self):
        super().setUp()
        self.service.create_task("A", "2026-10-20")
        self.service.create_task("B", "2026-10-21", status="en progreso")
        self.service.create_task("C", "2026-10-22", status="completada")
        self.service.create_task("D", "2026-10-23")

    def test_list_returns_all_sorted_by_id(self):
        self.assertEqual([t.name for t in self.service.list_tasks()], ["A", "B", "C", "D"])

    def test_list_empty(self):
        self.assertEqual(TaskService().list_tasks(), [])

    def test_filter_by_status_enum_and_string(self):
        pending = self.service.filter_by_status(TaskStatus.PENDING)
        self.assertEqual([t.name for t in pending], ["A", "D"])
        in_progress = self.service.filter_by_status("en_progreso")
        self.assertEqual([t.name for t in in_progress], ["B"])
        completed = self.service.filter_by_status("COMPLETADA")
        self.assertEqual([t.name for t in completed], ["C"])

    def test_filter_invalid_status_raises(self):
        with self.assertRaises(ValueError):
            self.service.filter_by_status("borrada")

    def test_get_task(self):
        self.assertEqual(self.service.get_task(2).name, "B")
        with self.assertRaises(TaskNotFoundError):
            self.service.get_task(50)


class TestServiceLoadsFromRepository(unittest.TestCase):
    def test_loads_existing_tasks_and_continues_ids(self):
        repo = InMemoryTaskRepository(
            [Task(id=5, name="Previa", due_date=date(2026, 10, 20))]
        )
        service = TaskService(repo)
        self.assertEqual(service.get_task(5).name, "Previa")
        self.assertEqual(service.create_task("Nueva", "2026-10-21").id, 6)


if __name__ == "__main__":
    unittest.main()
