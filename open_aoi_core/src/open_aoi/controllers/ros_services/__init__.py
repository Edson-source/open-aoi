import roslibpy

from open_aoi.settings import ROS_PORT
from open_aoi.exceptions import ROSServiceError


SINGLETON_ROS = roslibpy.Ros(host="localhost", port=ROS_PORT, is_secure=True)


class Service:
    _service_name: str

    @property
    def status(self) -> str:
        try:
            ros = self._get_ros_client()
            service = roslibpy.Service(
                ros, f"{self._service_name}/status", "open_aoi_interfaces/ServiceStatus"
            )
            request = roslibpy.ServiceRequest()
            response = service.call(request, timeout=10)

            return response["status"]
        except:
            raise ROSServiceError("Failed to obtain service status")

    @staticmethod
    def _get_ros_client():
        try:
            if SINGLETON_ROS.is_connected:
                return SINGLETON_ROS
            SINGLETON_ROS.run(timeout=5)
            return SINGLETON_ROS
        except:
            raise ROSServiceError("Failed to connect to ROS")
