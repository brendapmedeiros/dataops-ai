from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path


def load_dotenv(path: Path) -> None:
    if not path.exists():
        return

    for raw_line in path.read_text(encoding="utf-8").splitlines():
        line = raw_line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, value = line.split("=", 1)
        os.environ.setdefault(key.strip(), value.strip().strip("\"'"))


@dataclass(frozen=True)
class Settings:
    project_root: Path
    database_url: str
    gemini_api_key: str | None
    gemini_model: str
    gemini_store_interactions: bool
    bcb_series_code: int
    bcb_start_date: str
    bcb_end_date: str

    @property
    def raw_dir(self) -> Path:
        return self.project_root / "data" / "raw"

    @property
    def processed_dir(self) -> Path:
        return self.project_root / "data" / "processed"

    @property
    def curated_dir(self) -> Path:
        return self.project_root / "data" / "curated"

    @property
    def logs_dir(self) -> Path:
        return self.project_root / "logs"


def load_settings(project_root: Path) -> Settings:
    load_dotenv(project_root / ".env")

    return Settings(
        project_root=project_root,
        database_url=os.getenv("DATABASE_URL", "sqlite:///dataops_ai.db"),
        gemini_api_key=os.getenv("GEMINI_API_KEY") or None,
        gemini_model=os.getenv("GEMINI_MODEL", "gemini-2.5-flash"),
        gemini_store_interactions=_env_bool("GEMINI_STORE_INTERACTIONS", default=True),
        bcb_series_code=int(os.getenv("BCB_SERIES_CODE", "11")),
        bcb_start_date=os.getenv("BCB_START_DATE", "01/01/2024"),
        bcb_end_date=os.getenv("BCB_END_DATE", "31/01/2024"),
    )


def _env_bool(name: str, default: bool) -> bool:
    value = os.getenv(name)
    if value is None:
        return default
    return value.strip().lower() in {"1", "true", "sim", "yes", "y"}
