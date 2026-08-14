from pathlib import Path
import sys
import unittest

import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from dataops_ai.tools.quality_tools import run_quality_checks


class QualityToolsTest(unittest.TestCase):
    def test_quality_checks_detect_null_value(self) -> None:
        df = pd.DataFrame(
            {
                "date": pd.to_datetime(["2024-01-01", "2024-01-02"]),
                "value": [1.0, None],
                "series_code": [11, 11],
                "source": ["test", "test"],
            }
        )

        report = run_quality_checks(df)

        self.assertTrue(report.failed_checks)
        self.assertTrue(any(issue.check_name == "check_nulls" for issue in report.failed_checks))


if __name__ == "__main__":
    unittest.main()
