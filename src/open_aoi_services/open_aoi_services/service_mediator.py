"""
    This script is a definition of moderator node. Node inspection communication of other nodes with each other.
    The basic function is to perform product inspection, which consists of the following steps:
    - Get test image from frontend request
    - Identify product profile from request
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
from collections import defaultdict
from sensor_msgs.msg import Image as ImageMessage

from open_aoi_interfaces.srv import InspectionTrigger
from open_aoi_interfaces.msg import InspectionTarget
from open_aoi_core.services import StandardService
from open_aoi_core.content.populate_content import populate
from open_aoi_core.models import InspectionProfileModel, TemplateModel
from open_aoi_core.constants import (
    MediatorServiceConstants,
    InspectionExecutionConstants,
)
from open_aoi_core.models import InspectionTargetModel, engine
from open_aoi_core.controllers.inspection_profile import InspectionProfileController
from open_aoi_core.controllers.inspection import InspectionController
from open_aoi_core.controllers.inspection_log import InspectionLogController
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

        # Dependencies (removed: camera_acquisition, product_identification, GPIO)
        self.await_dependencies(
            [
                self.inspection_execution_execute_inspection_cli,
            ]
        )

        # Try to connect to database
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
                        self.logger.warning(f"Failed to create database structure and populate content ({str(e)}). Retrying...")
                        time.sleep(1)

    def _request_inspection_profile(
        self, request, response, inspection_profile_controller: InspectionProfileController
    ) -> InspectionProfileModel:
        """Retrieve inspection profile specified in the request"""
        try:
            # Obtém o perfil de inspeção com base no ID que virá da tela do operador
            inspection_profile = inspection_profile_controller.retrieve(request.inspection_profile_id)
            assert (
                inspection_profile is not None
            ), f"No inspection profile found for id {request.inspection_profile_id}."
            assert inspection_profile.is_active, "Inspection profile is not active."
        except Exception as e:
            self.logger.error(str(e))
            response.error = MediatorServiceConstants.Error.GENERAL
            response.error_description = (
                "Failed to retrieve inspection profile. Is profile active and valid?"
            )
            raise RuntimeError()
        return inspection_profile


    def _request_inspection_handlers_with_targets(
        self, request, response, inspection_profile: InspectionProfileModel
    ):
        inspection_handler_id_list = []
        inspection_handler_source_list = []

        inspection_handler_related_inspection_target_map = defaultdict(list)
        inspection_handler_related_inspection_target_message_map = defaultdict(list)

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

                    inspection_handler_related_inspection_target_map[
                        inspection_handler.id
                    ].append(target)
                    inspection_handler_related_inspection_target_message_map[
                        inspection_handler.id
                    ].append(_inspection_target_to_message(target))

                    if inspection_handler.id in inspection_handler_id_list:
                        continue

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
            inspection_profile_controller = InspectionProfileController(session)
            inspection_controller = InspectionController(session)
            inspection_log_controller = InspectionLogController(session)

            p = Profiler()

            try:
                # --- NOVA ARQUITETURA DE REDE ---
                # A imagem agora já vem pronta dentro do request gerado pelo Frontend!
                test_image_message = request.test_image
                self.logger.info(f"Test image received from frontend. [{p.tick()}]")

                # O perfil também vem atrelado ao request (operador selecionou no menu)
                inspection_profile = self._request_inspection_profile(
                    request,
                    response,
                    inspection_profile_controller,
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


def main(args=None):
    rclpy.init(args=args)

    service = Service()

    executor = rclpy.executors.MultiThreadedExecutor()
    executor.add_node(service)
    executor.spin()

    executor.shutdown()
    rclpy.shutdown()


if __name__ == "__main__":
    main()