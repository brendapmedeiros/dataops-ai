from pathlib import Path
import sys
import unittest

import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from dataops_ai.agents.quality_agent import DataQualityAgent
from dataops_ai.tools.quality_tools import run_quality_checks


class DataQualityAgentTest(unittest.TestCase):
    def test_local_diagnosis_handles_invalid_type_without_schema_drift_cause(self) -> None:
        df = pd.DataFrame(
            {
                "date": pd.to_datetime(["2024-01-01", "2024-01-02"]),
                "value": ["invalid_value", 1.1],
                "series_code": [11, 11],
                "source": ["test", "test"],
            }
        )

        quality_report = run_quality_checks(df)
        diagnosis = DataQualityAgent(None, "gemini-flash-latest").diagnose(quality_report, {})

        causes = " ".join(diagnosis.probable_causes)

        self.assertIn("conversao de tipo", causes)
        self.assertNotIn("Mudanca de schema", causes)


if __name__ == "__main__":
    unittest.main()
