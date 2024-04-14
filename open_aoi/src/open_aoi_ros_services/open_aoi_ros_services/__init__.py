from typing import Optional, Tuple, List

import rclpy
import numpy as np
from rclpy.node import Node
from rclpy.client import Client as ServiceClient
from rcl_interfaces.srv._set_parameters import SetParameters
from rcl_interfaces.msg import Parameter, ParameterType, ParameterValue
from sensor_msgs.msg import Image as ImageMsg

from open_aoi_core.utils import decode_image
from open_aoi_core.exceptions import ROSServiceError
from open_aoi_ros_interfaces.srv import (
    ServiceStatus,
    ImageAcquisition,
    IdentificationTrigger,
    InspectionTrigger,
)
from open_aoi_core.constants import (
    ImageAcquisitionConstants,
    ProductIdentificationConstants,
    MediatorServiceConstants,
    ServiceStatusEnum,
)


class IntegratedClient(Node):
    NODE_NAME: str

    image_acquisition_capture_cli: ServiceClient
    image_acquisition_get_status_cli: ServiceClient
    image_acquisition_set_parameters_cli: ServiceClient

    product_identification_get_barcode_cli: ServiceClient
    product_identification_get_status_cli: ServiceClient

    mediator_execute_inspection_cli: ServiceClient
    mediator_get_status_cli: ServiceClient

    def __init__(self) -> None:
        super().__init__(self.NODE_NAME)
        self.logger = self.get_logger()

        # Image acquisition
        self._acquire_service(
            f"{ImageAcquisitionConstants.NODE_NAME}/capture",
            "image_acquisition_capture_cli",
            ImageAcquisition,
        )
        self._acquire_service(
            f"{ImageAcquisitionConstants.NODE_NAME}/get_status",
            "image_acquisition_get_status_cli",
            ServiceStatus,
        )
        self._acquire_service(
            f"{ImageAcquisitionConstants.NODE_NAME}/set_parameters",
            "image_acquisition_set_parameters_cli",
            SetParameters,
        )

        # Product identification
        self._acquire_service(
            f"{ProductIdentificationConstants.NODE_NAME}/get_barcode",
            f"product_identification_get_barcode_cli",
            IdentificationTrigger,
        )
        self._acquire_service(
            f"{ProductIdentificationConstants.NODE_NAME}/get_status",
            "product_identification_get_status_cli",
            ServiceStatus,
        )

        # Mediator
        self._acquire_service(
            f"{MediatorServiceConstants.NODE_NAME}/execute_inspection",
            f"mediator_execute_inspection_cli",
            InspectionTrigger,
        )
        self._acquire_service(
            f"{MediatorServiceConstants.NODE_NAME}/get_status",
            "mediator_get_status_cli",
            ServiceStatus,
        )

    def _acquire_service(self, name: str, property_name: str, msg):
        cli = self.create_client(msg, name)
        setattr(self, property_name, cli)

    def _await_dependencies(self, service_cli_list: List[ServiceClient]):
        for cli in service_cli_list:
            while not cli.wait_for_service(timeout_sec=1.0):
                self.logger.info(
                    f"Service {cli.srv_name} not available, waiting again..."
                )

    @staticmethod
    def _resolve_param_type(param_value):
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
        return val


class ImageAcquisitionClient(IntegratedClient):
    def image_acquisition_set_parameters(
        self,
        camera_ip_address: Optional[str] = None,
        camera_emulation_mode: bool = False,
    ) -> bool:
        # https://github.com/ros-planning/navigation2/issues/2415#issuecomment-1028468173
        req = SetParameters.Request()
        parameters = []
        for param_name, param_value in [
            [
                ImageAcquisitionConstants.Parameter.CAMERA_EMULATION_MODE,
                camera_emulation_mode,
            ],
            [
                ImageAcquisitionConstants.Parameter.CAMERA_IP_ADDRESS,
                camera_ip_address,
            ],
            [ImageAcquisitionConstants.Parameter.CAMERA_ENABLED, True],
        ]:
            val = self._resolve_param_type(param_value)
            parameters.append(Parameter(name=param_name, value=val))
        req.parameters = parameters

        future = self.image_acquisition_set_parameters_cli.call_async(req)
        return future.result()

    def image_acquisition_capture_image(
        self,
        camera_ip_address: Optional[str] = None,
        camera_emulation_mode: bool = False,
    ) -> Tuple[Optional[np.ndarray], str, str]:
        try:
            self.logger.info("Image acquisition parameter update request dispatched")

            self.image_acquisition_set_parameters(
                camera_ip_address, camera_emulation_mode
            )

            req = ImageAcquisition.Request()
            self.logger.info("Image acquisition request dispatched")

            future = self.image_acquisition_capture_cli.call_async(req)
            response = future.result()

            error = response.error
            error_description = response.error_description
            im = decode_image(response.image)

            return im, error, error_description

        except Exception as e:
            self.logger.error(str(e))
            raise ROSServiceError(
                "Failed to capture image. Service did not respond correctly."
            )


class ProductIdentificationClient(ImageAcquisitionClient):
    def product_identification_get_barcode(
        self, im_msg: ImageMsg  # Avoid conversion to image from acquisition node
    ) -> Tuple[Optional[np.ndarray], str, str]:
        try:
            req = IdentificationTrigger.Request()
            req.image = im_msg
            self.logger.info("Identification request dispatched")

            future = self.product_identification_get_barcode_cli.call_async(req)
            response = future.result()

            return response.identification_code
        except Exception as e:
            self.logger.error(str(e))
            raise ROSServiceError(
                "Failed to identify product. Service did not respond correctly."
            )


class MediatorClient(ProductIdentificationClient):
    def mediator_execute_inspection(
        self, inspection_profile_id: int
    ) -> Tuple[Optional[np.ndarray], str, str]:
        try:
            req = InspectionTrigger.Request()
            req.inspection_profile_id = inspection_profile_id
            self.logger.info("Inspection request dispatched")

            future = self.mediator_execute_inspection_cli.call_async(req)
            response = future.result()

            return (
                response.overall_passed,
                response.error,
                response.error_description,
            )
        except Exception as e:
            self.logger.error(str(e))
            raise ROSServiceError(
                "Failed to inspect product. Service did not respond correctly."
            )


class StandardService(MediatorClient):
    service_status: ServiceStatusEnum = ServiceStatusEnum.IDLE
    service_status_reason: str = ""

    def __init__(self):
        super().__init__()
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
