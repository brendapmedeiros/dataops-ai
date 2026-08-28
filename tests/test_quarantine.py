from pathlib import Path
import sys
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from dataops_ai.agents.orchestrator import AgentOrchestrator
from dataops_ai.config import Settings


class QuarantineCircuitBreakerTest(unittest.TestCase):
    def test_quarantine_triggered_on_invalid_data(self) -> None:
        with tempfile.TemporaryDirectory(ignore_cleanup_errors=True) as temp_dir:
            root = Path(temp_dir)
            settings = Settings(
                project_root=root,
                database_url=f"sqlite:///{root / 'test.db'}",
                gemini_api_key=None,
                gemini_model="gemini-flash-latest",
                gemini_store_interactions=True,
                bcb_series_code=11,
                bcb_start_date="01/01/2024",
                bcb_end_date="05/01/2024",
            )

            result = AgentOrchestrator(settings).run("scenario_01_null_values", "valores nulos")

            self.assertTrue(result.quarantined)
            self.assertEqual(result.rows_loaded, 0)
            self.assertIsNotNone(result.quarantine_path)
            self.assertTrue(Path(result.quarantine_path).exists())
            self.assertTrue(bool(result.audit_hash))

    def test_clean_data_bypasses_quarantine(self) -> None:
        with tempfile.TemporaryDirectory(ignore_cleanup_errors=True) as temp_dir:
            root = Path(temp_dir)
            settings = Settings(
                project_root=root,
                database_url=f"sqlite:///{root / 'test.db'}",
                gemini_api_key=None,
                gemini_model="gemini-flash-latest",
                gemini_store_interactions=True,
                bcb_series_code=11,
                bcb_start_date="01/01/2024",
                bcb_end_date="05/01/2024",
            )

            result = AgentOrchestrator(settings).run("none", "sem incidente")

            self.assertFalse(result.quarantined)
            self.assertGreater(result.rows_loaded, 0)
            self.assertIsNone(result.quarantine_path)
            self.assertTrue(bool(result.audit_hash))


if __name__ == "__main__":
    unittest.main()
