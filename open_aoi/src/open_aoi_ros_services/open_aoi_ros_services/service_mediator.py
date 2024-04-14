"""
    This script is a definition of moderator node. Node control communication of other nodes with each other.
"""

import rclpy
import numpy as np
from sqlalchemy.orm import Session
from collections import defaultdict

from open_aoi_ros_interfaces.srv import InspectionTrigger, ImageAcquisition
from open_aoi_ros_interfaces.msg import ControlTarget, ConnectedComponent
from open_aoi_ros_services import StandardService
from open_aoi_core.constants import MediatorService
from open_aoi_core.models import ControlTargetModel, engine
from open_aoi_core.controllers.inspection_profile import InspectionProfileController


class Service(StandardService):
    NODE_NAME = MediatorService.NODE_NAME

    def __init__(self):
        super().__init__()
        # --- Services ---
        self.inspection_trigger_service = self.create_service(
            InspectionTrigger,
            f"{self.NODE_NAME}/execute_inspection",
            self.execute_inspection,
        )

    def execute_inspection(self, request, response):
        with Session(engine) as session:
            inspection_profile_controller = InspectionProfileController(session)

            try:
                inspection_profile = InspectionProfileController.retrieve(
                    request.inspection_profile_id
                )
            except Exception as e:
                self.logger.error(str(e))
                response.error = MediatorService.Error.GENERAL
                response.error_description = "Failed to retrieve inspection profile."
                return response

            try:
                camera = inspection_profile.camera
            except Exception as e:
                self.logger.error(str(e))
                response.error = MediatorService.Error.GENERAL
                response.error_description = "Failed to retrieve related camera."
                return response

            try:
                template = inspection_profile.template
            except Exception as e:
                self.logger.error(str(e))
                response.error = MediatorService.Error.GENERAL
                response.error_description = "Failed to retrieve related template."
                return response

            # Map each required control handler to related control zones
            # Retrieve control handler source
            try:
                control_handler_list = []
                control_handler_source_list = []
                control_handler_related_control_target_msg_map = defaultdict(list)

                control_zone_list = template.control_zone_list
                for cz in control_zone_list:
                    control_target_list = cz.control_target_list
                    for ct in control_target_list:
                        ch = ct.control_handler
                        if ch.id in control_handler_list:
                            continue
                        control_handler_list.append(ch.id)
                        source = ch.materialize_source().decode()
                        control_handler_source_list.append(source)
                        control_handler_related_control_target_msg_map[ch.id].append(
                            self._control_target_to_msg(ct)
                        )
            except Exception as e:
                self.logger.error(str(e))
                response.error = MediatorService.Error.RESOURCE_FAILED
                response.error_description = (
                    "Failed to retrieve related control handler."
                )
                return response
            
            # Image acquisition
            try:
                template_image = template.materialize_image()
                template_image = np.array(template_image)
            except Exception as e:
                self.logger.error(str(e))
                response.error = MediatorService.Error.RESOURCE_FAILED
                response.error_description = (
                    "Failed to retrieve related template."
                )
                return response
            
            try:
                image_acquisition_requiest = ImageAcquisition
                test_image = None
            except Exception as e:
                self.logger.error(str(e))
                response.error = MediatorService.Error.RESOURCE_FAILED
                response.error_description = (
                    "Failed to retrieve related template."
                )
                return response
            


    def _control_target_to_msg(ct: ControlTargetModel) -> ControlTarget:
        cz = ct.control_zone
        cc_msg = ConnectedComponent()
        cc_msg.stat_left = cz.cc.stat_left
        cc_msg.stat_top = cz.cc.stat_top
        cc_msg.stat_width = cz.cc.stat_width
        cc_msg.stat_height = cz.cc.stat_height
        ct_msg = ControlTarget()
        ct_msg.id = ct.id
        ct_msg.cc = cc_msg
        ct_msg.rotation = cz.rotation
        return ct_msg


def main(args=None):
    rclpy.init(args=args)
    service = Service()
    rclpy.spin(service)
    rclpy.shutdown()


if __name__ == "__main__":
    main()
