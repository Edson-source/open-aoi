"""
    Module provide image storing capabilities. Image is stored as blob on Minio blob storage.
    Mixin provide functions to publish (upload), materialize (download) and destroy (delete) image.
    Mixin does not commit anything to database, commit operation should be performed externally:
    ```
        template.publish_image(...)
        session.commit()
    ```
"""

import io

import numpy as np
from PIL import Image

from open_aoi_core.mixins import MinioBasedMixin
from open_aoi_core.constants import SystemBuckets
from open_aoi_core.exceptions import AssetIntegrityException


class ImageSourceMixin(MinioBasedMixin):
    image: np.ndarray  # Materialized image

    def publish_image(self, image: Image):
        """
        Upload image to storage.
        - raise: AssetIntegrityException if image already exist
        - raise: SystemIntegrityException if upload fails
        """

        blob_content = io.BytesIO()
        image.save(blob_content, format="PNG")
        self.publish(blob_content)
        self.image = np.array(image)

    def materialize_image(self) -> Image.Image:
        """
        Download image source and convert it to PIL image
        - raise: AssetIntegrityException if asset does not exist or is corrupted
        - raise: SystemIntegrityException if bucket does not exist or download failed
        """

        blob_content = self.materialize()
        try:
            image = Image.open(blob_content, formats=["PNG"])
        except Exception as e:
            raise AssetIntegrityException("Failed to convert asset to image.") from e
        self.image = np.array(image)
        return image

    def destroy_image(self):
        """
        Delete image source.
        - raise: AssetIntegrityException if image does not exist
        - raise: SystemIntegrityException if bucket does not exist or delete operation failed
        """
        self.destroy()
        self.image = None


class InspectionImageSourceMixin(ImageSourceMixin):
    _bucket_name = SystemBuckets.INSPECTION_IMAGES


class TemplateImageSourceMixin(ImageSourceMixin):
    _bucket_name = SystemBuckets.TEMPLATE_IMAGES
