import io
import logging
from typing import Optional, Tuple, List


from uuid import uuid4

from open_aoi.exceptions import IntegrityError
from open_aoi.mixins import Mixin


logger = logging.getLogger("controller.control_handler")


class Module:
    parameters: List

    @staticmethod
    def validate_specification(specification: dict) -> Tuple[bool, Optional[str]]:
        try:
            assert (
                specification.get("parameters") is not None
            ), "Parameters are missing!"
            assert (
                specification.get("process") is not None
            ), "Process function is missing!"
        except Exception as e:
            return False, str(e)
        return True, None

    def __init__(self, specification: dict, source: bytes) -> None:
        self._spec = specification
        self._source = source
        res, detail = self.validate_specification(specification)
        assert res, detail

        self.parameters = specification["parameters"]
        self.process = specification["process"]

    def process(self):
        raise NotImplementedError()


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

    def materialize_source(self) -> Module:
        assert getattr(self, "handler_blob") is not None
        client = self._client

        if not client.bucket_exists(self._bucket_name):
            raise IntegrityError("Module does not exist")

        obj = client.get_object(self._bucket_name, self.handler_blob)
        source = obj.read()
        obj.close()

        return Module(self._dynamic_import(source), source)

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
            source = cls._dynamic_import(source)
            Module.validate_specification(source)
        except Exception as e:
            return False, str(e)
        return True, None

    @staticmethod
    def _dynamic_import(source: bytes):
        """
        Import dynamically generated code as a module.
        """

        ctx = {}
        exec(source.decode(), ctx, ctx)
        return ctx
