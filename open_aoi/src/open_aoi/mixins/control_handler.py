import io
from typing import Optional, Tuple

from minio import Minio
from uuid import uuid4

from open_aoi.settings import MINIO_PORT, MINIO_ACCESS_KEY, MINIO_SECRET_KEY
from open_aoi.exceptions import IntegrityError
from open_aoi.module import Module


class Mixin:
    handler_blob: str
    _bucket_name = "modules"

    def __init__(self):
        self._minio_client = Minio(
            f"127.0.0.1:{MINIO_PORT}",
            access_key=MINIO_ACCESS_KEY,
            secret_key=MINIO_SECRET_KEY,
            secure=False,
        )

    def validate_source(self, source: bytes) -> Tuple[bool, Optional[str]]:
        try:
            source = self._dynamic_import(source)
            Module.validate_specification(source)
        except Exception as e:
            return False, str(e)
        return True, None

    def upload_handler_source(self, content: bytes) -> str:
        assert getattr(self, "handler_blob", None) is None

        handler_blob = str(uuid4())

        if not self._minio_client.bucket_exists(self._bucket_name):
            self._minio_client.make_bucket(self._bucket_name)

        blob = io.BytesIO(content)
        blob.seek(0)
        self._minio_client.put_object(
            self._bucket_name, handler_blob, blob, len(content)
        )

        return handler_blob

    def materialize_handler_source(self) -> Module:
        assert getattr(self, "handler_blob") is not None

        if not self._minio_client.bucket_exists(self._bucket_name):
            raise IntegrityError("Module does not exist")

        obj = self._minio_client.get_object(self._bucket_name, self.handler_blob)
        source = self._dynamic_import(obj.read())
        obj.close()

        return Module(source)

    def _dynamic_import(self, source: bytes):
        """
        Import dynamically generated code as a module.
        """

        ctx = {}
        exec(source.decode(), ctx, ctx)
        return ctx


if __name__ == "__main__":
    m = Mixin()

    source = """
parameters = []
process = lambda: print('hello open-aoi!')
""".encode()

    print(m.validate_source(source))

    handler_blob = m.upload_handler_source(source)
    print(f"Module uploaded as: {handler_blob}")

    m.handler_blob = handler_blob
    materialized = m.materialize_handler_source()
    print(materialized)
