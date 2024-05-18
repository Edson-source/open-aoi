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
import time
import rclpy
import numpy as np
from PIL import Image
from sqlalchemy.orm import Session
from sqlalchemy.exc import ProgrammingError
from collections import defaultdict
from sensor_msgs.msg import Image as ImageMessage

from open_aoi_interfaces.srv import InspectionTrigger
from open_aoi_interfaces.msg import InspectionTarget
from open_aoi_core.services import StandardService
from open_aoi_core.content.populate_content import populate
from open_aoi_core.models import CameraModel, InspectionProfileModel, TemplateModel
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
from open_aoi_core.utils_ros import cv2_to_imgmsg, imgmsg_to_cv2
from open_aoi_core.utils_basic import Profiler


def _inspection_target_to_message(target: InspectionTargetModel) -> InspectionTarget:
    message = InspectionTarget()
    message.id = target.id

    message.rotation = float(target.inspection_zone.rotation)

    message.stat_left = target.inspection_zone.cc.stat_left
    message.stat_top = target.inspection_zone.cc.stat_top
    message.stat_width = target.inspection_zone.cc.stat_width
    message.stat_height = target.inspection_zone.cc.stat_height

    return message


class Service(StandardService):
    NODE_NAME = MediatorServiceConstants.NODE_NAME

    def __init__(self):
        super().__init__()

        # Register inspection service
        self.inspection_trigger_service = self.create_service(
            InspectionTrigger,
            f"{self.NODE_NAME}/inspection",
            self.inspection,
        )
        # Wait for dependencies: image acquisition, product identification and inspection execution nodes
        self.await_dependencies(
            [
                self.image_acquisition_capture_cli,
                self.product_identification_get_barcode_cli,
                self.inspection_execution_execute_inspection_cli,
                self.gpio_interface_propagate_results_cli,
                self.gpio_interface_set_parameters_cli,
            ]
        )
        # Try to connect to database. When booting for the first 
        # time no tables will be created - recreated them and populate the content.
        with Session(engine) as session:
            inspection_profile_controller = InspectionProfileController(session)
            try:
                self.logger.info('Checking database...')
                inspection_profile_controller.list()
            except Exception as e:
                self.logger.info('Database structure not created. Creating...')
                while True:
                    try:
                        populate()
                        break
                    except Exception as e:
                        self.logger.warning(f"Failed to create database structure and populate content. Retrying...")
                        time.sleep(1)

        self.watch_pin_list_update_service = self.create_timer(
            1,
            self.update_watch_pin_list,
        )

    def _request_camera(self, request, response, camera_controller) -> CameraModel:
        """Retrieve camera based on request"""

        if request.camera_id_valid:
            # Particular camera has been requested (request comes from UI)
            try:
                camera = camera_controller.retrieve(request.camera_id)
                assert camera is not None, "Camera with specified id does not exist."
                return camera
            except Exception as e:
                self.logger.error(str(e))
                response.error = MediatorServiceConstants.Error.GENERAL
                response.error_description = "Failed to retrieve related camera by id."
                raise RuntimeError()
        elif request.io_pin_valid:
            # Particular pin was triggered (request comes from GPIO interface)
            # Get camera with provided pin.
            try:
                camera = camera_controller.retrieve_by_io_pin_trigger(request.io_pin)
                assert camera is not None, "Camera with specified id does not exist."
                return camera
            except Exception as e:
                self.logger.error(str(e))
                response.error = MediatorServiceConstants.Error.GENERAL
                response.error_description = (
                    "Failed to retrieve related camera by I/O pin."
                )
                raise RuntimeError()
        else:
            # No camera - no candies
            self.logger.warning("Camera identification not provided")
            response.error = MediatorServiceConstants.Error.GENERAL
            response.error_description = "No camera identification provided."
            raise RuntimeError()

    def _request_test_image(
        self, request, response, camera: CameraModel
    ) -> ImageMessage:
        """Trigger image service and await response"""
        future = self.image_acquisition_capture_image(camera.ip_address)
        sub_response = self.await_future(future)
        if sub_response.error != ImageAcquisitionConstants.Error.NONE:
            response.error = MediatorServiceConstants.Error.CAPTURE_FAILED
            response.error_description = (
                f"Failed to capture image. {response.error_description}"
            )
            raise RuntimeError()
        return sub_response.image

    def _request_identification(
        self, request, response, test_image_message: ImageMessage
    ) -> str:
        # Product identification
        future = self.product_identification_get_barcode(test_image_message)
        sub_response = self.await_future(future)

        identification_code = sub_response.identification_code
        try:
            identification_code = identification_code.strip()
            assert sub_response.identification_code
        except (AttributeError, AssertionError):
            response.error = MediatorServiceConstants.Error.IDENTIFICATION_FAILED
            response.error_description = f"Failed to identify product."
            raise RuntimeError()
        return identification_code

    def _request_inspection_profile(
        self,
        request,
        response,
        inspection_profile_controller: InspectionProfileController,
        identification_code: str,
    ) -> InspectionProfileModel:
        try:
            inspection_profile = (
                inspection_profile_controller.retrieve_by_identification_code(
                    identification_code
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
            raise RuntimeError()
        return inspection_profile

    def _request_inspection_handlers_with_targets(
        self, request, response, inspection_profile: InspectionProfileModel
    ):
        # Map each required inspection handler to related inspection zones
        # Retrieve inspection handler source
        inspection_handler_id_list = []  # ih1, ih2, ...
        inspection_handler_source_list = []  # ih1 source, ih2 source, ...

        inspection_handler_related_inspection_target_map = defaultdict(
            list
        )  # handler id: insp. target
        inspection_handler_related_inspection_target_message_map = defaultdict(
            list
        )  # handler id: insp. target as message

        try:
            template = inspection_profile.template
            assert template, "Template record not available"

            inspection_zone_list = template.inspection_zone_list
            assert len(inspection_zone_list), "Inspection zone list is empty"

            for inspection_zone in inspection_zone_list:

                inspection_target_list = inspection_zone.inspection_target_list
                assert len(inspection_target_list), "Inspection target list is empty"

                for target in inspection_target_list:

                    inspection_handler = target.inspection_handler
                    assert inspection_handler, "Inspection handler record not available"

                    # Assign target to handler
                    inspection_handler_related_inspection_target_map[
                        inspection_handler.id
                    ].append(target)
                    inspection_handler_related_inspection_target_message_map[
                        inspection_handler.id
                    ].append(_inspection_target_to_message(target))

                    if inspection_handler.id in inspection_handler_id_list:
                        continue

                    # Materialize inspection handler source
                    inspection_handler_id_list.append(inspection_handler.id)
                    source = inspection_handler.materialize_source().decode()
                    inspection_handler_source_list.append(source)
        except Exception as e:
            self.logger.error(str(e))
            response.error = MediatorServiceConstants.Error.RESOURCE_FAILED
            response.error_description = (
                "Failed to retrieve related inspection handler."
            )
            raise RuntimeError()

        return (
            inspection_handler_id_list,
            inspection_handler_source_list,
            inspection_handler_related_inspection_target_map,
            inspection_handler_related_inspection_target_message_map,
        )

    def _request_template_image(
        self, request, response, template: TemplateModel
    ) -> ImageMessage:
        try:
            template_image = template.materialize_image()
            template_image = np.array(template_image)
            template_image_message = cv2_to_imgmsg(template_image)
        except Exception as e:
            self.logger.error(str(e))
            response.error = MediatorServiceConstants.Error.RESOURCE_FAILED
            response.error_description = "Failed to retrieve related template."
            raise RuntimeError()

        return template_image_message

    def _request_inspection_handler_execution(
        self,
        request,
        response,
        inspection_handler_id_list,
        inspection_handler_source_list,
        inspection_handler_related_inspection_target_map,
        inspection_handler_related_inspection_target_message_map,
        test_image_message,
        template_image_message,
        inspection_profile: InspectionProfileModel,
    ):

        # Lists of all inspection targets and related logs (order is kept)
        inspection_target_list_full = []
        inspection_target_list_full_message = []
        inspection_log_list_full_message = []

        for inspection_handler_id, inspection_handler_source in zip(
            inspection_handler_id_list, inspection_handler_source_list
        ):
            self.logger.info(f"Executing handler: {inspection_handler_id}")
            try:
                inspection_target_list = (
                    inspection_handler_related_inspection_target_map[
                        inspection_handler_id
                    ]
                )
                inspection_target_message_list = (
                    inspection_handler_related_inspection_target_message_map[
                        inspection_handler_id
                    ]
                )
                future = self.inspection_execution_execute_inspection(
                    test_image_message=test_image_message,
                    template_image_message=template_image_message,
                    inspection_handler_source=inspection_handler_source,
                    inspection_target_list=inspection_target_message_list,
                    environment=inspection_profile.environment,
                )

                sub_response = self.await_future(future)
                if sub_response.error != InspectionExecutionConstants.Error.NONE:
                    self.logger.error(
                        f"Failed to apply inspection execution. {sub_response.error}: {sub_response.error_description}"
                    )
                    response.error = MediatorServiceConstants.Error.CONTROL_FAILED
                    response.error_description = f"Failed to apply inspection handler {inspection_handler_id}. {sub_response.error_description}"
                    raise RuntimeError()

                for inspection_target_message, inspection_log_message in zip(
                    inspection_target_message_list,
                    sub_response.inspection_log_list,
                ):
                    assert (
                        inspection_target_message.id == inspection_log_message.id
                    ), "Inspection log disorder detected."

                # Collect all records (flatten)
                inspection_target_list_full_message.extend(
                    inspection_target_message_list
                )
                inspection_target_list_full.extend(inspection_target_list)
                inspection_log_list_full_message.extend(
                    sub_response.inspection_log_list
                )
            except Exception as e:
                self.logger.error(str(e))
                response.error = MediatorServiceConstants.Error.CONTROL_FAILED
                response.error_description = (
                    f"Failed to apply inspection handler: {inspection_handler_id}."
                )
                raise RuntimeError()

            self.logger.info(f"Completed: {inspection_handler_id}")

        return (
            inspection_target_list_full,
            inspection_target_list_full_message,
            inspection_log_list_full_message,
        )

    def _request_log_dump(
        self,
        request,
        response,
        inspection_controller: InspectionController,
        inspection_log_controller: InspectionLogController,
        inspection_profile: InspectionProfileModel,
        test_image_message,
        inspection_target_list_full,
        inspection_log_list_full_message,
    ):
        try:
            inspection = inspection_controller.create(inspection_profile)

            test_image = imgmsg_to_cv2(test_image_message)
            test_image = Image.fromarray(test_image)

            inspection.publish_image(test_image)
            for inspection_target, inspection_log_message in zip(
                inspection_target_list_full, inspection_log_list_full_message
            ):
                inspection_log_controller.create(
                    inspection_target,
                    inspection,
                    inspection_log_message.log,
                    inspection_log_message.passed,
                )
            inspection_controller.commit()
        except Exception as e:
            self.logger.error(str(e))
            response.error = MediatorServiceConstants.Error.CONTROL_FAILED
            response.error_description = f"Failed to store inspection results."
            raise RuntimeError()

    def inspection(self, request, response):
        """Service curate inspection logic bringing all required resources together"""

        self.logger.info("Inspection requested")
        response.overall_passed = False

        with Session(engine) as session:
            # Node is going to communicate with database, so initiate controllers
            inspection_profile_controller = InspectionProfileController(session)
            inspection_controller = InspectionController(session)
            inspection_log_controller = InspectionLogController(session)
            camera_controller = CameraController(session)

            p = Profiler()

            try:
                # Camera identification
                camera = self._request_camera(request, response, camera_controller)
                self.logger.info(
                    f"Camera {camera.id} retrieved: {camera.title}. [{p.tick()}]"
                )

                # Capture test image
                test_image_message = self._request_test_image(request, response, camera)
                self.logger.info(f"Test image captured as message. [{p.tick()}]")

                # Product identification
                identification_code = self._request_identification(
                    request, response, test_image_message
                )
                self.logger.info(f"Identification finished. [{p.tick()}]")

                # Inspection profile retrieval
                inspection_profile = self._request_inspection_profile(
                    request,
                    response,
                    inspection_profile_controller,
                    identification_code,
                )
                self.logger.info(
                    f"Inspection profile {inspection_profile.id} retrieved: {inspection_profile.title}. [{p.tick()}]"
                )

                # Inspection handler target mapping
                (
                    inspection_handler_id_list,
                    inspection_handler_source_list,
                    inspection_handler_related_inspection_target_map,
                    inspection_handler_related_inspection_target_message_map,
                ) = self._request_inspection_handlers_with_targets(
                    request, response, inspection_profile
                )
                self.logger.info(
                    f"Inspection handler retrieved and inspection targets are ready. [{p.tick()}]"
                )

                # Template image materialization
                template_image_message = self._request_template_image(
                    request, response, inspection_profile.template
                )
                self.logger.info(f"Template image retrieved. [{p.tick()}]")

                # Inspection handler execution
                (
                    inspection_target_list_full,
                    inspection_target_list_full_message,
                    inspection_log_list_full_message,
                ) = self._request_inspection_handler_execution(
                    request,
                    response,
                    inspection_handler_id_list,
                    inspection_handler_source_list,
                    inspection_handler_related_inspection_target_map,
                    inspection_handler_related_inspection_target_message_map,
                    test_image_message,
                    template_image_message,
                    inspection_profile,
                )
                self.logger.info(f"Inspection execution completed. [{p.tick()}]")

                # Log dumping
                self._request_log_dump(
                    request,
                    response,
                    inspection_controller,
                    inspection_log_controller,
                    inspection_profile,
                    test_image_message,
                    inspection_target_list_full,
                    inspection_log_list_full_message,
                )
                self.logger.info(f"Inspection log dumped. [{p.tick()}]")

                response.overall_passed = all(
                    [
                        inspection_log.passed
                        for inspection_log in inspection_log_list_full_message
                    ]
                )
                response.image = test_image_message
                response.inspection_log_list = inspection_log_list_full_message
                response.inspection_target_list = inspection_target_list_full_message
                response.error = MediatorServiceConstants.Error.NONE

                self.logger.info(f"Response constructed and returned. [{p.tick()}]")
                return response

            except RuntimeError:
                self.logger.info(f"Error ocurred while processing request.")
                return response

    def update_watch_pin_list(self):
        """Callback to update GPIO interface with new pins to watch"""

        try:
            with Session(engine) as session:
                camera_controller = CameraController(session)
                camera_list = camera_controller.list()
    
                watch_pin_list = []
                for camera in camera_list:
                    if camera.io_pin_trigger is not None:
                        watch_pin_list.append(camera.io_pin_trigger)
    
                future = self.gpio_interface_set_parameters(watch_pin_list)
                self.await_future(future)
        except Exception as e:
            self.logger.warning(f"Failed to update pin watch list: {str(e)}")


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
