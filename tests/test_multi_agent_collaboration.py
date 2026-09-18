from pathlib import Path
import sys
import tempfile
import unittest

import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from dataops_ai.agents.investigation_agent import InvestigationAgent
from dataops_ai.agents.orchestrator import AgentOrchestrator
from dataops_ai.agents.quality_agent import DataQualityAgent
from dataops_ai.agents.resolution_agent import ResolutionAgent
from dataops_ai.config import Settings
from dataops_ai.models import AgentDiagnosis, QualityReport
from dataops_ai.pipelines.load import load_timeseries
from dataops_ai.tools.quality_tools import run_quality_checks


class MultiAgentCollaborationTest(unittest.TestCase):
    def test_direct_consensus_flow(self) -> None:
        """Cenário sem incidente conclui em consenso direto na rodada 1."""
        with tempfile.TemporaryDirectory(ignore_cleanup_errors=True) as temp_dir:
            root = Path(temp_dir)
            settings = Settings(
                project_root=root,
                database_url=f"sqlite:///{root / 'test.db'}",
                gemini_api_key=None,
                gemini_model="gemini-flash-latest",
                gemini_store_interactions=False,
                bcb_series_code=11,
                bcb_start_date="01/01/2024",
                bcb_end_date="05/01/2024",
            )

            result = AgentOrchestrator(settings).run("none", "sem incidente")

            self.assertIsNotNone(result.collaboration)
            self.assertEqual(result.collaboration.status, "consenso_direto")
            self.assertEqual(result.collaboration.iterations, 1)
            self.assertGreaterEqual(len(result.collaboration.conversation), 3)

            speakers = [turn.speaker for turn in result.collaboration.conversation]
            self.assertIn("DataQualityAgent", speakers)
            self.assertIn("InvestigationAgent", speakers)
            self.assertIn("ResolutionAgent", speakers)

            report_content = Path(result.incident_report_path).read_text(encoding="utf-8")
            self.assertIn("Colaboração e Consenso Multiagente", report_content)
            self.assertIn("Consenso Direto", report_content)

    def test_refined_consensus_with_calibration(self) -> None:
        """Cenário com incidente de tipo inválido aciona calibração supervisionada (rodada 2)."""
        with tempfile.TemporaryDirectory(ignore_cleanup_errors=True) as temp_dir:
            root = Path(temp_dir)
            settings = Settings(
                project_root=root,
                database_url=f"sqlite:///{root / 'test.db'}",
                gemini_api_key=None,
                gemini_model="gemini-flash-latest",
                gemini_store_interactions=False,
                bcb_series_code=11,
                bcb_start_date="01/01/2024",
                bcb_end_date="05/01/2024",
            )

            result = AgentOrchestrator(settings).run("scenario_05_invalid_type", "tipo inválido")

            self.assertIsNotNone(result.collaboration)
            self.assertEqual(result.collaboration.status, "consenso_refinado")
            self.assertEqual(result.collaboration.iterations, 2)

            roles = [turn.role for turn in result.collaboration.conversation]
            self.assertIn("diagnosis", roles)
            self.assertIn("investigation", roles)
            self.assertIn("calibration", roles)
            self.assertIn("action_plan", roles)

            report_content = Path(result.incident_report_path).read_text(encoding="utf-8")
            self.assertIn("Consenso Refinado (com calibração)", report_content)


    def test_investigation_alignment_evaluation(self) -> None:
        """Testa as condições sob as quais a investigação solicita calibração ao supervisor."""
        investigation_agent = InvestigationAgent("sqlite:///:memory:", Path(tempfile.gettempdir()))
        df = pd.DataFrame(
            {
                "date": pd.to_datetime(["2024-01-01"]),
                "value": [10.5],
                "series_code": [11],
                "source": ["bcb_api"],
            }
        )
        report = run_quality_checks(df)
        diag = AgentDiagnosis(
            agent_name="DataQualityAgent",
            severity="low",
            summary="Tudo ok.",
            probable_causes=[],
            recommended_actions=[],
            needs_investigation_agent=False,
        )
        inv = investigation_agent.investigate(report, diag, "none", "run_ok")

        needs_refine, _ = investigation_agent.evaluate_alignment(report, diag, inv, {})
        self.assertFalse(needs_refine)

        # Se severidade for alta, deve sinalizar refinamento
        diag_high = AgentDiagnosis(
            agent_name="DataQualityAgent",
            severity="high",
            summary="Problema grave.",
            probable_causes=["falha"],
            recommended_actions=[],
            needs_investigation_agent=True,
        )
        df_fail = pd.DataFrame(
            {
                "date": pd.to_datetime(["2024-01-01"]),
                "value": ["invalido"],
                "series_code": [11],
                "source": ["bcb_api"],
            }
        )
        report_fail = run_quality_checks(df_fail)
        inv_fail = investigation_agent.investigate(report_fail, diag_high, "falha", "run_fail")

        needs_refine_high, reason = investigation_agent.evaluate_alignment(
            report_fail, diag_high, inv_fail, {"quarantined": True}
        )
        self.assertTrue(needs_refine_high)
        self.assertIn("ALTA", reason)

    def test_resolution_agent_build_plan_with_consensus(self) -> None:
        """Testa formulação de plano consensual pelo ResolutionAgent."""
        resolution_agent = ResolutionAgent()
        df = pd.DataFrame(
            {
                "date": pd.to_datetime(["2024-01-01", "2024-01-01"]),
                "value": [1.0, 1.0],
                "series_code": [11, 11],
                "source": ["test", "test"],
            }
        )
        report = run_quality_checks(df)
        diag = DataQualityAgent(None, "gemini-flash-latest").diagnose(report, {})
        inv = InvestigationAgent("sqlite:///:memory:", Path(tempfile.gettempdir())).investigate(
            report, diag, "duplicados", "run_01"
        )

        plan, turn = resolution_agent.build_plan_with_consensus(
            report, diag, inv, {"quarantined": True}
        )

        self.assertEqual(turn.speaker, "ResolutionAgent")
        self.assertEqual(turn.role, "action_plan")
        self.assertEqual(turn.action_taken, "consenso_atingido")
        self.assertTrue(any("quarentena" in step.lower() or "dlq" in step.lower() for step in plan.correction_steps))


if __name__ == "__main__":
    unittest.main()
