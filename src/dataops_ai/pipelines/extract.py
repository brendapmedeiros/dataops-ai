from __future__ import annotations

import json
from pathlib import Path
from urllib.error import URLError
from urllib.parse import urlencode
from urllib.request import urlopen


BCB_BASE_URL = "https://api.bcb.gov.br/dados/serie/bcdata.sgs.{series_code}/dados"


def extract_bcb_series(
    series_code: int,
    start_date: str,
    end_date: str,
    output_dir: Path,
    timeout_seconds: int = 20,
    force_timeout: bool = False,
) -> list[dict]:
    params = urlencode(
        {"formato": "json", "dataInicial": start_date, "dataFinal": end_date}
    )
    url = f"{BCB_BASE_URL.format(series_code=series_code)}?{params}"

    try:
        if force_timeout:
            raise TimeoutError("timeout simulado para teste da pipeline")

        with urlopen(url, timeout=timeout_seconds) as response:
            payload = json.loads(response.read().decode("utf-8"))
            source = "bcb_api"
    except TimeoutError:
        payload = _fallback_payload()
        source = "simulated_api_timeout_fallback" if force_timeout else "local_fallback"
    except (URLError, OSError):
        payload = _fallback_payload()
        source = "local_fallback"

    output_dir.mkdir(parents=True, exist_ok=True)
    raw_path = output_dir / f"bcb_sgs_{series_code}.json"
    raw_path.write_text(json.dumps(payload, ensure_ascii=True, indent=2), encoding="utf-8")

    return [{"source": source, **row} for row in payload]


def _fallback_payload() -> list[dict]:
    return [
        {"data": "02/01/2024", "valor": "0.043739"},
        {"data": "03/01/2024", "valor": "0.043739"},
        {"data": "04/01/2024", "valor": "0.043739"},
        {"data": "05/01/2024", "valor": "0.043739"},
        {"data": "08/01/2024", "valor": "0.043739"},
    ]
