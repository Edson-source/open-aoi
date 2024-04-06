import io
import urllib3
import logging
from typing import Optional, Tuple, List


from minio import Minio
from uuid import uuid4

from open_aoi.settings import MINIO_PORT, MINIO_ACCESS_KEY, MINIO_SECRET_KEY
from open_aoi.exceptions import IntegrityError, ConnectivityError
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
        raise NotImplemented()


class ModuleSourceMixin(Mixin):
    handler_blob: Optional[str]
    _bucket_name = "modules"
    _client = Minio(
        f"127.0.0.1:{MINIO_PORT}",
        access_key=MINIO_ACCESS_KEY,
        secret_key=MINIO_SECRET_KEY,
        secure=False,
        http_client=urllib3.PoolManager(num_pools=10, timeout=10, retries=2),
    )

    @property
    def is_valid(self):
        return self.handler_blob is not None

    def publish_source(self, content: bytes) -> str:
        assert getattr(self, "handler_blob", None) is None
        client = self._client

        handler_blob = str(uuid4())

        if not client.bucket_exists(self._bucket_name):
            client.make_bucket(self._bucket_name)

        blob = io.BytesIO(content)
        blob.seek(0)
        client.put_object(self._bucket_name, handler_blob, blob, len(content))

        return handler_blob

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

    @classmethod
    def test_store_connection(cls):
        try:
            client = cls._client
            client.bucket_exists("ignore")
        except Exception as e:
            logger.error("Could not connect to source code storage.")
            logger.exception(e)
            raise ConnectivityError("Could not connect to source code storage.") from e

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


if __name__ == "__main__":
    m = ModuleSourceMixin()

    source = """
parameters = []
process = lambda: print('hello open-aoi!')
""".encode()

    print(m.validate_source(source))

    handler_blob = m.publish_source(source)
    print(f"Module uploaded as: {handler_blob}")

    m.handler_blob = handler_blob
    materialized = m.materialize_handler_source()
    print(materialized)
