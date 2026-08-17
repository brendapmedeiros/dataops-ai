from pathlib import Path
import sys
import unittest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from dataops_ai.tools import api_tools


class FakeResponse:
    status = 200

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc, traceback):
        return False


class ApiToolsTest(unittest.TestCase):
    def test_get_api_status_returns_available_when_request_succeeds(self) -> None:
        original_urlopen = api_tools.urlopen
        api_tools.urlopen = lambda url, timeout: FakeResponse()

        try:
            status = api_tools.get_api_status(11, "01/01/2024", "05/01/2024")
        finally:
            api_tools.urlopen = original_urlopen

        self.assertTrue(status["available"])
        self.assertEqual(status["status_code"], 200)
        self.assertEqual(status["source"], "bcb_api")

    def test_get_api_status_handles_timeout(self) -> None:
        original_urlopen = api_tools.urlopen

        def raise_timeout(url, timeout):
            raise TimeoutError("tempo esgotado")

        api_tools.urlopen = raise_timeout

        try:
            status = api_tools.get_api_status(11, "01/01/2024", "05/01/2024")
        finally:
            api_tools.urlopen = original_urlopen

        self.assertFalse(status["available"])
        self.assertEqual(status["error"], "timeout")


if __name__ == "__main__":
    unittest.main()
