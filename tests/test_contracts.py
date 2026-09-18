from pathlib import Path
import sys
import unittest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from dataops_ai.contracts import find_default_contract


class ContractsTest(unittest.TestCase):
    def test_default_contract_and_schema_loading(self) -> None:
        # valida carregamento do contrato yaml e definicao do schema
        contract = find_default_contract(ROOT)
        self.assertEqual(contract.dataset_name, "bcb_timeseries")
        self.assertIn("date", contract.columns)
        self.assertIn("value", contract.columns)
        self.assertIn("series_code", contract.columns)
        self.assertIn("source", contract.columns)
        self.assertEqual(contract.columns["date"].type, "datetime")
        self.assertEqual(contract.columns["value"].type, "numeric")
        self.assertEqual(contract.expected_schema.get("date"), "datetime")
        self.assertEqual(contract.expected_schema.get("value"), "numeric")


if __name__ == "__main__":
    unittest.main()
