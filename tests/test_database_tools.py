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


if __name__ == "__main__":
    unittest.main()
