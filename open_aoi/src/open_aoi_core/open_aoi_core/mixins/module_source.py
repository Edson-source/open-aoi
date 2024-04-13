import io
import logging
from uuid import uuid4
from dataclasses import dataclass
from typing import Optional, Tuple, List

import numpy as np

from open_aoi_core.exceptions import IntegrityError, InvalidAsset
from open_aoi_core.utils import crop_stat_cv
from open_aoi_core.mixins import Mixin


logger = logging.getLogger("controller.control_handler")


class IModule:
    @dataclass
    class ControlZone:
        rotation: float
        stat_left: int
        stat_top: int
        stat_width: int
        stat_height: int

    @dataclass
    class ControlLog:
        log: str
        passed: bool

    def process(
        self,
        environment: dict,
        test_image: np.ndarray,
        template_image: np.array,
        control_zone_list: List[ControlZone],
    ) -> List[ControlLog]:
        raise NotImplementedError()

    def apply_control_zone(im: np.ndarray, control_zone: ControlZone) -> np.ndarray:
        stat = [
            control_zone.stat_left,
            control_zone.stat_top,
            control_zone.stat_width,
            control_zone.stat_height,
        ]
        chunk = crop_stat_cv(im, stat)
        #TODO: Rotation
        return chunk


def dynamic_import(source: bytes) -> IModule:
    """
    Import dynamically generated code as a module.
    """
    ctx = {}

    try:
        exec(source.decode(), ctx, ctx)
    except Exception as e:
        raise InvalidAsset(f"Failed to execute module: {str(e)}") from e

    try:
        assert ctx.get("DOCUMENTATION") is not None, "Documentation is missing!"
        assert ctx.get("module") is not None, "Process function is missing!"
        assert isinstance(
            ctx.get("module"), IModule
        ), "Module does not provide IModule interface!"
    except AssertionError as e:
        raise InvalidAsset(f"Failed to validate module: {str(e)}") from e


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
