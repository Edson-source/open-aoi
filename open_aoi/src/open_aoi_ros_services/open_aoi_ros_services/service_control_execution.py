"""
    This script define control execution logic to apply control handler to control zone in the tested image.
"""

from io import StringIO

import rclpy
from rclpy.node import Node
from dotenv import dotenv_values

from open_aoi_ros_interfaces.msg import ControlLog
from open_aoi_ros_interfaces.srv import ServiceStatus, ExecutionControlTrigger
from open_aoi_ros_services import StandardServiceMixin
from open_aoi_core.services.utils import decode_image
from open_aoi_core.mixins.module_source import dynamic_import, IModule


NODE_NAME = "control_execution"


class Error:
    none = "NONE"
    control_handler_invalid = "CONTROL_HANDLER_INVALID"
    control_zone_invalid = "CONTROL_ZONE_INVALID"
    environment_invalid = "ENVIRONMENT_INVALID"
    image_invalid = "IMAGE_INVALID"
    general = "GENERAL"


class Service(Node, StandardServiceMixin):
    service_status_default: str = "Working"
    service_status: str = service_status_default

    def __init__(self):
        super().__init__(NODE_NAME)
        self.logger = self.get_logger()

        # --- Services ---
        self.control_trigger_service = self.create_service(
            None,
            f"{NODE_NAME}/control_execution/trigger",
            self.control_execution_trigger,
        )

        self.status_service = self.create_service(
            ServiceStatus,
            f"{NODE_NAME}/status",
            self.expose_status,
        )

    def control_execution_trigger(
        self,
        request: ExecutionControlTrigger.Request,
        response: ExecutionControlTrigger.Response,
    ):
        # TODO: align and isolate
        try:
            test_image = decode_image(request.test_image)
        except Exception as e:
            self.logger.error(str(e))
            self.logger.info("Failed to decode test image")

            request.error = Error.image_invalid
            request.error_description = "Failed to decode test image"

            return response

        try:
            template_image = decode_image(request.template_image)
        except Exception as e:
            self.logger.error(str(e))
            self.logger.info("Failed to decode template image")

            response.error = Error.image_invalid
            response.error_description = "Failed to decode template image"

            return response

        source = request.control_handler
        try:
            module = dynamic_import(source.encode())
        except Exception as e:
            self.logger.error(str(e))
            self.logger.info(
                "Failed to import control handler specification from source"
            )

            response.error = Error.control_handler_invalid
            response.error_description = (
                "Failed to import control handler specification from source"
            )

            return response

        environment = StringIO(request.environment)
        try:
            environment = dotenv_values(stream=environment)
        except Exception as e:
            self.logger.error(str(e))
            self.logger.info(f"Failed to load environment")

            response.error = Error.control_handler_invalid
            response.error_description = f"Failed to load environment"

            return response

        control_zone_list = [
            IModule.ControlZone(
                rotation=cz.rotation,
                stat_left=cz.cc.stat_left,
                stat_top=cz.cc.stat_top,
                stat_width=cz.cc.stat_width,
                stat_height=cz.cc.stat_height,
            )
            for cz in request.control_zone_list
        ]

        try:
            log_list = module.process(
                environment=environment,
                test_image=test_image,
                template_image=template_image,
                control_zone_list=control_zone_list,
            )
            for i, log in enumerate(log_list):
                ros_log = ControlLog()
                ros_log.log = log.log
                ros_log.passed = log.passed
                response.control_log_list[i] = ros_log
                return response
        except Exception as e:
            self.logger.error(str(e))
            self.logger.info(f"Failed to execute control handler")

            response.error = Error.general
            response.error_description = f"Failed to execute control handler: {str(e)}"

            return response


def main(args=None):
    rclpy.init(args=args)
    service = Service()
    rclpy.spin(service)
    rclpy.shutdown()


if __name__ == "__main__":
    main()
