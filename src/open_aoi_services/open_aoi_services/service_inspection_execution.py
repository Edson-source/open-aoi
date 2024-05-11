"""
    This script define inspection execution logic to apply inspection handler to inspection zone in the tested image.
"""

import rclpy
from io import StringIO
from dotenv import dotenv_values

from open_aoi_core.services import StandardService
from open_aoi_interfaces.msg import InspectionLog
from open_aoi_interfaces.srv import InspectionExecutionTrigger
from open_aoi_core.constants import InspectionExecutionConstants, SystemServiceStatus
from open_aoi_core.utils_ros import message_to_image
from open_aoi_core.utils_basic import dynamic_import, Profiler
from open_aoi_core.content.modules import IModule


class Service(StandardService):
    NODE_NAME = InspectionExecutionConstants.NODE_NAME

    def __init__(self):
        super().__init__()
        self.inspection_execution_service = self.create_service(
            InspectionExecutionTrigger,
            f"{self.NODE_NAME}/execute_inspection",
            self.execute_inspection,
        )

    def execute_inspection(
        self,
        request: InspectionExecutionTrigger.Request,
        response: InspectionExecutionTrigger.Response,
    ):
        self.logger.info("Execution request received")
        self.set_status(SystemServiceStatus.BUSY)

        p = Profiler()

        # Decode test image
        try:
            test_image = message_to_image(request.test_image)
        except Exception as e:
            self.logger.error(str(e))
            self.logger.info("Failed to decode test image")

            request.error = InspectionExecutionConstants.Error.IMAGE_INVALID
            request.error_description = "Failed to decode test image"

            self.set_status(SystemServiceStatus.IDLE)
            return response
        self.logger.info(f"Test image decoded. [{p.tick()}]")

        # Decode template image
        try:
            template_image = message_to_image(request.template_image)
        except Exception as e:
            self.logger.error(str(e))
            self.logger.info("Failed to decode template image")

            response.error = InspectionExecutionConstants.Error.IMAGE_INVALID
            response.error_description = "Failed to decode template image"

            self.set_status(SystemServiceStatus.IDLE)
            return response
        self.logger.info(f"Template image decoded. [{p.tick()}]")

        # Import handler
        source = request.inspection_handler
        self.logger.info(source)
        try:
            module, _ = dynamic_import(source.encode())
        except Exception as e:
            self.logger.error(str(e))
            self.logger.info(
                "Failed to import inspection handler specification from source"
            )

            response.error = InspectionExecutionConstants.Error.CONTROL_HANDLER_INVALID
            response.error_description = (
                "Failed to import inspection handler specification from source"
            )

            self.set_status(SystemServiceStatus.IDLE)
            return response
        self.logger.info(f"Handler was imported. [{p.tick()}]")

        # Prase environment
        environment = StringIO(request.environment)
        try:
            environment = dotenv_values(stream=environment)
        except Exception as e:
            self.logger.error(str(e))
            self.logger.info(f"Failed to load environment")

            response.error = InspectionExecutionConstants.Error.ENVIRONMENT_INVALID
            response.error_description = f"Failed to load environment"

            self.set_status(SystemServiceStatus.IDLE)
            return response
        self.logger.info(f"Environment was imported. [{p.tick()}]")

        inspection_zone_list = [
            IModule.InspectionZone(
                rotation=ct.rotation,
                stat_left=ct.stat_left,
                stat_top=ct.stat_top,
                stat_width=ct.stat_width,
                stat_height=ct.stat_height,
            )
            for ct in request.inspection_target_list
        ]
        self.logger.info(f"Inspection zone list constructed. [{p.tick()}]")

        # Invoke handler
        try:
            self.logger.info(f"Inspection handler invoked. [{p.tick()}]")
            inspection_log_list = module.process(
                environment=environment,
                test_image=test_image,
                template_image=template_image,
                inspection_zone_list=inspection_zone_list,
            )
            self.logger.info(f"Inspection handler finished. [{p.tick()}]")
        except Exception as e:
            self.logger.error(str(e))
            self.logger.info(f"Failed to execute inspection handler")

            response.error = InspectionExecutionConstants.Error.GENERAL
            response.error_description = (
                f"Failed to execute inspection handler: {str(e)}"
            )

            self.set_status(SystemServiceStatus.IDLE)
            return response

        # Construct response
        inspection_log_list_message = []
        for log, target in zip(inspection_log_list, request.inspection_target_list):
            ros_log = InspectionLog()
            ros_log.id = target.id
            ros_log.log = log.log
            ros_log.passed = log.passed
            inspection_log_list_message.append(ros_log)
        response.inspection_log_list = inspection_log_list_message
        response.error = InspectionExecutionConstants.Error.NONE

        self.set_status(SystemServiceStatus.IDLE)
        self.logger.info(f"Log constructed and returned. [{p.tick()}]")
        return response


def main(args=None):
    rclpy.init(args=args)
    service = Service()
    rclpy.spin(service)
    rclpy.shutdown()


if __name__ == "__main__":
    main()
