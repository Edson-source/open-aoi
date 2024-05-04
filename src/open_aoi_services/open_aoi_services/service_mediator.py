"""
    This script is a definition of moderator node. Node inspection communication of other nodes with each other.
    The basic function is to perform product inspection, which consists of the following steps:
    - Identify camera from request (by camera id or I/O pin id, which is related to camera)
    - Get test image
    - Identify product from test image
    - Get related inspection profile, template and inspection zone list
    - Iterate over inspection zones and get each used inspection handler
    - Pass inspection handler with related inspection zones to inspection executor and wait for logs
    - Create inspection profile and inspection logs records in database to store results
"""

import rclpy
import numpy as np
from PIL import Image
from sqlalchemy.orm import Session
from collections import defaultdict

from open_aoi_interfaces.srv import InspectionTrigger
from open_aoi_interfaces.msg import InspectionTarget
from open_aoi_core.services import StandardService
from open_aoi_core.constants import (
    MediatorServiceConstants,
    ImageAcquisitionConstants,
    InspectionExecutionConstants,
)
from open_aoi_core.models import InspectionTargetModel, engine
from open_aoi_core.controllers.inspection_profile import InspectionProfileController
from open_aoi_core.controllers.inspection import InspectionController
from open_aoi_core.controllers.inspection_log import InspectionLogController
from open_aoi_core.controllers.camera import CameraController
from open_aoi_core.utils import image_to_msg, msg_to_image


def _inspection_target_to_msg(ct: InspectionTargetModel) -> InspectionTarget:
    ct_msg = InspectionTarget()
    ct_msg.id = ct.id

    ct_msg.rotation = float(ct.inspection_zone.rotation)

    ct_msg.stat_left = ct.inspection_zone.cc.stat_left
    ct_msg.stat_top = ct.inspection_zone.cc.stat_top
    ct_msg.stat_width = ct.inspection_zone.cc.stat_width
    ct_msg.stat_height = ct.inspection_zone.cc.stat_height

    return ct_msg


class Service(StandardService):
    NODE_NAME = MediatorServiceConstants.NODE_NAME

    def __init__(self):
        super().__init__()

        # Register inspection service
        self.inspection_trigger_service = self.create_service(
            InspectionTrigger,
            f"{self.NODE_NAME}/inspection",
            self.execute_inspection,
            # callback_group=self._group,
        )
        # Wait for dependencies: image acquisition, product identification and inspection execution nodes
        self.await_dependencies(
            [
                self.image_acquisition_capture_cli,
                self.product_identification_get_barcode_cli,
                self.inspection_execution_execute_inspection_cli,
            ]
        )

    def execute_inspection(self, request, response):
        self.logger.info("Inspection requested")
        response.overall_passed = False

        with Session(engine) as session:
            # Node is going to communicate with database, so initiate controllers
            inspection_profile_controller = InspectionProfileController(session)
            inspection_controller = InspectionController(session)
            inspection_log_controller = InspectionLogController(session)
            camera_controller = CameraController(session)

            # Camera identification
            if request.camera_id_valid:
                # Particular camera has been requested (request comes from UI)
                try:
                    camera = camera_controller.retrieve(request.camera_id)
                except Exception as e:
                    self.logger.error(str(e))
                    sub_response.error = MediatorServiceConstants.Error.GENERAL
                    sub_response.error_description = (
                        "Failed to retrieve related camera by id."
                    )
                    return sub_response
            elif request.io_pin_valid:
                # Particular pin was triggered (request comes from GPIO interface)
                # Get camera with provided pin.
                try:
                    camera = camera_controller.retrieve_by_io_pin_trigger(request.io_pin)
                except Exception as e:
                    self.logger.error(str(e))
                    sub_response.error = MediatorServiceConstants.Error.GENERAL
                    sub_response.error_description = (
                        "Failed to retrieve related camera by I/O pin."
                    )
                    return sub_response
            else:
                # No camera - no candies
                self.logger.warning("Camera identification not provided")
                response.error = MediatorServiceConstants.Error.GENERAL
                response.error_description = "No camera identification provided."
                return response

            self.logger.info(f"Camera retrieved [{camera.id}]: {camera.title}")

            # Capture test image
            future = self.image_acquisition_capture_image(camera.ip_address, True)
            sub_response = self.await_future(future)
            if sub_response.error != ImageAcquisitionConstants.Error.NONE:
                response.error = MediatorServiceConstants.Error.CAPTURE_FAILED
                response.error_description = (
                    f"Failed to capture image. {response.error_description}"
                )
                return response
            test_image_msg = sub_response.image
            self.logger.info(f"Test image captured as message")

            # Product identification
            future = self.product_identification_get_barcode(test_image_msg)
            # Decode test image while waiting for sub_response (will be used for logging purposed)
            test_image = msg_to_image(test_image_msg)
            sub_response = self.await_future(future)

            self.logger.info(f"Test image captured as message")

            try:
                assert (
                    sub_response.identification_code is not None
                    and sub_response.identification_code.strip()
                )
            except AssertionError:
                response.error = (
                    MediatorServiceConstants.Error.IDENTIFICATION_FAILED
                )
                response.error_description = f"Failed to identify product."
                return response

            # Inspection profile retrieval
            try:
                inspection_profile = (
                    inspection_profile_controller.retrieve_by_identification_code(
                        sub_response.identification_code
                    )
                )
                assert (
                    inspection_profile is not None
                ), "Inspection profile not detected by product code"
            except Exception as e:
                self.logger.error(str(e))
                response.error = MediatorServiceConstants.Error.GENERAL
                response.error_description = (
                    "Failed to retrieve inspection profile. Is profile active?"
                )
                return response

            self.logger.info(
                f"Inspection profile retrieved [{inspection_profile.id}]: {inspection_profile.title}"
            )

            # Template retrieval
            try:
                template = inspection_profile.template
            except Exception as e:
                self.logger.error(str(e))
                response.error = MediatorServiceConstants.Error.GENERAL
                response.error_description = "Failed to retrieve related template."
                return response

            self.logger.info(f"Template retrieved [{template.id}]: {template.title}")

            # Map each required inspection handler to related inspection zones
            # Retrieve inspection handler source
            inspection_handler_list = []
            inspection_handler_source_list = []
            inspection_handler_related_inspection_target_msg_map = defaultdict(list)
            try:
                inspection_zone_list = template.inspection_zone_list
                assert len(inspection_zone_list), "Inspection zone list is empty"

                for cz in inspection_zone_list:
                    inspection_target_list = cz.inspection_target_list
                    assert len(inspection_target_list), "Inspection target list is empty"

                    for ct in inspection_target_list:
                        ch = ct.inspection_handler
                        self.logger.info(
                            f"Registering inspection target [{ct.id}]: inspection zone: {cz.title}, inspection handler: {ch.title}"
                        )
                        inspection_handler_related_inspection_target_msg_map[ch.id].append(
                            _inspection_target_to_msg(ct)
                        )

                        if ch.id in inspection_handler_list:
                            continue

                        inspection_handler_list.append(ch.id)
                        # Materialize inspection handler source
                        source = ch.materialize_source().decode()
                        inspection_handler_source_list.append(source)
            except Exception as e:
                self.logger.error(str(e))
                response.error = MediatorServiceConstants.Error.RESOURCE_FAILED
                response.error_description = (
                    "Failed to retrieve related inspection handler."
                )
                return response

            self.logger.info(f"Inspection handler retrieved and inspection targets are ready")

            # Template image materialization

            try:
                template_image = template.materialize_image()
                template_image = np.array(template_image)
                template_image_msg = image_to_msg(template_image)
            except Exception as e:
                self.logger.error(str(e))
                response.error = MediatorServiceConstants.Error.RESOURCE_FAILED
                response.error_description = "Failed to retrieve related template."
                return response

            self.logger.info(f"Template image retrieved: {template_image.shape}")

            inspection_target_list_full_msg = []
            inspection_log_list_full_msg = []
            for inspection_handler_id, inspection_handler_source in zip(
                inspection_handler_list, inspection_handler_source_list
            ):
                self.logger.info(f"Executing: {inspection_handler_id}")
                try:
                    inspection_target_list = (
                        inspection_handler_related_inspection_target_msg_map[
                            inspection_handler_id
                        ]
                    )
                    future = self.inspection_execution_execute_inspection(
                        template_image_msg,
                        test_image_msg,
                        inspection_handler_source,
                        inspection_profile.environment,
                        inspection_target_list,
                    )
                    sub_response = self.await_future(future)
                    if sub_response.error != InspectionExecutionConstants.Error.NONE:
                        self.logger.error(
                            f"Failed to apply inspection execution. {response.error}: {response.error_description}"
                        )
                        response.error = (
                            MediatorServiceConstants.Error.CONTROL_FAILED
                        )
                        response.error_description = f"Failed to apply inspection handler {inspection_handler_id}. {error_description}"
                        return response
                    for inspection_target, inspection_log in zip(
                        inspection_target_list, sub_response.inspection_log_list
                    ):
                        assert (
                            inspection_target.id == inspection_log.id
                        ), "Inspection log disorder detected."

                    # Collect all logs before creating inspection record
                    inspection_target_list_full_msg.extend(inspection_target_list)
                    inspection_log_list_full_msg.extend(response.inspection_log_list)
                except Exception as e:
                    self.logger.error(str(e))
                    response.error = MediatorServiceConstants.Error.CONTROL_FAILED
                    response.error_description = (
                        f"Failed to apply inspection handler {inspection_handler_id}."
                    )
                    return response
                self.logger.info(f"Completed: {inspection_handler_id}")

            self.logger.info(f"Inspection execution completed")

            try:
                inspection = inspection_controller.create(inspection_profile)
                inspection.publish_image(Image.fromarray(test_image))
                for inspection_target, inspection_log in zip(
                    inspection_target_list_full_msg, inspection_log_list_full_msg
                ):
                    inspection_log_controller.create(
                        inspection_target, inspection, inspection_log.log, inspection_log.passed
                    )
                inspection_controller.commit()
            except Exception as e:
                self.logger.error(str(e))
                response.error = MediatorServiceConstants.Error.CONTROL_FAILED
                response.error_description = f"Failed to store inspection results."
                return response

            response.overall_passed = all(
                [cl.passed for cl in inspection_log_list_full_msg]
            )
            response.image = test_image_msg
            response.inspection_log_list = inspection_log_list_full_msg
            response.inspection_target_list = inspection_target_list_full_msg
            response.error = MediatorServiceConstants.Error.NONE

            self.logger.info(f"Response constructed and returned")
            return response


def main(args=None):
    rclpy.init(args=args)

    service = Service()

    # Use multithread executor to be avoid deadlocks while awaiting services sub_responses
    executor = rclpy.executors.MultiThreadedExecutor()
    executor.add_node(service)
    executor.spin()

    executor.shutdown()
    rclpy.shutdown()


if __name__ == "__main__":
    main()
