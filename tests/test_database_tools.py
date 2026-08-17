from pathlib import Path
import sys
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from dataops_ai.tools.database_tools import DatabaseClient


class DatabaseToolsTest(unittest.TestCase):
    def test_sqlite_ping(self) -> None:
        with tempfile.TemporaryDirectory(ignore_cleanup_errors=True) as temp_dir:
            database_url = f"sqlite:///{Path(temp_dir) / 'test.db'}"

            self.assertTrue(DatabaseClient(database_url).ping())

    def test_append_record_keeps_existing_rows(self) -> None:
        with tempfile.TemporaryDirectory(ignore_cleanup_errors=True) as temp_dir:
            database_url = f"sqlite:///{Path(temp_dir) / 'test.db'}"
            database = DatabaseClient(database_url)

            self.assertFalse(database.table_exists("incident_history"))

            database.append_record({"run_id": "run_001", "failed_checks": 0}, "incident_history")
            database.append_record({"run_id": "run_002", "failed_checks": 1}, "incident_history")

            self.assertTrue(database.table_exists("incident_history"))
            self.assertEqual(database.count_rows("incident_history"), 2)


if __name__ == "__main__":
    unittest.main()
