import urllib3
from minio import Minio

from open_aoi.settings import MINIO_PORT, MINIO_ROOT_USER, MINIO_ROOT_PASSWORD
from open_aoi.exceptions import ConnectivityError


class Mixin:
    id: int

    _client = Minio(
        f"127.0.0.1:{MINIO_PORT}",
        access_key=MINIO_ROOT_USER,
        secret_key=MINIO_ROOT_PASSWORD,
        secure=False,
        http_client=urllib3.PoolManager(num_pools=10, timeout=10, retries=2),
    )

    @classmethod
    def test_store_connection(cls):
        try:
            client = cls._client
            client.bucket_exists("ignore")
        except Exception as e:
            raise ConnectivityError("Could not connect to source code storage.") from e
