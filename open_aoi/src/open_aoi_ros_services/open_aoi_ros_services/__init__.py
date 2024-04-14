from rclpy.node import Node
from open_aoi_core.enums import ServiceStatusEnum
from open_aoi_ros_interfaces.srv import ServiceStatus


class StandardService(Node):
    NODE_NAME: str

    service_status: ServiceStatusEnum = ServiceStatusEnum.IDLE
    service_status_reason: str = ""

    def __init__(self):
        super().__init__(self.NODE_NAME)
        self.logger = self.get_logger()

        self._status_service_instance = self.create_service(
            ServiceStatus,
            f"{self.NODE_NAME}/get_status",
            self._get_status,
        )
        self.logger.info("Service started")

    def _set_status(self, status: ServiceStatusEnum, reason: str = ""):
        self.service_status = status
        self.service_status_reason = reason

    def _get_status(self, request, response):
        response.status = self.service_status.value
        response.reason = self.service_status_reason
        return response
