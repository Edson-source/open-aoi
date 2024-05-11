# [Name of the module]
# This module identify [defect type] defects.

import numpy as np
from typing import List

try:
    from open_aoi_core.content.modules import IModule  # Import module interface
except ImportError:
    import sys  # Add core library to the path for development (in production it will be available without this)

    sys.path.append("./src/open_aoi_core")
    from open_aoi_core.content.modules import IModule  # Import module interface


DOCUMENTATION = """
This is sample module that logs inspection zone index and allow all zones to pass.

Required parameters
- VERY_IMPORTANT_PARAMETER: A string that is important
"""


class Module(IModule):
    def process(
        self,
        environment: dict,
        test_image: np.ndarray,
        template_image: np.ndarray,
        inspection_zone_list: List[IModule.InspectionZone],
    ) -> List[IModule.InspectionLog]:
        VERY_IMPORTANT_PARAMETER = environment["VERY_IMPORTANT_PARAMETER"]

        inspection_log_list = []
        for i, zone in enumerate(inspection_zone_list):

            # test_chunk = self.cut_inspection_zone(test_image, zone)
            # template_chunk = self.cut_inspection_zone(template_image, zone)

            inspection_log_list.append(
                IModule.InspectionLog(
                    f"Important: {VERY_IMPORTANT_PARAMETER}. Index: {i}", True
                )
            )
        return inspection_log_list


module = Module()
