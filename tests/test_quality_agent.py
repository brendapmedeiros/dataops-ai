from pathlib import Path
import sys
import unittest

import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from dataops_ai.agents.quality_agent import DataQualityAgent
from dataops_ai.llm.provider import GeminiResult
from dataops_ai.models import LLMMetadata
from dataops_ai.tools.quality_tools import run_quality_checks


class FakeGeminiClient:
    def generate_json(
        self,
        prompt: str,
        schema: dict,
        tools: list | None = None,
        tool_handlers: dict | None = None,
    ) -> GeminiResult:
        return GeminiResult(
            data={
                "agent_name": "DataQualityAgent",
                "severity": "high",
                "summary": "Tipo inválido encontrado na coluna de valor.",
                "probable_causes": ["Falha na conversão do valor antes da carga."],
                "recommended_actions": ["Revisar a transformação antes de carregar novamente."],
                "needs_investigation_agent": True,
            },
            metadata=LLMMetadata(
                provider="gemini",
                model="gemini-2.5-flash",
                api="interactions",
                interaction_id="int_teste",
                response_format="json_schema",
                prompt_version="quality-diagnosis-v1",
                store_interaction=True,
                latency_ms=120,
                step_types=["model_output"],
            ),
        )


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

        self.assertIn("conversão de tipo", causes)
        self.assertNotIn("Mudança de schema", causes)

    def test_gemini_metadata_is_kept_when_diagnosis_uses_interactions(self) -> None:
        df = pd.DataFrame(
            {
                "date": pd.to_datetime(["2024-01-01", "2024-01-02"]),
                "value": ["invalid_value", 1.1],
                "series_code": [11, 11],
                "source": ["test", "test"],
            }
        )

        quality_report = run_quality_checks(df)
        agent = DataQualityAgent(
            "fake-key",
            "gemini-2.5-flash",
            store_interactions=True,
            gemini_client=FakeGeminiClient(),
        )
        diagnosis = agent.diagnose(quality_report, {"run_id": "teste"})

        self.assertEqual(diagnosis.severity, "high")
        self.assertEqual(agent.engine_used, "gemini")
        self.assertEqual(agent.llm_metadata.api, "interactions")
        self.assertEqual(agent.llm_metadata.interaction_id, "int_teste")


if __name__ == "__main__":
    unittest.main()
