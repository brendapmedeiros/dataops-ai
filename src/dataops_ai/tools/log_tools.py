from __future__ import annotations

import json
from datetime import UTC, datetime
from pathlib import Path


def write_pipeline_log(logs_dir: Path, event: str, payload: dict) -> Path:
    logs_dir.mkdir(parents=True, exist_ok=True)
    log_path = logs_dir / "pipeline_runs.jsonl"
    record = {"timestamp": datetime.now(UTC).isoformat(), "event": event, "payload": payload}
    with log_path.open("a", encoding="utf-8") as file:
        file.write(json.dumps(record, ensure_ascii=True) + "\n")
    return log_path


def read_pipeline_logs(logs_dir: Path, limit: int = 20) -> list[dict]:
    log_path = logs_dir / "pipeline_runs.jsonl"
    if not log_path.exists():
        return []

    lines = log_path.read_text(encoding="utf-8").splitlines()
    return [json.loads(line) for line in lines[-limit:]]


def get_last_pipeline_run(logs_dir: Path) -> dict | None:
    logs = read_pipeline_logs(logs_dir, limit=1)
    return logs[0] if logs else None

