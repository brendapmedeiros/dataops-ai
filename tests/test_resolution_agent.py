from pathlib import Path
import sys
import tempfile
import unittest

import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from dataops_ai.agents.investigation_agent import InvestigationAgent
from dataops_ai.agents.quality_agent import DataQualityAgent
from dataops_ai.agents.resolution_agent import ResolutionAgent
from dataops_ai.pipelines.load import load_timeseries
from dataops_ai.tools.incident_tools import append_incident_history, create_incident_report, read_incident_history
from dataops_ai.tools.log_tools import write_pipeline_log
from dataops_ai.tools.quality_tools import run_quality_checks


class ResolutionAgentTest(unittest.TestCase):
    def test_resolution_plan_handles_duplicates(self) -> None:
        with tempfile.TemporaryDirectory(ignore_cleanup_errors=True) as temp_dir:
            temp_path = Path(temp_dir)
            database_url = f"sqlite:///{temp_path / 'test.db'}"
            logs_dir = temp_path / "logs"
            df = pd.DataFrame(
                {
                    "date": pd.to_datetime(["2024-01-01", "2024-01-01"]),
                    "value": [1.0, 1.0],
                    "series_code": [11, 11],
                    "source": ["test", "test"],
                }
            )

            load_timeseries(df, database_url)
            quality_report = run_quality_checks(df)
            diagnosis = DataQualityAgent(None, "gemini-flash-latest").diagnose(quality_report, {})
            investigation = InvestigationAgent(database_url, logs_dir).investigate(
                quality_report,
                diagnosis,
                "registros_duplicados",
                "run_test_001",
            )

            plan = ResolutionAgent().build_plan(quality_report, diagnosis, investigation)

            self.assertIn("duplicados", plan.summary)
            self.assertFalse(plan.requires_manual_review)
            self.assertTrue(any("deduplicacao" in step for step in plan.correction_steps))

    def test_incident_report_is_created(self) -> None:
        with tempfile.TemporaryDirectory(ignore_cleanup_errors=True) as temp_dir:
            temp_path = Path(temp_dir)
            database_url = f"sqlite:///{temp_path / 'test.db'}"
            logs_dir = temp_path / "logs"
            output_dir = temp_path / "curated"
            df = pd.DataFrame(
                {
                    "date": pd.to_datetime(["2024-01-01", "2024-01-02"]),
                    "value": [1.0, 1.1],
                    "series_code": [11, 11],
                    "source": ["fallback", "fallback"],
                }
            )

            load_timeseries(df, database_url)
            write_pipeline_log(
                logs_dir,
                "api_fallback_used",
                {"scenario": "timeout_api", "run_id": "run_test_001", "source": "local_fallback"},
            )
            quality_report = run_quality_checks(df)
            diagnosis = DataQualityAgent(None, "gemini-flash-latest").diagnose(quality_report, {})
            investigation = InvestigationAgent(database_url, logs_dir).investigate(
                quality_report,
                diagnosis,
                "timeout_api",
                "run_test_001",
            )
            resolution = ResolutionAgent().build_plan(quality_report, diagnosis, investigation)

            report_path = create_incident_report(
                output_dir,
                "run_test_001",
                "timeout na API",
                quality_report,
                diagnosis,
                investigation,
                resolution,
            )

            self.assertTrue(report_path.exists())
            self.assertIn("Relatorio de incidente", report_path.read_text(encoding="utf-8"))

    def test_incident_history_is_appended_and_read(self) -> None:
        with tempfile.TemporaryDirectory(ignore_cleanup_errors=True) as temp_dir:
            temp_path = Path(temp_dir)
            database_url = f"sqlite:///{temp_path / 'test.db'}"
            logs_dir = temp_path / "logs"
            output_dir = temp_path / "curated"
            df = pd.DataFrame(
                {
                    "date": pd.to_datetime(["2024-01-01", "2024-01-02"]),
                    "value": [1.0, 1.1],
                    "series_code": [11, 11],
                    "source": ["test", "test"],
                }
            )

            load_timeseries(df, database_url)
            quality_report = run_quality_checks(df)
            diagnosis = DataQualityAgent(None, "gemini-flash-latest").diagnose(quality_report, {})
            investigation = InvestigationAgent(database_url, logs_dir).investigate(
                quality_report,
                diagnosis,
                "sem_incidente",
                "run_test_001",
            )
            resolution = ResolutionAgent().build_plan(quality_report, diagnosis, investigation)

            history_path = append_incident_history(
                output_dir,
                "run_test_001",
                "sem incidente",
                quality_report,
                diagnosis,
                "regras_locais",
                resolution,
                "quality_diagnosis.json",
                "incident_report.md",
            )
            records = read_incident_history(output_dir)

            self.assertTrue(history_path.exists())
            self.assertEqual(len(records), 1)
            self.assertEqual(records[0]["run_id"], "run_test_001")
            self.assertEqual(records[0]["scenario"], "sem incidente")


if __name__ == "__main__":
    unittest.main()
