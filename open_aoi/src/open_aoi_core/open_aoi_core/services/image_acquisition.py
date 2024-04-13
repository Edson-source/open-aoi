from typing import Optional, Tuple

import rclpy
from rclpy.client import Client
from rcl_interfaces.msg import Parameter, ParameterType, ParameterValue
from rcl_interfaces.srv._set_parameters import SetParameters
from PIL import Image

from open_aoi_core.exceptions import ROSServiceError
from open_aoi_core.services.utils import decode_image
from open_aoi_ros_interfaces.srv import ImageAcquisition


class ROSImageAcquisitionClient:
    image_acquisition_capture_cli: Client
    image_acquisition_get_status_cli: Client
    image_acquisition_set_parameters_cli: Client

    CAMERA_ERROR_NONE = "NONE"

    def _publish_image_acquisition_service_parameters(
        self,
        camera_ip_address: Optional[str] = None,
        camera_emulation_mode: bool = False,
    ) -> bool:
        # https://github.com/ros-planning/navigation2/issues/2415#issuecomment-1028468173
        req = SetParameters.Request()
        parameters = []
        for param_name, param_value in [
            ["camera_emulation_mode", camera_emulation_mode],
            ["camera_ip_address", camera_ip_address],
            ["camera_enabled", True],
        ]:
            if isinstance(param_value, float):
                val = ParameterValue(
                    double_value=param_value, type=ParameterType.PARAMETER_DOUBLE
                )
            elif isinstance(param_value, int):
                val = ParameterValue(
                    integer_value=param_value, type=ParameterType.PARAMETER_INTEGER
                )
            elif isinstance(param_value, str):
                val = ParameterValue(
                    string_value=param_value, type=ParameterType.PARAMETER_STRING
                )
            elif isinstance(param_value, bool):
                val = ParameterValue(
                    bool_value=param_value, type=ParameterType.PARAMETER_BOOL
                )
            parameters.append(Parameter(name=param_name, value=val))
        req.parameters = parameters

        self.future = self.image_acquisition_set_parameters_cli.call_async(req)
        while rclpy.ok():
            if self.future.done():
                try:
                    response = self.future.result()
                    if response[0].successful:
                        return True
                except Exception as e:
                    pass
                return False

    def capture_image(
        self,
        camera_ip_address: Optional[str] = None,
        camera_emulation_mode: bool = False,
    ) -> Tuple[Image.Image, str, str]:
        try:
            self._publish_image_acquisition_service_parameters(
                camera_ip_address, camera_emulation_mode
            )
            req = ImageAcquisition.Request()

            self.future = self.image_acquisition_capture_cli.call_async(req)
            while rclpy.ok():
                if self.future.done():
                    response = self.future.result()
                    error = response.error
                    error_description = response.error_description

                    data = decode_image(response.image)
                    im = Image.fromarray(data)

                    return im, error, error_description
        except:
            raise ROSServiceError("Failed to obtain service status")
