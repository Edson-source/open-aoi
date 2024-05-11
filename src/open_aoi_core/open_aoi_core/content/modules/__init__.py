from typing import List, Tuple
from dataclasses import dataclass

import numpy as np

from open_aoi_core.utils_basic import crop_stat_cv
from open_aoi_core.exceptions import AssetIntegrityException

class IModule:
    """
    Class define interface for custom modules. Custom module is single python file, that contains
    global variable named `module` of class, that realize IModule interface and global variable
    named `DOCUMENTATION` of type string, which describes documentation for module.

    Example (my_fancy_module.py):
    ```
        from open_aoi_core.content.modules import IModule
        # Import any installed library, like opencv, numpy, etc...
        # Do not import other open_aoi packages and do not call Open AOI services (may break the system)


        # Required
        DOCUMENTATION = "This is my module. No environment variable (parameters are used). Module does nothing."


        class Module(IModule):
            def process(
                self,
                environment,  # Dictionary with key-value pairs defined in inspection profile (describe in documentation what you need to be there)
                test_image,  # Full size raw test image
                template_image,  # Full size raw template image
                inspection_zone_list  # List of inspection zone coordinates (length of returned log list MUST match length of inspection zone list)
            ):
                accept = True
                reject = False
                return [
                    self.InspectionLog("My module thinks that this inspection zone is OK... or it is not.", accept)
                    for chunk in inspection_zone_list
                ]

        # Required
        module = Module()
    ```
    """

    @dataclass
    class InspectionZone:
        """
        Class that represent inspection zone coordinates on template and test images. Use
        `open_aoi_core.utils` crop functions to crop each zone after preprocessing the images as needed.
        """

        rotation: float
        stat_left: int
        stat_top: int
        stat_width: int
        stat_height: int

    @dataclass
    class InspectionLog:
        """
        Class that represent result of the inspection process. Set passed flag to False to indicate rejection of
        the zone (defect is present) or to True to indicate that zone has no defect. Log is a free form optional inspection message.
        """

        log: str
        passed: bool

    def cut_inspection_zone(
        im: np.ndarray, inspection_zone: InspectionZone
    ) -> np.ndarray:
        """Cut chunk from provided image with provided inspection zone"""
        # TODO: Apply rotation
        stat = [
            inspection_zone.stat_left,
            inspection_zone.stat_top,
            inspection_zone.stat_width,
            inspection_zone.stat_height,
        ]
        chunk = crop_stat_cv(im, stat)
        return chunk

    def process(
        self,
        environment: dict,
        test_image: np.ndarray,
        template_image: np.array,
        inspection_zone_list: List[InspectionZone],
    ) -> List[InspectionLog]:
        raise NotImplementedError()


def _dynamic_import(source: bytes) -> Tuple[IModule, str]:
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

    return ctx.get("module"), ctx.get("DOCUMENTATION")
