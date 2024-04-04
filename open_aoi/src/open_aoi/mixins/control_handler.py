import io
from typing import Optional, Tuple, List


from minio import Minio
from uuid import uuid4

from open_aoi.settings import MINIO_PORT, MINIO_ACCESS_KEY, MINIO_SECRET_KEY
from open_aoi.exceptions import IntegrityError
from open_aoi.mixins import Mixin


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

    def __init__(self, specification: dict) -> None:
        self._spec = specification
        res, detail = self.validate_specification(specification)
        assert res, detail

        self.parameters = specification["parameters"]
        self.process = specification["process"]

    def process(self):
        raise NotImplemented()


class ModuleSourceMixin(Mixin):
    handler_blob: str
    _bucket_name = "modules"

    def publish_source(self, content: bytes) -> str:
        assert getattr(self, "handler_blob", None) is None
        client = self._get_client()

        handler_blob = str(uuid4())

        if not client.bucket_exists(self._bucket_name):
            client.make_bucket(self._bucket_name)

        blob = io.BytesIO(content)
        blob.seek(0)
        client.put_object(self._bucket_name, handler_blob, blob, len(content))

        return handler_blob

    def materialize_source(self) -> Module:
        assert getattr(self, "handler_blob") is not None
        client = self._get_client()

        if not client.bucket_exists(self._bucket_name):
            raise IntegrityError("Module does not exist")

        obj = client.get_object(self._bucket_name, self.handler_blob)
        source = self._dynamic_import(obj.read())
        obj.close()

        return Module(source)

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

    @staticmethod
    def _get_client():
        return Minio(
            f"127.0.0.1:{MINIO_PORT}",
            access_key=MINIO_ACCESS_KEY,
            secret_key=MINIO_SECRET_KEY,
            secure=False,
        )


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
