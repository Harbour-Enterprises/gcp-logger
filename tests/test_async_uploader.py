# File: tests/test_async_uploader.py

from unittest.mock import MagicMock, patch

import pytest

from src.gcp_logger.async_uploader import AsyncUploader


@pytest.fixture
def async_uploader():
    with patch("src.gcp_logger.async_uploader.Storage"):
        return AsyncUploader(bucket_name="test-bucket")


@pytest.mark.asyncio
async def test_async_uploader_initialization(async_uploader):
    assert async_uploader.bucket_name == "test-bucket"
    assert async_uploader.loop is not None
    assert async_uploader.loop_thread.is_alive()


@pytest.mark.asyncio
async def test_initialize_storage_client(async_uploader):
    with patch("src.gcp_logger.async_uploader.Storage") as mock_storage:
        await async_uploader._initialize_storage_client()
        mock_storage.assert_called_once()


@pytest.mark.asyncio
async def test_async_upload(async_uploader):
    mock_storage_client = MagicMock()
    async_uploader.storage_client = mock_storage_client

    await async_uploader._async_upload(b"test data", "test_object")

    mock_storage_client.upload.assert_called_once_with(
        bucket="test-bucket", object_name="test_object", file_data=b"test data"
    )


def test_upload_data(async_uploader):
    with patch.object(async_uploader, "_async_upload") as mock_async_upload:
        async_uploader.upload_data(b"test data", "test_object")
        assert mock_async_upload.called
