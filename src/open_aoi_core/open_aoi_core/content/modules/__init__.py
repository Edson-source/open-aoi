from typing import List
from dataclasses import dataclass

import numpy as np

from open_aoi_core.exceptions import InvalidAsset
from open_aoi_core.utils import crop_stat_cv


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
        # TODO: Rotation
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
        assert ctx.get("module") is not None, "Module instance function is missing!"
        assert isinstance(
            ctx.get("module"), IModule
        ), "Module does not provide IModule interface!"
    except AssertionError as e:
        raise InvalidAsset(f"Failed to validate module: {str(e)}") from e
    
    return ctx.get("module")
