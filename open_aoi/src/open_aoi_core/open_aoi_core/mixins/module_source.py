import io
import logging
from uuid import uuid4
from typing import Optional, Tuple

from open_aoi_core.mixins import Mixin
from open_aoi_core.content.modules import dynamic_import
from open_aoi_core.exceptions import IntegrityError, InvalidAsset


logger = logging.getLogger("controller.control_handler")


class ModuleSourceMixin(Mixin):
    handler_blob: Optional[str]
    _bucket_name = "modules"

    @property
    def is_valid(self):
        return getattr(self, "handler_blob", None) is not None

    def publish_source(self, content: bytes) -> str:
        assert getattr(self, "handler_blob", None) is None
        client = self._client

        handler_blob = str(uuid4())

        if not client.bucket_exists(self._bucket_name):
            client.make_bucket(self._bucket_name)

        blob = io.BytesIO(content)
        blob.seek(0)
        client.put_object(self._bucket_name, handler_blob, blob, len(content))

        self.handler_blob = handler_blob

    def materialize_source(self) -> bytes:
        assert getattr(self, "handler_blob") is not None
        client = self._client

        if not client.bucket_exists(self._bucket_name):
            raise IntegrityError("Module does not exist")

        obj = client.get_object(self._bucket_name, self.handler_blob)
        source = obj.read()
        obj.close()

        return source

    def destroy_source(self):
        assert getattr(self, "handler_blob") is not None
        client = self._client

        if not client.bucket_exists(self._bucket_name):
            raise IntegrityError("Module does not exist")

        client.remove_object(self._bucket_name, self.handler_blob)

        self.handler_blob = None

    @classmethod
    def validate_source(cls, source: bytes) -> Tuple[bool, Optional[str]]:
        try:
            dynamic_import(source)
        except InvalidAsset as e:
            return False, str(e)
        return True, None
