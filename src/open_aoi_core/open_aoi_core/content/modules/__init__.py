from typing import List
from dataclasses import dataclass

import numpy as np

from open_aoi_core.exceptions import AssetIntegrityException
from open_aoi_core.utils import crop_stat_cv


class IModule:
    @dataclass
    class InspectionZone:
        rotation: float
        stat_left: int
        stat_top: int
        stat_width: int
        stat_height: int

    @dataclass
    class InspectionLog:
        log: str
        passed: bool

    def process(
        self,
        environment: dict,
        test_image: np.ndarray,
        template_image: np.array,
        inspection_zone_list: List[InspectionZone],
    ) -> List[InspectionLog]:
        raise NotImplementedError()

    def apply_inspection_zone(im: np.ndarray, inspection_zone: InspectionZone) -> np.ndarray:
        stat = [
            inspection_zone.stat_left,
            inspection_zone.stat_top,
            inspection_zone.stat_width,
            inspection_zone.stat_height,
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
        raise AssetIntegrityException(f"Failed to execute module: {str(e)}") from e

    try:
        assert ctx.get("DOCUMENTATION") is not None, "Documentation is missing."
        assert ctx.get("module") is not None, "Module instance function is missing."
        assert isinstance(
            ctx.get("module"), IModule
        ), "Module does not provide IModule interface."
    except AssertionError as e:
        raise AssetIntegrityException(f"Failed to validate module: {str(e)}") from e
    
    return ctx.get("module")
