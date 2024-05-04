"""
    Module provide extended capabilities for database models in form of mixins.
    Mixin may be independent, like authentication mixin or may require some external services,
    like Minio based mixins, which require Minio blob storage.
"""

import io
from uuid import uuid4
from typing import Optional

import urllib3
from minio import Minio

from open_aoi_core.exceptions import (
    ConnectionFailedException,
    SystemIntegrityException,
    AssetIntegrityException,
)
from open_aoi_core.settings import (
    MINIO_ROOT_USER,
    MINIO_ROOT_PASSWORD,
    MINIO_HOST,
    MINIO_PORT,
)


class Mixin:
    pass


class MinioBasedMixin(Mixin):
    blob: Optional[str]  # Blob name. If missing, asset has never been published
    _bucket_name: str  # Name of bucked with content

    _minio_client = Minio(
        f"{MINIO_HOST}:{MINIO_PORT}",
        access_key=MINIO_ROOT_USER,
        secret_key=MINIO_ROOT_PASSWORD,
        secure=False,
        http_client=urllib3.PoolManager(num_pools=10, timeout=10, retries=2),
    )

    @property
    def has_source_blob(self) -> bool:
        """Test if record has blob to materialize"""
        return getattr(self, "blob", None) is not None

    @classmethod
    def test_minio_connection(cls):
        """
        Test connection to Minio blob storage service.
        - raise: ConnectionFailedException if connection fails
        """
        try:
            client = cls._minio_client
            client.bucket_exists("ignore")
        except Exception as e:
            raise ConnectionFailedException("Could not connect to Minio server.") from e

    def publish(self, blob_content: io.BytesIO):
        """
        Upload content to storage.
        - raise: SystemIntegrityException if upload fails
        - raise: AssetIntegrityException if asset already exist
        """
        try:
            assert getattr(self, "blob", None) is None
        except AssertionError as e:
            raise AssetIntegrityException(
                "Asset already exist. Overrides are not permitted."
            ) from e

        try:
            # Check bucket exists
            client = self._minio_client
            if not client.bucket_exists(self._bucket_name):
                client.make_bucket(self._bucket_name)

            # Create blob name and content
            blob_name = str(uuid4())

            length = blob_content.tell()
            blob_content.seek(0)

            # Upload
            client.put_object(self._bucket_name, blob_name, blob_content, length)
        except Exception as e:
            raise SystemIntegrityException("Failed to upload asset to storage.") from e

        self.blob = blob_name

    def materialize(self) -> io.BytesIO:
        """
        Download content from storage.
        - raise: AssetIntegrityException if asset does not exist
        - raise: SystemIntegrityException if bucket does not exist or download failed
        """
        try:
            assert getattr(self, "blob") is not None
        except AssertionError as e:
            raise AssetIntegrityException("Asset does not have source.") from e

        # Check bucket
        client = self._client
        if not client.bucket_exists(self._bucket_name):
            raise SystemIntegrityException(
                f"Bucket {self._bucket_name} does not exist, but asset blob is defined ({self.blob})."
            )

        # Download source
        try:
            blob_content = io.BytesIO()
            content = client.get_object(self._bucket_name, self.blob)
            blob_content.write(content.read())
            content.close()
        except Exception as e:
            raise SystemIntegrityException(
                "Failed to download content from storage."
            ) from e

        return blob_content

    def destroy(self):
        """
        Delete source at storage.
        - raise: AssetIntegrityException if asset does not exist
        - raise: SystemIntegrityException if bucket does not exist or delete operation failed
        """
        try:
            assert getattr(self, "blob") is not None
        except AssertionError as e:
            raise AssetIntegrityException("Asset does not have source.") from e

        # Check bucket
        client = self._client
        if not client.bucket_exists(self._bucket_name):
            raise SystemIntegrityException(
                f"Bucket {self._bucket_name} does not exist, but asset blob is defined ({self.blob})."
            )

        try:
            client.remove_object(self._bucket_name, self.blob)
        except Exception as e:
            raise SystemIntegrityException("Failed to destroy asset source.") from e

        self.blob = None
