"""
    Module provide inspection handler storing capabilities. Inspection handler code is stored as bytes on Minio blob storage.
    Module provide functions to publish, materialize and destroy inspection handler source.
"""

import io
from typing import Optional, Tuple

from open_aoi_core.mixins import MinioBasedMixin
from open_aoi_core.constants import SystemBuckets
from open_aoi_core.content.modules import _dynamic_import
from open_aoi_core.exceptions import AssetIntegrityException


class ModuleSourceMixin(MinioBasedMixin):
    _bucket_name = SystemBuckets.MODULE_SOURCES

    # Module source
    source: Optional[bytes] = None

    def publish_source(self, source: bytes):
        """
        Upload content to storage.
        - raise: SystemIntegrityException if upload fails
        - raise: AssetIntegrityException if asset already exist
        """
        blob_content = io.BytesIO()
        blob_content.write(source)
        self.publish(blob_content)
        doc = self.get_source_documentation(source)
        self.description = doc
        self.source = source

    def materialize_source(self) -> bytes:
        """
        Download content from storage.
        - raise: AssetIntegrityException if asset does not exist
        - raise: SystemIntegrityException if bucket does not exist or download failed
        """
        blob_content = self.materialize()
        source = blob_content.read()
        self.source = source
        return source

    def destroy_source(self):
        """
        Delete source at storage.
        - raise: AssetIntegrityException if asset does not exist
        - raise: SystemIntegrityException if bucket does not exist or delete operation failed
        """
        self.destroy()
        self.source = None

    @classmethod
    def validate_source(cls, source: bytes) -> Tuple[bool, str]:
        """Validate modules content (python code). Call before uploading source to storage."""
        try:
            _dynamic_import(source)
        except AssetIntegrityException as e:
            return False, str(e)
        return True, "Module is valid."

    @classmethod
    def get_source_documentation(cls, source: bytes) -> str:
        """Return documentation from module source."""
        try:
            _, doc = _dynamic_import(source)
            return doc
        except AssetIntegrityException as e:
            return "No documentation available"
