from typing import List
from dataclasses import dataclass

import numpy as np


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

    def process(
        self,
        environment: dict,
        test_image: np.ndarray,
        test_image_chunk_list: List[np.ndarray],
        template_image: np.array,
        template_image_chunk_list: List[np.ndarray],
        inspection_zone_list: List[InspectionZone],
    ) -> List[InspectionLog]:
        raise NotImplementedError()
