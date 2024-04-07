import io
import logging
import numpy as np
from uuid import uuid4
from typing import Optional

from PIL import Image

from open_aoi.mixins import Mixin
from open_aoi.exceptions import IntegrityError

logger = logging.getLogger("controller.template")


class ImageSourceMixin(Mixin):
    image: np.ndarray
    image_blob: Optional[str]

    _bucket_name = "templates"

    @property
    def is_valid(self):
        return getattr(self, "image_blob", None) is not None

    def publish_image(self, im: Image):
        assert getattr(self, "image_blob", None) is None
        client = self._client

        if not client.bucket_exists(self._bucket_name):
            client.make_bucket(self._bucket_name)

        image_blob = str(uuid4())
        blob = io.BytesIO()

        im.save(blob, format="PNG")
        length = blob.tell()
        blob.seek(0)

        client.put_object(self._bucket_name, image_blob, blob, length)

        self.image_blob = image_blob

    def materialize_image(self) -> Image.Image:
        assert getattr(self, "image_blob") is not None
        client = self._client

        if not client.bucket_exists(self._bucket_name):
            raise IntegrityError("Image does not exist")

        obj = client.get_object(self._bucket_name, self.image_blob)
        im = Image.open(obj, formats=["PNG"])
        obj.close()

        return im

    def destroy_image(self):
        assert getattr(self, "image_blob") is not None
        client = self._client

        if not client.bucket_exists(self._bucket_name):
            raise IntegrityError("Image does not exist")

        client.remove_object(self._bucket_name, self.image_blob)

        self.image_blob = None
