"""
    This script define control execution logic to apply control handler to control zone in the tested image.
"""

import rclpy
from io import StringIO
from dotenv import dotenv_values

from open_aoi_ros_services import StandardService
from open_aoi_ros_interfaces.msg import ControlLog
from open_aoi_ros_interfaces.srv import ControlExecutionTrigger
from open_aoi_core.enums import ControlExecutionEnum, ServiceStatusEnum
from open_aoi_core.utils import decode_image
from open_aoi_core.mixins.module_source import dynamic_import, IModule


class Service(StandardService):
    NODE_NAME = ControlExecutionEnum.NODE_NAME.value

    def __init__(self):
        super().__init__()
        self.control_trigger_service = self.create_service(
            None,
            f"{self.NODE_NAME}/control_execution/trigger",
            self.control_execution_trigger,
        )

    def control_execution_trigger(
        self,
        request: ControlExecutionTrigger.Request,
        response: ControlExecutionTrigger.Response,
    ):
        self._set_status(ServiceStatusEnum.BUSY.value)

        # TODO: align and isolate product
        try:
            test_image = decode_image(request.test_image)
        except Exception as e:
            self.logger.error(str(e))
            self.logger.info("Failed to decode test image")

            request.error = ControlExecutionEnum.Error.IMAGE_INVALID.value
            request.error_description = "Failed to decode test image"

            self._set_status(ServiceStatusEnum.IDLE.value)
            return response

        try:
            template_image = decode_image(request.template_image)
        except Exception as e:
            self.logger.error(str(e))
            self.logger.info("Failed to decode template image")

            response.error = ControlExecutionEnum.Error.IMAGE_INVALID.value
            response.error_description = "Failed to decode template image"

            self._set_status(ServiceStatusEnum.IDLE.value)
            return response

        source = request.control_handler
        try:
            module = dynamic_import(source.encode())
        except Exception as e:
            self.logger.error(str(e))
            self.logger.info(
                "Failed to import control handler specification from source"
            )

            response.error = ControlExecutionEnum.Error.CONTROL_HANDLER_INVALID.value
            response.error_description = (
                "Failed to import control handler specification from source"
            )

            self._set_status(ServiceStatusEnum.IDLE.value)
            return response

        environment = StringIO(request.environment)
        try:
            environment = dotenv_values(stream=environment)
        except Exception as e:
            self.logger.error(str(e))
            self.logger.info(f"Failed to load environment")

            response.error = ControlExecutionEnum.Error.ENVIRONMENT_INVALID.value
            response.error_description = f"Failed to load environment"

            self._set_status(ServiceStatusEnum.IDLE.value)
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
                self._set_status(ServiceStatusEnum.IDLE.value)
                return response

        except Exception as e:
            self.logger.error(str(e))
            self.logger.info(f"Failed to execute control handler")

            response.error = ControlExecutionEnum.Error.GENERAL.value
            response.error_description = f"Failed to execute control handler: {str(e)}"

            self._set_status(ServiceStatusEnum.IDLE.value)
            return response


def main(args=None):
    rclpy.init(args=args)
    service = Service()
    rclpy.spin(service)
    rclpy.shutdown()


if __name__ == "__main__":
    main()
