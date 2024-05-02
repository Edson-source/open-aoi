"""
    This script is a definition of moderator node. Node control communication of other nodes with each other.
    The basic function is to perform product inspection, which consists of the following steps:
    - Identify camera from request (by camera id or I/O pin id, which is related to camera)
    - Get test image
    - Identify product from test image
    - Get related inspection profile, template and control zone list
    - Iterate over control zones and get each used control handler
    - Pass control handler with related control zones to control executor and wait for logs
    - Create inspection profile and control logs records in database to store results
"""

import rclpy
import numpy as np
from PIL import Image
from sqlalchemy.orm import Session
from collections import defaultdict

from open_aoi_interfaces.srv import InspectionTrigger
from open_aoi_interfaces.msg import ControlTarget
from open_aoi_core.services import StandardService
from open_aoi_core.constants import (
    MediatorServiceConstants,
    ImageAcquisitionConstants,
    ControlExecutionConstants,
)
from open_aoi_core.models import ControlTargetModel, engine
from open_aoi_core.controllers.inspection_profile import InspectionProfileController
from open_aoi_core.controllers.inspection import InspectionController
from open_aoi_core.controllers.control_log import ControlLogController
from open_aoi_core.controllers.camera import CameraController
from open_aoi_core.utils import encode_image, decode_image


def _control_target_to_msg(ct: ControlTargetModel) -> ControlTarget:
    ct_msg = ControlTarget()
    ct_msg.id = ct.id

    ct_msg.rotation = float(ct.control_zone.rotation)

    ct_msg.stat_left = ct.control_zone.cc.stat_left
    ct_msg.stat_top = ct.control_zone.cc.stat_top
    ct_msg.stat_width = ct.control_zone.cc.stat_width
    ct_msg.stat_height = ct.control_zone.cc.stat_height

    return ct_msg


class Service(StandardService):
    NODE_NAME = MediatorServiceConstants.NODE_NAME

    def __init__(self):
        super().__init__()

        # Register inspection service
        self.inspection_trigger_service = self.create_service(
            InspectionTrigger,
            f"{self.NODE_NAME}/execute_inspection",
            self.execute_inspection,
            # callback_group=self._group,
        )
        # Wait for dependencies: image acquisition, product identification and control execution nodes
        self._await_dependencies(
            [
                self.image_acquisition_capture_cli,
                self.product_identification_get_barcode_cli,
                self.control_execution_execute_control_cli,
            ]
        )

    def execute_inspection(self, request, own_response):
        self.logger.info("Inspection requested")
        own_response.overall_passed = False

        with Session(engine) as session:
            # Node is going to communicate with database, so initiate controllers
            inspection_profile_controller = InspectionProfileController(session)
            inspection_controller = InspectionController(session)
            control_log_controller = ControlLogController(session)
            camera_controller = CameraController(session)

            # Camera identification
            if request.camera_id_valid:
                # Particular camera has been requested (request comes from UI)
                try:
                    camera = camera_controller.retrieve(request.camera_id)
                except Exception as e:
                    self.logger.error(str(e))
                    response.error = MediatorServiceConstants.Error.GENERAL
                    response.error_description = (
                        "Failed to retrieve related camera by id."
                    )
                    return response
            elif request.io_pin_valid:
                # Particular pin was triggered (request comes from GPIO interface)
                # Get camera with provided pin.
                try:
                    camera = camera_controller.retrieve_by_io_pin(request.io_pin)
                except Exception as e:
                    self.logger.error(str(e))
                    response.error = MediatorServiceConstants.Error.GENERAL
                    response.error_description = (
                        "Failed to retrieve related camera by I/O pin."
                    )
                    return response
            else:
                # No camera - no candies
                self.logger.warning("Camera identification not provided")
                own_response.error = MediatorServiceConstants.Error.GENERAL
                own_response.error_description = "No camera identification provided."
                return own_response

            self.logger.info(f"Camera retrieved [{camera.id}]: {camera.title}")

            # Capture test image
            future = self.image_acquisition_capture_image(camera.ip_address, True)
            response = self._await_future(future)
            if response.error != ImageAcquisitionConstants.Error.NONE:
                own_response.error = MediatorServiceConstants.Error.CAPTURE_FAILED
                own_response.error_description = (
                    f"Failed to capture image. {response.error_description}"
                )
                return own_response
            test_image_msg = response.image
            self.logger.info(f"Test image captured as message")

            # Product identification
            future = self.product_identification_get_barcode(test_image_msg)
            # Decode test image while waiting for response (will be used for logging purposed)
            test_image = decode_image(test_image_msg)
            response = self._await_future(future)

            self.logger.info(f"Test image captured as message")

            try:
                assert (
                    response.identification_code is not None
                    and response.identification_code.strip()
                )
            except AssertionError:
                own_response.error = (
                    MediatorServiceConstants.Error.IDENTIFICATION_FAILED
                )
                own_response.error_description = f"Failed to identify product."
                return own_response

            # Inspection profile retrieval
            try:
                inspection_profile = (
                    inspection_profile_controller.retrieve_by_identification_code(
                        response.identification_code
                    )
                )
                assert (
                    inspection_profile is not None
                ), "Inspection profile not detected by product code"
            except Exception as e:
                self.logger.error(str(e))
                own_response.error = MediatorServiceConstants.Error.GENERAL
                own_response.error_description = (
                    "Failed to retrieve inspection profile. Is profile active?"
                )
                return own_response

            self.logger.info(
                f"Inspection profile retrieved [{inspection_profile.id}]: {inspection_profile.title}"
            )

            # Template retrieval
            try:
                template = inspection_profile.template
            except Exception as e:
                self.logger.error(str(e))
                own_response.error = MediatorServiceConstants.Error.GENERAL
                own_response.error_description = "Failed to retrieve related template."
                return own_response

            self.logger.info(f"Template retrieved [{template.id}]: {template.title}")

            # Map each required control handler to related control zones
            # Retrieve control handler source
            control_handler_list = []
            control_handler_source_list = []
            control_handler_related_control_target_msg_map = defaultdict(list)
            try:
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
                            _control_target_to_msg(ct)
                        )

                        if ch.id in control_handler_list:
                            continue

                        control_handler_list.append(ch.id)
                        # Materialize control handler source
                        source = ch.materialize_source().decode()
                        control_handler_source_list.append(source)
            except Exception as e:
                self.logger.error(str(e))
                own_response.error = MediatorServiceConstants.Error.RESOURCE_FAILED
                own_response.error_description = (
                    "Failed to retrieve related control handler."
                )
                return own_response

            self.logger.info(f"Control handler retrieved and control targets are ready")

            # Template image materialization

            try:
                template_image = template.materialize_image()
                template_image = np.array(template_image)
                template_image_msg = encode_image(template_image)
            except Exception as e:
                self.logger.error(str(e))
                own_response.error = MediatorServiceConstants.Error.RESOURCE_FAILED
                own_response.error_description = "Failed to retrieve related template."
                return own_response

            self.logger.info(f"Template image retrieved: {template_image.shape}")

            control_target_list_full_msg = []
            control_log_list_full_msg = []
            for control_handler_id, control_handler_source in zip(
                control_handler_list, control_handler_source_list
            ):
                self.logger.info(f"Executing: {control_handler_id}")
                try:
                    control_target_list = (
                        control_handler_related_control_target_msg_map[
                            control_handler_id
                        ]
                    )
                    future = self.control_execution_execute_control(
                        template_image_msg,
                        test_image_msg,
                        control_handler_source,
                        inspection_profile.environment,
                        control_target_list,
                    )
                    response = self._await_future(future)
                    if response.error != ControlExecutionConstants.Error.NONE:
                        self.logger.error(
                            f"Failed to apply control execution. {response.error}: {response.error_description}"
                        )
                        own_response.error = (
                            MediatorServiceConstants.Error.CONTROL_FAILED
                        )
                        own_response.error_description = f"Failed to apply control handler {control_handler_id}. {error_description}"
                        return own_response
                    for control_target, control_log in zip(
                        control_target_list, response.control_log_list
                    ):
                        assert (
                            control_target.id == control_log.id
                        ), "Control log disorder detected."

                    # Collect all logs before creating inspection record
                    control_target_list_full_msg.extend(control_target_list)
                    control_log_list_full_msg.extend(response.control_log_list)
                except Exception as e:
                    self.logger.error(str(e))
                    own_response.error = MediatorServiceConstants.Error.CONTROL_FAILED
                    own_response.error_description = (
                        f"Failed to apply control handler {control_handler_id}."
                    )
                    return own_response
                self.logger.info(f"Completed: {control_handler_id}")

            self.logger.info(f"Control execution completed")

            try:
                inspection = inspection_controller.create(inspection_profile)
                inspection.publish_image(Image.fromarray(test_image))
                for control_target, control_log in zip(
                    control_target_list_full_msg, control_log_list_full_msg
                ):
                    control_log_controller.create(
                        control_target, inspection, control_log.log, control_log.passed
                    )
                inspection_controller.commit()
            except Exception as e:
                self.logger.error(str(e))
                own_response.error = MediatorServiceConstants.Error.CONTROL_FAILED
                own_response.error_description = f"Failed to store inspection results."
                return own_response

            own_response.overall_passed = all(
                [cl.passed for cl in control_log_list_full_msg]
            )
            own_response.image = test_image_msg
            own_response.control_log_list = control_log_list_full_msg
            own_response.control_target_list = control_target_list_full_msg
            own_response.error = MediatorServiceConstants.Error.NONE

            self.logger.info(f"Response constructed and returned")
            return own_response


def main(args=None):
    rclpy.init(args=args)

    service = Service()

    # Use multithread executor to be avoid deadlocks while awaiting services responses
    executor = rclpy.executors.MultiThreadedExecutor()
    executor.add_node(service)
    executor.spin()

    executor.shutdown()
    rclpy.shutdown()


if __name__ == "__main__":
    main()
