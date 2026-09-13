"""Tests for polymer_pipeline.r2_storage — Cloudflare R2 client.

Uses unittest.mock to avoid actual R2 connections.
"""

from __future__ import annotations

import tempfile
import unittest
from pathlib import Path
from unittest.mock import MagicMock, patch

from polymer_pipeline.r2_storage import R2Storage, get_r2_client


class TestGetR2Client(unittest.TestCase):
    @patch("polymer_pipeline.r2_storage.get_r2_endpoint", return_value=None)
    def test_returns_none_when_no_endpoint(self, _mock) -> None:
        result = get_r2_client()
        self.assertIsNone(result)

    @patch("polymer_pipeline.r2_storage.get_r2_endpoint", return_value="https://r2.example.com")
    @patch("polymer_pipeline.r2_storage.get_r2_access_key", return_value=None)
    def test_returns_none_when_no_access_key(self, _mock_ep, _mock_key) -> None:
        result = get_r2_client()
        self.assertIsNone(result)

    @patch("polymer_pipeline.r2_storage.get_r2_endpoint", return_value="https://r2.example.com")
    @patch("polymer_pipeline.r2_storage.get_r2_access_key", return_value="key")
    @patch("polymer_pipeline.r2_storage.get_r2_secret_key", return_value="secret")
    @patch("polymer_pipeline.r2_storage.boto3")
    def test_creates_client_when_all_configured(
        self, mock_boto, _mock_ep, _mock_key, _mock_secret,
    ) -> None:
        mock_boto.client.return_value = MagicMock()
        result = get_r2_client()
        self.assertIsNotNone(result)
        self.assertIsInstance(result, R2Storage)


class TestR2Storage(unittest.TestCase):
    def setUp(self) -> None:
        self.mock_client = MagicMock()
        self.storage = R2Storage.__new__(R2Storage)
        self.storage._endpoint = "https://r2.example.com"
        self.storage._access_key = "key"
        self.storage._secret_key = "secret"
        self.storage._bucket = "test-bucket"
        self.storage._client = self.mock_client

    def test_file_exists_true(self) -> None:
        self.mock_client.head_object.return_value = {}
        self.assertTrue(self.storage.file_exists("test.pdf"))

    def test_file_exists_false(self) -> None:
        from botocore.exceptions import ClientError
        self.mock_client.head_object.side_effect = ClientError(
            {"Error": {"Code": "404"}}, "HeadObject"
        )
        self.assertFalse(self.storage.file_exists("test.pdf"))

    def test_upload_file_success(self) -> None:
        tmp = Path(tempfile.mktemp(suffix=".pdf"))
        tmp.write_bytes(b"%PDF test")
        result = self.storage.upload_file(tmp, "test.pdf")
        self.assertTrue(result)
        self.mock_client.upload_file.assert_called_once()
        tmp.unlink(missing_ok=True)

    def test_upload_file_failure(self) -> None:
        from botocore.exceptions import ClientError
        tmp = Path(tempfile.mktemp(suffix=".pdf"))
        tmp.write_bytes(b"%PDF test")
        self.mock_client.upload_file.side_effect = ClientError(
            {"Error": {"Code": "AccessDenied"}}, "PutObject"
        )
        result = self.storage.upload_file(tmp, "test.pdf")
        self.assertFalse(result)
        tmp.unlink(missing_ok=True)

    def test_delete_file_success(self) -> None:
        result = self.storage.delete_file("test.pdf")
        self.assertTrue(result)
        self.mock_client.delete_object.assert_called_once()

    def test_delete_file_failure(self) -> None:
        from botocore.exceptions import ClientError
        self.mock_client.delete_object.side_effect = ClientError(
            {"Error": {"Code": "AccessDenied"}}, "DeleteObject"
        )
        result = self.storage.delete_file("test.pdf")
        self.assertFalse(result)

    def test_delete_all(self) -> None:
        mock_paginator = MagicMock()
        mock_paginator.paginate.return_value = [
            {"Contents": [{"Key": "a.pdf"}, {"Key": "b.pdf"}]}
        ]
        self.mock_client.get_paginator.return_value = mock_paginator
        deleted = self.storage.delete_all()
        self.assertEqual(deleted, 2)

    def test_delete_all_empty_bucket(self) -> None:
        mock_paginator = MagicMock()
        mock_paginator.paginate.return_value = [{}]
        self.mock_client.get_paginator.return_value = mock_paginator
        deleted = self.storage.delete_all()
        self.assertEqual(deleted, 0)

    def test_list_files(self) -> None:
        mock_paginator = MagicMock()
        mock_paginator.paginate.return_value = [
            {
                "Contents": [
                    {
                        "Key": "a.pdf",
                        "Size": 1024,
                        "LastModified": MagicMock(
                            isoformat=lambda: "2024-01-01T00:00:00",
                        ),
                    },
                ]
            }
        ]
        self.mock_client.get_paginator.return_value = mock_paginator
        files = self.storage.list_files()
        self.assertEqual(len(files), 1)
        self.assertEqual(files[0]["key"], "a.pdf")
        self.assertEqual(files[0]["size"], 1024)

    def test_list_files_with_prefix(self) -> None:
        mock_paginator = MagicMock()
        mock_paginator.paginate.return_value = [{"Contents": []}]
        self.mock_client.get_paginator.return_value = mock_paginator
        self.storage.list_files(prefix="papers/")
        mock_paginator.paginate.assert_called_once_with(Bucket="test-bucket", Prefix="papers/")

    def test_get_bucket_info(self) -> None:
        mock_paginator = MagicMock()
        mock_paginator.paginate.return_value = [
            {
                "Contents": [
                    {"Key": "a.pdf", "Size": 1000},
                    {"Key": "b.pdf", "Size": 2000},
                ]
            }
        ]
        self.mock_client.get_paginator.return_value = mock_paginator
        info = self.storage.get_bucket_info()
        self.assertEqual(info["count"], 2)
        self.assertEqual(info["total_size_bytes"], 3000)

    def test_get_bucket_info_empty(self) -> None:
        mock_paginator = MagicMock()
        mock_paginator.paginate.return_value = [{}]
        self.mock_client.get_paginator.return_value = mock_paginator
        info = self.storage.get_bucket_info()
        self.assertEqual(info["count"], 0)
        self.assertEqual(info["total_size_bytes"], 0)

    def test_bucket_property(self) -> None:
        self.assertEqual(self.storage.bucket, "test-bucket")


if __name__ == "__main__":
    unittest.main()
