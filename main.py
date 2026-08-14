from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent
sys.path.insert(0, str(PROJECT_ROOT / "src"))

from dataops_ai.agents.quality_agent import DataQualityAgent
from dataops_ai.config import load_settings
from dataops_ai.pipelines.extract import extract_bcb_series
from dataops_ai.pipelines.load import load_timeseries
from dataops_ai.pipelines.transform import transform_bcb_payload
from dataops_ai.scenarios import SCENARIOS, apply_scenario
from dataops_ai.tools.log_tools import get_last_pipeline_run, write_pipeline_log
from dataops_ai.tools.quality_tools import run_quality_checks


def main() -> None:
    parser = argparse.ArgumentParser(description="DataOps AI V1")
    parser.add_argument("command", choices=["run", "scenarios"])
    parser.add_argument("--scenario", default="none", choices=sorted(SCENARIOS))
    args = parser.parse_args()

    if args.command == "scenarios":
        print("\n".join(sorted(SCENARIOS)))
        return

    settings = load_settings(PROJECT_ROOT)
    write_pipeline_log(settings.logs_dir, "pipeline_started", {"scenario": args.scenario})

    raw_rows = extract_bcb_series(
        series_code=settings.bcb_series_code,
        start_date=settings.bcb_start_date,
        end_date=settings.bcb_end_date,
        output_dir=settings.raw_dir,
    )
    transformed = transform_bcb_payload(raw_rows, settings.bcb_series_code)
    staged = apply_scenario(transformed, args.scenario)

    settings.processed_dir.mkdir(parents=True, exist_ok=True)
    processed_path = settings.processed_dir / "bcb_timeseries.csv"
    staged.to_csv(processed_path, index=False)

    rows_loaded = load_timeseries(staged, settings.database_url)
    quality_report = run_quality_checks(staged)
    context = {
        "scenario": args.scenario,
        "rows_loaded": rows_loaded,
        "last_pipeline_run": get_last_pipeline_run(settings.logs_dir),
    }
    diagnosis = DataQualityAgent(settings.gemini_api_key, settings.gemini_model).diagnose(
        quality_report,
        context,
    )

    output = {
        "quality_report": quality_report.model_dump(mode="json"),
        "diagnosis": diagnosis.model_dump(mode="json"),
    }

    settings.curated_dir.mkdir(parents=True, exist_ok=True)
    report_path = settings.curated_dir / "quality_diagnosis.json"
    report_path.write_text(json.dumps(output, ensure_ascii=True, indent=2), encoding="utf-8")

    write_pipeline_log(
        settings.logs_dir,
        "pipeline_finished",
        {
            "scenario": args.scenario,
            "rows_loaded": rows_loaded,
            "failed_checks": len(quality_report.failed_checks),
            "severity": diagnosis.severity,
        },
    )

    print(json.dumps(output, ensure_ascii=True, indent=2))
    print(f"\nSaved diagnosis to {report_path}")


if __name__ == "__main__":
    main()
