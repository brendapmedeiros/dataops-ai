from pathlib import Path
import sys
import unittest
from unittest.mock import MagicMock, patch

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from dataops_ai.tools.storage_tools import upload_to_gcs_if_configured


class StorageToolsTest(unittest.TestCase):
    # valido que sem bucket informado o retorno e nulo sem tentar conexao externa
    def test_upload_returns_none_without_bucket(self) -> None:
        result = upload_to_gcs_if_configured(Path("dummy.csv"), "dummy.csv", None)
        self.assertIsNone(result)

    # simulo o cliente gcs para testar o envio com sucesso
    @patch("dataops_ai.tools.storage_tools.storage")
    def test_upload_success_with_mocked_client(self, mock_storage: MagicMock) -> None:
        mock_client = MagicMock()
        mock_bucket = MagicMock()
        mock_blob = MagicMock()

        mock_storage.Client.return_value = mock_client
        mock_client.bucket.return_value = mock_bucket
        mock_bucket.blob.return_value = mock_blob

        result = upload_to_gcs_if_configured(Path("dummy.csv"), "remote_blob.csv", "meu-bucket")
        self.assertEqual(result, "gs://meu-bucket/remote_blob.csv")
        mock_blob.upload_from_filename.assert_called_once_with("dummy.csv")

    # garanto que falhas no gcs nao quebram a execucao
    @patch("dataops_ai.tools.storage_tools.storage")
    def test_upload_failure_handled_gracefully(self, mock_storage: MagicMock) -> None:
        mock_storage.Client.side_effect = Exception("erro de conexao")

        result = upload_to_gcs_if_configured(Path("dummy.csv"), "remote_blob.csv", "meu-bucket")
        self.assertIsNone(result)


if __name__ == "__main__":
    unittest.main()
