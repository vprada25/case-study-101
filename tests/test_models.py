"""Pruebas unitarias del modelo de dominio (task_manager.models)."""

import unittest
from datetime import date

from task_manager.models import Task, TaskStatus, parse_date


class TestTaskStatus(unittest.TestCase):
    def test_from_string_accepts_exact_values(self):
        self.assertIs(TaskStatus.from_string("pendiente"), TaskStatus.PENDING)
        self.assertIs(TaskStatus.from_string("en progreso"), TaskStatus.IN_PROGRESS)
        self.assertIs(TaskStatus.from_string("completada"), TaskStatus.COMPLETED)

    def test_from_string_is_case_and_separator_insensitive(self):
        self.assertIs(TaskStatus.from_string("  En_Progreso "), TaskStatus.IN_PROGRESS)
        self.assertIs(TaskStatus.from_string("EN-PROGRESO"), TaskStatus.IN_PROGRESS)
        self.assertIs(TaskStatus.from_string("COMPLETADA"), TaskStatus.COMPLETED)

    def test_from_string_rejects_unknown_value(self):
        with self.assertRaises(ValueError):
            TaskStatus.from_string("cancelada")


class TestParseDate(unittest.TestCase):
    def test_parses_iso_string(self):
        self.assertEqual(parse_date("2026-12-31"), date(2026, 12, 31))

    def test_returns_date_unchanged(self):
        d = date(2026, 1, 1)
        self.assertIs(parse_date(d), d)

    def test_rejects_invalid_format(self):
        for bad in ("31/12/2026", "2026-13-01", "", "mañana"):
            with self.subTest(value=bad):
                with self.assertRaises(ValueError):
                    parse_date(bad)


class TestTask(unittest.TestCase):
    def make_task(self, **overrides):
        data = {
            "id": 1,
            "name": "Escribir informe",
            "description": "Informe del caso práctico",
            "due_date": date(2026, 10, 20),
        }
        data.update(overrides)
        return Task(**data)

    def test_default_status_is_pending(self):
        self.assertIs(self.make_task().status, TaskStatus.PENDING)

    def test_strips_name_and_description(self):
        task = self.make_task(name="  Tarea  ", description="  detalle  ")
        self.assertEqual(task.name, "Tarea")
        self.assertEqual(task.description, "detalle")

    def test_empty_name_raises(self):
        for bad in ("", "   "):
            with self.subTest(name=bad):
                with self.assertRaises(ValueError):
                    self.make_task(name=bad)

    def test_accepts_string_date_and_status(self):
        task = self.make_task(due_date="2026-11-01", status="completada")
        self.assertEqual(task.due_date, date(2026, 11, 1))
        self.assertIs(task.status, TaskStatus.COMPLETED)

    def test_invalid_status_raises(self):
        with self.assertRaises(ValueError):
            self.make_task(status="archivada")
        with self.assertRaises(ValueError):
            self.make_task(status=42)

    def test_is_overdue(self):
        today = date(2026, 10, 21)
        self.assertTrue(self.make_task().is_overdue(today))
        self.assertFalse(self.make_task(status=TaskStatus.COMPLETED).is_overdue(today))
        self.assertFalse(self.make_task(due_date=date(2026, 10, 22)).is_overdue(today))

    def test_to_dict_and_from_dict_roundtrip(self):
        task = self.make_task(status=TaskStatus.IN_PROGRESS)
        data = task.to_dict()
        self.assertEqual(
            data,
            {
                "id": 1,
                "name": "Escribir informe",
                "description": "Informe del caso práctico",
                "due_date": "2026-10-20",
                "status": "en progreso",
            },
        )
        self.assertEqual(Task.from_dict(data), task)


if __name__ == "__main__":
    unittest.main()
