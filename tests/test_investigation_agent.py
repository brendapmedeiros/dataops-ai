from pathlib import Path
import sys
import tempfile
import unittest

import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from dataops_ai.agents.investigation_agent import InvestigationAgent
from dataops_ai.agents.quality_agent import DataQualityAgent
from dataops_ai.pipelines.load import load_timeseries
from dataops_ai.tools.log_tools import write_pipeline_log
from dataops_ai.tools.quality_tools import run_quality_checks


class InvestigationAgentTest(unittest.TestCase):
    def test_investigation_uses_database_and_logs_as_evidence(self) -> None:
        with tempfile.TemporaryDirectory(ignore_cleanup_errors=True) as temp_dir:
            temp_path = Path(temp_dir)
            database_url = f"sqlite:///{temp_path / 'test.db'}"
            logs_dir = temp_path / "logs"
            df = pd.DataFrame(
                {
                    "date": pd.to_datetime(["2024-01-01", "2024-01-02"]),
                    "value": [1.0, None],
                    "series_code": [11, 11],
                    "source": ["test", "test"],
                }
            )

            load_timeseries(df, database_url)
            write_pipeline_log(logs_dir, "pipeline_finished", {"scenario": "valores_nulos"})
            quality_report = run_quality_checks(df)
            diagnosis = DataQualityAgent(None, "gemini-flash-latest").diagnose(quality_report, {})

            report = InvestigationAgent(database_url, logs_dir).investigate(
                quality_report,
                diagnosis,
                "valores_nulos",
                "run_test_001",
            )

            self.assertEqual(report.agent_name, "InvestigationAgent")
            self.assertTrue(report.evidence)
            self.assertIn("2 linha(s)", " ".join(report.evidence))
            self.assertTrue(report.next_steps)

    def test_investigation_detects_api_fallback_from_logs(self) -> None:
        with tempfile.TemporaryDirectory(ignore_cleanup_errors=True) as temp_dir:
            temp_path = Path(temp_dir)
            database_url = f"sqlite:///{temp_path / 'test.db'}"
            logs_dir = temp_path / "logs"
            df = pd.DataFrame(
                {
                    "date": pd.to_datetime(["2024-01-01", "2024-01-02"]),
                    "value": [1.0, 1.1],
                    "series_code": [11, 11],
                    "source": ["simulated_api_timeout_fallback", "simulated_api_timeout_fallback"],
                }
            )

            load_timeseries(df, database_url)
            write_pipeline_log(
                logs_dir,
                "api_fallback_used",
                {
                    "scenario": "timeout_api",
                    "run_id": "run_test_001",
                    "source": "simulated_api_timeout_fallback",
                    "reason": "timeout simulado",
                    "rows_returned": len(df),
                },
            )
            quality_report = run_quality_checks(df)
            diagnosis = DataQualityAgent(None, "gemini-flash-latest").diagnose(quality_report, {})

            report = InvestigationAgent(database_url, logs_dir).investigate(
                quality_report,
                diagnosis,
                "timeout_api",
                "run_test_001",
            )

            self.assertIn("falha operacional", report.summary)
            self.assertIn("fallback", " ".join(report.evidence))
            self.assertIn("coleta", report.hypothesis)


if __name__ == "__main__":
    unittest.main()
