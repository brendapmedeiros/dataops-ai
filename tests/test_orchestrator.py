from pathlib import Path
import sys
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from dataops_ai.agents.orchestrator import AgentOrchestrator
from dataops_ai.config import Settings


class AgentOrchestratorTest(unittest.TestCase):
    def test_orchestrator_runs_pipeline_and_agents(self) -> None:
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

            self.assertTrue(result.run_id)
            self.assertGreater(result.rows_loaded, 0)
            self.assertEqual(result.diagnosis_engine, "regras_locais")
            self.assertTrue(Path(result.diagnosis_report_path).exists())
            self.assertTrue(Path(result.incident_report_path).exists())
            self.assertTrue(Path(result.history_path).exists())


if __name__ == "__main__":
    unittest.main()
