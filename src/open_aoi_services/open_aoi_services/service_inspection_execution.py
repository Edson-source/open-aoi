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
from open_aoi_core.utils import msg_to_image
from open_aoi_core.content.modules import dynamic_import, IModule


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

        # TODO: align and isolate product
        try:
            test_image = msg_to_image(request.test_image)
        except Exception as e:
            self.logger.error(str(e))
            self.logger.info("Failed to decode test image")

            request.error = InspectionExecutionConstants.Error.IMAGE_INVALID
            request.error_description = "Failed to decode test image"

            self.set_status(SystemServiceStatus.IDLE)
            return response

        self.logger.info("Test image decoded")

        try:
            template_image = msg_to_image(request.template_image)
        except Exception as e:
            self.logger.error(str(e))
            self.logger.info("Failed to decode template image")

            response.error = InspectionExecutionConstants.Error.IMAGE_INVALID
            response.error_description = "Failed to decode template image"

            self.set_status(SystemServiceStatus.IDLE)
            return response

        self.logger.info("Template image decoded")

        source = request.inspection_handler
        try:
            module = dynamic_import(source.encode())
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

        self.logger.info("Controller is valid")

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

        self.logger.info("Environment is valid")

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
        self.logger.info("Inspection zone list constructed")

        try:
            self.logger.info("Process requested")
            inspection_log_list = module.process(
                environment=environment,
                test_image=test_image,
                template_image=template_image,
                inspection_zone_list=inspection_zone_list,
            )
            self.logger.info("Process finished")
        except Exception as e:
            self.logger.error(str(e))
            self.logger.info(f"Failed to execute inspection handler")

            response.error = InspectionExecutionConstants.Error.GENERAL
            response.error_description = f"Failed to execute inspection handler: {str(e)}"

            self.set_status(SystemServiceStatus.IDLE)
            return response

        inspection_log_list_msg = []
        for i, log in enumerate(inspection_log_list):
            ros_log = InspectionLog()
            ros_log.log = log.log
            ros_log.passed = log.passed
        response.inspection_log_list = inspection_log_list_msg
        response.error = InspectionExecutionConstants.Error.NONE

        self.set_status(SystemServiceStatus.IDLE)
        self.logger.info("Log constructed and returned")
        return response


def main(args=None):
    rclpy.init(args=args)
    service = Service()
    rclpy.spin(service)
    rclpy.shutdown()


if __name__ == "__main__":
    main()
