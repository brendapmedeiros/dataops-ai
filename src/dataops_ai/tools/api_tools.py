from __future__ import annotations

from urllib.error import URLError
from urllib.parse import urlencode
from urllib.request import urlopen

from dataops_ai.pipelines.extract import BCB_BASE_URL


def get_api_status(
    series_code: int,
    start_date: str,
    end_date: str,
    timeout_seconds: int = 10,
) -> dict:
    params = urlencode(
        {"formato": "json", "dataInicial": start_date, "dataFinal": end_date}
    )
    url = f"{BCB_BASE_URL.format(series_code=series_code)}?{params}"

    try:
        with urlopen(url, timeout=timeout_seconds) as response:
            status_code = getattr(response, "status", 200)
            return {
                "available": 200 <= status_code < 300,
                "status_code": status_code,
                "source": "bcb_api",
                "error": None,
            }
    except TimeoutError:
        return {
            "available": False,
            "status_code": None,
            "source": "bcb_api",
            "error": "timeout",
        }
    except (URLError, OSError) as exc:
        return {
            "available": False,
            "status_code": None,
            "source": "bcb_api",
            "error": str(exc),
        }
