# File: gcp_logger/async_uploader.py

import asyncio
import logging
import threading

from gcloud.aio.storage import Storage
from google.api_core import exceptions as google_exceptions

from .internal_logger import internal_debug


class AsyncUploader:
    def __init__(self, bucket_name: str):
        """
        Initializes the AsyncUploader with the specified GCS bucket.

        Args:
            bucket_name (str): The name of the Google Cloud Storage bucket.
        """
        self.bucket_name = bucket_name
        self.loop = asyncio.new_event_loop()
        self.loop_thread = threading.Thread(target=self._run_loop, daemon=True)
        self.loop_thread.start()
        self.storage_client = None  # Will be initialized asynchronously
        internal_debug("AsyncUploader: Initialized with bucket '%s'.", self.bucket_name)

    def _run_loop(self):
        """
        Runs the asyncio event loop indefinitely in a separate thread.
        """
        asyncio.set_event_loop(self.loop)
        self.loop.run_forever()

    async def _initialize_storage_client(self):
        """
        Initializes the Storage client asynchronously.
        """
        if not self.storage_client:
            try:
                self.storage_client = Storage()
                internal_debug("AsyncUploader: Storage client initialized.")
            except Exception as e:
                logging.error("AsyncUploader: Failed to initialize Storage client: %s", e)

    def upload_data(self, data: bytes, object_name: str):
        """
        Schedules the asynchronous upload of data to GCS.

        Args:
            data (bytes): The data to upload.
            object_name (str): The name of the object in GCS.
        """
        future = asyncio.run_coroutine_threadsafe(self._async_upload(data, object_name), self.loop)
        internal_debug("AsyncUploader: Scheduled upload for object '%s'.", object_name)
        return future

    async def _async_upload(self, data: bytes, object_name: str):
        """
        Asynchronously uploads data to GCS.

        Args:
            data (bytes): The data to upload.
            object_name (str): The name of the object in GCS.
        """
        try:
            # Initialize the storage client if not already done
            await self._initialize_storage_client()

            # Upload the data to the specified bucket and object name
            await self.storage_client.upload(
                bucket=self.bucket_name,
                object_name=object_name,
                file_data=data,
                # Optionally, you can set additional parameters like content_type
                # content_type='text/plain'
            )
            logging.info(
                "AsyncUploader: Successfully uploaded '%s' to bucket '%s'.",
                object_name,
                self.bucket_name,
            )
        except google_exceptions.GoogleAPICallError as e:
            logging.error(
                "AsyncUploader: Google API call failed while uploading '%s' to bucket '%s': %s",
                object_name,
                self.bucket_name,
                e,
            )
        except Exception as e:
            logging.error(
                "AsyncUploader: An unexpected error occurred while uploading '%s': %s",
                object_name,
                e,
            )

    def shutdown(self):
        """
        Gracefully shuts down the event loop and background thread.
        """
        if self.storage_client:
            future = asyncio.run_coroutine_threadsafe(self.storage_client.close(), self.loop)
            try:
                future.result(timeout=5)
                internal_debug("AsyncUploader: Storage client closed.")
            except Exception as e:
                logging.error("AsyncUploader: Error closing storage client: %s", e)

        self.loop.call_soon_threadsafe(self.loop.stop)
        self.loop_thread.join()
        internal_debug("AsyncUploader: Event loop stopped and thread joined.")
