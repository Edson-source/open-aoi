import numpy as np
from typing import List
from open_aoi_core.content.modules import IModule

DOCUMENTATION = "Module reject product automatically."


class Module(IModule):
    def process(
        self,
        environment: dict,
        test_image: np.ndarray,
        template_image: np.array,
        inspection_zone_list: List[IModule.InspectionZone],
    ) -> List[IModule.InspectionLog]:
        return [
            IModule.InspectionLog("Rejected automatically.", False)
            for zone in inspection_zone_list
        ]


module = Module()
