from __future__ import annotations

from pathlib import Path
from typing import Any

import yaml
from pydantic import BaseModel, Field


class ColumnContract(BaseModel):
    type: str
    nullable: bool = False
    unique: bool = False
    min_value: float | None = None
    max_value: float | None = None
    description: str | None = None


class AnomalyRule(BaseModel):
    enabled: bool = True
    column: str | None = None
    threshold: float | None = None
    description: str | None = None


class DataContract(BaseModel):
    version: str = "1.0"
    dataset_name: str
    description: str | None = None
    columns: dict[str, ColumnContract]
    anomaly_rules: dict[str, AnomalyRule] = Field(default_factory=dict)

    @property
    def expected_schema(self) -> dict[str, str]:
        """Retorna o mapeamento coluna -> tipo semântico."""
        return {col: info.type for col, info in self.columns.items()}

    @property
    def required_columns(self) -> list[str]:
        return [col for col, info in self.columns.items() if not info.nullable]

    @property
    def unique_columns(self) -> list[str]:
        return [col for col, info in self.columns.items() if info.unique]


def load_contract(path: Path) -> DataContract:
    """Carrega e valida um contrato de dados a partir de um arquivo YAML."""
    if not path.exists():
        raise FileNotFoundError(f"Arquivo de contrato não encontrado: {path}")

    raw = yaml.safe_load(path.read_text(encoding="utf-8"))
    return DataContract(**raw)


def find_default_contract(project_root: Path) -> DataContract:
    """Busca o contrato padrão em config/contracts/bcb_series.yaml."""
    contract_path = project_root / "config" / "contracts" / "bcb_series.yaml"
    if contract_path.exists():
        return load_contract(contract_path)

    # Fallback caso o arquivo não seja encontrado
    return DataContract(
        dataset_name="bcb_timeseries",
        columns={
            "date": ColumnContract(type="datetime", nullable=False, unique=True),
            "value": ColumnContract(type="numeric", nullable=False, min_value=0.0, max_value=100.0),
            "series_code": ColumnContract(type="numeric", nullable=False),
            "source": ColumnContract(type="text", nullable=False),
        },
    )
