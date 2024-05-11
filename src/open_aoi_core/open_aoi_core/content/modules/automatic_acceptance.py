# Automatic acceptance
# This module accept all test zones automatically.

try:
    from open_aoi_core.content.modules import IModule  # Import module interface
except ImportError:
    import sys  # Add core library to the path for development (in production it will be available without this)

    sys.path.append("./src/open_aoi_core")
    from open_aoi_core.content.modules import IModule  # Import module interface


import numpy as np
from typing import List
from open_aoi_core.content.modules import IModule  # Import module interface

DOCUMENTATION = "Module accept product automatically. Takes not parameters"


class Module(IModule):
    def process(
        self,
        environment: dict,
        test_image: np.ndarray,
        template_image: np.array,
        inspection_zone_list: List[IModule.InspectionZone],
    ) -> List[IModule.InspectionLog]:
        return [
            IModule.InspectionLog("Accepted automatically.", True)
            for zone in inspection_zone_list
        ]


module = Module()
