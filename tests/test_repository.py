"""Pruebas unitarias de los repositorios (task_manager.repository)."""

import json
import tempfile
import unittest
from datetime import date
from pathlib import Path

from task_manager.exceptions import StorageError
from task_manager.models import Task, TaskStatus
from task_manager.repository import InMemoryTaskRepository, JsonTaskRepository


def sample_tasks():
    return [
        Task(id=1, name="Ñandú", description="tildes áéí", due_date=date(2026, 10, 20)),
        Task(
            id=2,
            name="Segunda",
            due_date=date(2026, 11, 1),
            status=TaskStatus.COMPLETED,
        ),
    ]


class TestInMemoryTaskRepository(unittest.TestCase):
    def test_save_and_load(self):
        repo = InMemoryTaskRepository()
        tasks = sample_tasks()
        repo.save(tasks)
        self.assertEqual(repo.load(), tasks)

    def test_load_returns_copy(self):
        repo = InMemoryTaskRepository(sample_tasks())
        repo.load().clear()
        self.assertEqual(len(repo.load()), 2)


class TestJsonTaskRepository(unittest.TestCase):
    def setUp(self):
        self._tmp = tempfile.TemporaryDirectory()
        self.dir = Path(self._tmp.name)
        self.path = self.dir / "tasks.json"
        self.repo = JsonTaskRepository(self.path)

    def tearDown(self):
        self._tmp.cleanup()

    def test_missing_file_returns_empty_list(self):
        self.assertEqual(self.repo.load(), [])
        self.assertFalse(self.path.exists())

    def test_save_then_load_roundtrip(self):
        tasks = sample_tasks()
        self.repo.save(tasks)
        self.assertEqual(JsonTaskRepository(self.path).load(), tasks)

    def test_file_format(self):
        self.repo.save(sample_tasks())
        text = self.path.read_text(encoding="utf-8")
        self.assertIn("Ñandú", text)  # UTF-8 legible, sin escapes \u
        data = json.loads(text)
        self.assertEqual(data["version"], 1)
        self.assertEqual(
            data["tasks"][1],
            {
                "id": 2,
                "name": "Segunda",
                "description": "",
                "due_date": "2026-11-01",
                "status": "completada",
            },
        )

    def test_creates_parent_directories(self):
        nested = JsonTaskRepository(self.dir / "a" / "b" / "tasks.json")
        nested.save(sample_tasks())
        self.assertEqual(len(nested.load()), 2)

    def test_save_overwrites_previous_content(self):
        self.repo.save(sample_tasks())
        self.repo.save([])
        self.assertEqual(self.repo.load(), [])

    def test_no_temp_files_left_behind(self):
        self.repo.save(sample_tasks())
        self.assertEqual([p.name for p in self.dir.iterdir()], ["tasks.json"])

    def test_corrupt_file_raises_storage_error(self):
        cases = {
            "json inválido": "{ no es json",
            "sin clave tasks": '{"version": 1}',
            "fecha inválida": '{"tasks": [{"id": 1, "name": "x", "due_date": "ayer"}]}',
        }
        for label, content in cases.items():
            with self.subTest(label):
                self.path.write_text(content, encoding="utf-8")
                with self.assertRaises(StorageError):
                    self.repo.load()

    def test_corrupt_file_is_not_overwritten_on_load(self):
        self.path.write_text("{ dañado", encoding="utf-8")
        with self.assertRaises(StorageError):
            self.repo.load()
        self.assertEqual(self.path.read_text(encoding="utf-8"), "{ dañado")

    def test_unwritable_location_raises_storage_error(self):
        blocker = self.dir / "archivo"
        blocker.write_text("x")
        repo = JsonTaskRepository(blocker / "tasks.json")  # el padre es un archivo
        with self.assertRaises(StorageError):
            repo.save(sample_tasks())


if __name__ == "__main__":
    unittest.main()
