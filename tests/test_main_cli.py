from pathlib import Path
import sys
import unittest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from main import _validate_quality_rules


class MainCliTest(unittest.TestCase):
    def test_validate_quality_rules_covers_core_scenarios(self) -> None:
        results = _validate_quality_rules()

        self.assertEqual(len(results), 5)
        self.assertTrue(all(result["ok"] for result in results))


if __name__ == "__main__":
    unittest.main()
