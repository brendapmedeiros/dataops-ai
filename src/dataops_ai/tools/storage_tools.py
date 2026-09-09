from __future__ import annotations

import logging
from pathlib import Path

logger = logging.getLogger(__name__)

# tento importar o cliente do google cloud storage de forma opcional
try:
    from google.cloud import storage
except ImportError:
    storage = None


def upload_to_gcs_if_configured(
    local_path: Path,
    blob_name: str,
    bucket_name: str | None,
) -> str | None:
    # se o bucket nao foi informado ou a biblioteca nao estiver instalada, mantenho apenas local
    if not bucket_name or storage is None:
        return None

    try:
        client = storage.Client()
        bucket = client.bucket(bucket_name)
        blob = bucket.blob(blob_name)
        blob.upload_from_filename(str(local_path))
        logger.info("arquivo enviado com sucesso para o gcs: gs://%s/%s", bucket_name, blob_name)
        return f"gs://{bucket_name}/{blob_name}"
    except Exception as exc:
        # nao quebro a pipeline local caso o upload falhe ou nao haja credenciais de nuvem ativas
        logger.warning("nao foi possivel enviar para o gcs (%s): %s", blob_name, exc)
        return None
