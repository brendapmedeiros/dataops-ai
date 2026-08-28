from pathlib import Path
import sys
import unittest

import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from dataops_ai.tools.quality_tools import compare_schema, run_quality_checks


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

    def test_compare_schema_detects_missing_column(self) -> None:
        df = pd.DataFrame(
            {
                "date": pd.to_datetime(["2024-01-01"]),
                "series_code": [11],
                "source": ["test"],
            }
        )

        issues = compare_schema(df)

        self.assertTrue(any(issue.column == "value" and issue.status == "fail" for issue in issues))

    def test_check_drift_zscore_detects_severe_outlier(self) -> None:
        from dataops_ai.tools.quality_tools import check_drift_zscore

        # Série com 24 valores normais em torno de 10.0 e 1 outlier extremo de 100.0 (Z-score ~ 4.8)
        values = [10.0] * 24 + [100.0]
        df = pd.DataFrame({"value": values})

        issue = check_drift_zscore(df, "value", threshold=3.0)
        self.assertEqual(issue.status, "fail")
        self.assertGreater(issue.rows_affected, 0)
        self.assertIn("anomalia estatística", issue.details)

    def test_check_pii_exposure_detects_cpf(self) -> None:
        from dataops_ai.tools.quality_tools import check_pii_exposure

        df = pd.DataFrame({"obs": ["Normal", "Cliente CPF: 123.456.789-00 registrado"]})
        issue = check_pii_exposure(df)
        self.assertEqual(issue.status, "fail")
        self.assertIn("PII", issue.details)

    def test_check_pii_exposure_passes_on_clean_data(self) -> None:
        from dataops_ai.tools.quality_tools import check_pii_exposure

        df = pd.DataFrame({"source": ["bcb_api", "bcb_api"]})
        issue = check_pii_exposure(df)
        self.assertEqual(issue.status, "pass")


if __name__ == "__main__":
    unittest.main()
