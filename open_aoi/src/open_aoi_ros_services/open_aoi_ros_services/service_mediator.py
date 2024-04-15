"""
    This script is a definition of moderator node. Node control communication of other nodes with each other.
"""

import rclpy
import numpy as np
from sqlalchemy.orm import Session
from collections import defaultdict

from rclpy.executors import MultiThreadedExecutor

from open_aoi_ros_interfaces.srv import InspectionTrigger
from open_aoi_ros_interfaces.msg import ControlTarget
from open_aoi_core.services import StandardService
from open_aoi_core.constants import (
    MediatorServiceConstants,
    ImageAcquisitionConstants,
    ControlExecutionConstants,
)
from open_aoi_core.models import ControlTargetModel, engine
from open_aoi_core.controllers.inspection_profile import InspectionProfileController
from open_aoi_core.utils import encode_image


class Service(StandardService):
    NODE_NAME = MediatorServiceConstants.NODE_NAME

    def __init__(self):
        super().__init__()

        self.inspection_trigger_service = self.create_service(
            InspectionTrigger,
            f"{self.NODE_NAME}/execute_inspection",
            self.execute_inspection,
        )
        self._await_dependencies(
            [
                self.image_acquisition_capture_cli,
                self.product_identification_get_barcode_cli,
                self.control_execution_execute_control_cli,
            ]
        )

    def execute_inspection(self, request, response):
        self.logger.info("Inspection requested")
        response.overall_passed = False

        with Session(engine) as session:
            inspection_profile_controller = InspectionProfileController(session)
            try:
                inspection_profile = inspection_profile_controller.retrieve(
                    request.inspection_profile_id
                )
            except Exception as e:
                self.logger.error(str(e))
                response.error = MediatorServiceConstants.Error.GENERAL
                response.error_description = "Failed to retrieve inspection profile."
                return response

            self.logger.info(
                f"Inspection profile retrieved [{inspection_profile.id}]: {inspection_profile.title}"
            )

            try:
                camera = inspection_profile.camera
            except Exception as e:
                self.logger.error(str(e))
                response.error = MediatorServiceConstants.Error.GENERAL
                response.error_description = "Failed to retrieve related camera."
                return response

            self.logger.info(f"Camera retrieved [{camera.id}]: {camera.title}")

            try:
                template = inspection_profile.template
            except Exception as e:
                self.logger.error(str(e))
                response.error = MediatorServiceConstants.Error.GENERAL
                response.error_description = "Failed to retrieve related template."
                return response

            self.logger.info(f"Template retrieved [{template.id}]: {template.title}")

            # Map each required control handler to related control zones
            # Retrieve control handler source
            try:
                control_handler_list = []
                control_handler_source_list = []
                control_handler_related_control_target_msg_map = defaultdict(list)

                control_zone_list = template.control_zone_list
                assert len(control_zone_list), "Control zone list is empty"

                for cz in control_zone_list:
                    control_target_list = cz.control_target_list
                    assert len(control_target_list), "Control target list is empty"

                    for ct in control_target_list:
                        ch = ct.control_handler
                        self.logger.info(
                            f"Registering control target [{ct.id}]: control zone: {cz.title}, control handler: {ch.title}"
                        )
                        control_handler_related_control_target_msg_map[ch.id].append(
                            self._control_target_to_msg(ct)
                        )

                        if ch.id in control_handler_list:
                            continue

                        control_handler_list.append(ch.id)
                        source = ch.materialize_source().decode()
                        control_handler_source_list.append(source)
            except Exception as e:
                self.logger.error(str(e))
                response.error = MediatorServiceConstants.Error.RESOURCE_FAILED
                response.error_description = (
                    "Failed to retrieve related control handler."
                )
                return response

            self.logger.info(f"Control handler retrieved and control targets are ready")

            # Image acquisition
            try:
                template_image = template.materialize_image()
                template_image = np.array(template_image)
                template_image_msg = encode_image(template_image)
            except Exception as e:
                self.logger.error(str(e))
                response.error = MediatorServiceConstants.Error.RESOURCE_FAILED
                response.error_description = "Failed to retrieve related template."
                return response

            self.logger.info(f"Template image retrieved: {template_image.shape}")

            try:
                # Do not decode image here, send directly to control execution
                test_image_msg, error, error_description = (
                    self.image_acquisition_capture_image_msg(camera.ip_address, True)
                )
            except Exception as e:
                self.logger.error(str(e))
                response.error = MediatorServiceConstants.Error.CAPTURE_FAILED
                response.error_description = "Failed to capture image."
                return response
            else:
                if error != ImageAcquisitionConstants.Error.NONE:
                    response.error = MediatorServiceConstants.Error.CAPTURE_FAILED
                    response.error_description = (
                        f"Failed to capture image. {error_description}"
                    )

            self.logger.info(f"Test image captured as message")

            for control_handler_id, control_handler_source in zip(
                control_handler_list, control_handler_source_list
            ):
                self.logger.info(f"Executing: {control_handler_id}")
                try:
                    target_list = control_handler_related_control_target_msg_map[
                        control_handler_id
                    ]
                    control_log_list, error, error_description = (
                        self.control_execution_execute_control(
                            template_image_msg,
                            test_image_msg,
                            control_handler_source,
                            inspection_profile.environment,
                            target_list,
                        )
                    )
                    if error != ControlExecutionConstants.Error.NONE:
                        self.logger.error(f"Failed to apply control execution. {error}: {error_description}")
                        response.error = MediatorServiceConstants.Error.CONTROL_FAILED
                        response.error_description = f"Failed to apply control handler {control_handler_id}. {error_description}"
                        return response
                except Exception as e:
                    self.logger.error(str(e))
                    response.error = MediatorServiceConstants.Error.CONTROL_FAILED
                    response.error_description = (
                        f"Failed to apply control handler {control_handler_id}."
                    )
                    return response
                self.logger.info(f"Completed: {control_handler_id}")

            return response

    @staticmethod
    def _control_target_to_msg(ct: ControlTargetModel) -> ControlTarget:
        ct_msg = ControlTarget()
        ct_msg.id = ct.id

        ct_msg.rotation = float(ct.control_zone.rotation)

        ct_msg.stat_left = ct.control_zone.cc.stat_left
        ct_msg.stat_top = ct.control_zone.cc.stat_top
        ct_msg.stat_width = ct.control_zone.cc.stat_width
        ct_msg.stat_height = ct.control_zone.cc.stat_height

        return ct_msg


def main(args=None):
    rclpy.init(args=args)
    executor = MultiThreadedExecutor(10)

    service = Service()
    executor.add_node(service)

    executor.spin()

    executor.shutdown()
    rclpy.shutdown()


if __name__ == "__main__":
    main()
