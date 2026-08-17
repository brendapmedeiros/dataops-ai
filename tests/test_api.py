from pathlib import Path
import sys
import tempfile
import unittest

from fastapi.testclient import TestClient

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from dataops_ai.api import create_app
from dataops_ai.config import Settings


class ApiTest(unittest.TestCase):
    def test_root_lists_available_endpoints(self) -> None:
        with tempfile.TemporaryDirectory(ignore_cleanup_errors=True) as temp_dir:
            client = TestClient(create_app(_test_settings(Path(temp_dir))))

            response = client.get("/")

            self.assertEqual(response.status_code, 200)
            self.assertIn("/docs", response.json()["endpoints"])

    def test_health_check(self) -> None:
        with tempfile.TemporaryDirectory(ignore_cleanup_errors=True) as temp_dir:
            client = TestClient(create_app(_test_settings(Path(temp_dir))))

            response = client.get("/saude")

            self.assertEqual(response.status_code, 200)
            self.assertEqual(response.json()["status"], "ok")

    def test_list_scenarios(self) -> None:
        with tempfile.TemporaryDirectory(ignore_cleanup_errors=True) as temp_dir:
            client = TestClient(create_app(_test_settings(Path(temp_dir))))

            response = client.get("/cenarios")

            self.assertEqual(response.status_code, 200)
            self.assertTrue(any(item["nome"] == "tipo_invalido" for item in response.json()["cenarios"]))

    def test_run_pipeline_and_read_history(self) -> None:
        with tempfile.TemporaryDirectory(ignore_cleanup_errors=True) as temp_dir:
            client = TestClient(create_app(_test_settings(Path(temp_dir))))

            run_response = client.post("/execucoes", json={"scenario": "timeout_api"})
            history_response = client.get("/historico")

            self.assertEqual(run_response.status_code, 200)
            self.assertEqual(run_response.json()["cenario"], "timeout na API")
            self.assertEqual(run_response.json()["relatorio_incidente"], "data/curated/incident_report.md")
            self.assertEqual(history_response.status_code, 200)
            self.assertEqual(len(history_response.json()["historico"]), 1)

    def test_run_pipeline_rejects_invalid_scenario(self) -> None:
        with tempfile.TemporaryDirectory(ignore_cleanup_errors=True) as temp_dir:
            client = TestClient(create_app(_test_settings(Path(temp_dir))))

            response = client.post("/execucoes", json={"scenario": "cenario_que_nao_existe"})

            self.assertEqual(response.status_code, 400)
            self.assertIn("Cenario invalido", response.json()["detail"])


def _test_settings(root: Path) -> Settings:
    return Settings(
        project_root=root,
        database_url=f"sqlite:///{root / 'test.db'}",
        gemini_api_key=None,
        gemini_model="gemini-flash-latest",
        bcb_series_code=11,
        bcb_start_date="01/01/2024",
        bcb_end_date="05/01/2024",
    )


if __name__ == "__main__":
    unittest.main()
