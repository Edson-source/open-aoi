""" 
    Module provide SDK to OpenAOI services to communicate with each other. Module
    also define standard service class, which should be used by all nodes. This allow 
    to automatically define status logic (used to identify service status) and prevent 
    dead locks when calling service from callbacks. Deadlock prevention logic is based 
    on this solution: https://robotics.stackexchange.com/a/94614/40411
"""

import time
from typing import Optional, List

from rclpy.node import Node
from rclpy.client import Client as ServiceClient
from rclpy.callback_groups import ReentrantCallbackGroup
from rcl_interfaces.srv._set_parameters import SetParameters
from rcl_interfaces.msg import Parameter, ParameterType, ParameterValue
from sensor_msgs.msg import Image as ImageMsg

from open_aoi_interfaces.msg import InspectionTarget as InspectionTargetMSg
from open_aoi_interfaces.srv import (
    ImageAcquisitionTrigger,
    IdentificationTrigger,
    InspectionTrigger,
    InspectionExecutionTrigger,
    ServiceStatus,
    GPIOTrigger,
)
from open_aoi_core.exceptions import SystemServiceException
from open_aoi_core.constants import (
    ImageAcquisitionConstants,
    GPIOInterfaceConstants,
    ProductIdentificationConstants,
    MediatorServiceConstants,
    SystemServiceStatus,
    InspectionExecutionConstants,
)


class BaseClient:
    NODE_NAME: str


class ImageAcquisitionClient(BaseClient):
    image_acquisition_capture_cli: ServiceClient
    image_acquisition_get_status_cli: ServiceClient
    image_acquisition_set_parameters_cli: ServiceClient

    def image_acquisition_set_parameters(
        self,
        camera_ip_address: Optional[str] = None,
    ):
        """
        Dispatch parameters update request to image acquisition service
        - raise: SystemServiceException if any exception occur
        """

        try:
            req = SetParameters.Request()
            req.parameters = [
                Parameter(
                    name=ImageAcquisitionConstants.Parameter.CAMERA_IP_ADDRESS,
                    value=ParameterValue(
                        string_value=camera_ip_address,
                        type=ParameterType.PARAMETER_STRING,
                    ),
                ),
                Parameter(
                    name=ImageAcquisitionConstants.Parameter.CAMERA_ENABLED,
                    value=ParameterValue(
                        bool_value=True, type=ParameterType.PARAMETER_BOOL
                    ),
                ),
            ]

            self.logger.info(
                "Parameter update request on image acquisition service dispatched"
            )
            return self.image_acquisition_set_parameters_cli.call_async(req)
        except Exception as e:
            self.logger.error(str(e))
            raise SystemServiceException(
                "Failed to set image acquisition parameters."
            ) from e

    def image_acquisition_capture_image(
        self,
        camera_ip_address: Optional[str] = None,
    ):
        """
        Dispatch image capturing request.
        - raise: SystemServiceException if any exception occur
        """
        try:
            self.image_acquisition_set_parameters(camera_ip_address)

            req = ImageAcquisitionTrigger.Request()

            self.logger.info("Image acquisition request dispatched")
            return self.image_acquisition_capture_cli.call_async(req)
        except Exception as e:
            self.logger.error(str(e))
            raise SystemServiceException("Failed to capture image.") from e


class ProductIdentificationClient(BaseClient):
    product_identification_get_barcode_cli: ServiceClient
    product_identification_get_status_cli: ServiceClient

    def product_identification_get_barcode(self, image_msg: ImageMsg):
        """
        Dispatch product identification request. Require image as message as it is meant to work on
        image acquisition service results (prevent unnecessary conversion from message  to image and back)
        - raise: SystemServiceException if any exception occur
        """
        try:
            req = IdentificationTrigger.Request()
            req.image = image_msg

            self.logger.info("Identification request dispatched")
            return self.product_identification_get_barcode_cli.call_async(req)
        except Exception as e:
            self.logger.error(str(e))
            raise SystemServiceException("Failed to identify product.")


class InspectionExecutionClient(BaseClient):
    inspection_execution_execute_inspection_cli: ServiceClient
    inspection_execution_get_status_cli: ServiceClient

    def inspection_execution_execute_inspection(
        self,
        test_image_msg: ImageMsg,
        template_image_msg: ImageMsg,
        environment: str,
        inspection_handler_source: str,
        inspection_target_list: List[InspectionTargetMSg],
    ):
        """
        Dispatch inspection execution request. Require image as message as it is meant to work on
        image acquisition service results (prevent unnecessary conversion from message  to image and back)
        - raise: SystemServiceException if any exception occur
        """
        try:
            req = InspectionExecutionTrigger.Request()

            req.test_image = test_image_msg
            req.template_image = template_image_msg

            req.environment = environment
            req.inspection_handler = inspection_handler_source
            req.inspection_target_list = inspection_target_list

            self.logger.info("Inspection execution request dispatched")
            return self.inspection_execution_execute_inspection_cli.call_async(req)
        except Exception as e:
            self.logger.error(str(e))
            raise SystemServiceException("Failed to execute inspection.")


class GPIOInterfaceClient(BaseClient):
    gpio_interface_propagate_results_cli: ServiceClient
    gpio_interface_get_status_cli: ServiceClient
    gpio_interface_set_parameters_cli: ServiceClient

    def gpio_interface_set_parameters(
        self,
        watch_pin_list: List[int],
    ):
        """
        Dispatch parameters update request on GPIO service.
        - raise: SystemServiceException if any exception occur
        """
        try:
            req = SetParameters.Request()
            req.parameters = [
                Parameter(
                    name=GPIOInterfaceConstants.Parameter.WATCH_PIN_LIST,
                    value=ParameterValue(
                        integer_array_value=watch_pin_list,
                        type=ParameterType.PARAMETER_INTEGER_ARRAY,
                    ),
                ),
            ]

            return self.gpio_interface_set_parameters_cli.call_async(req)
        except Exception as e:
            self.logger.error(str(e))
            raise SystemServiceException(
                "Failed to set GPIO interface parameters."
            ) from e

    def gpio_interface_propagate_results(
        self,
        propagate_pin: int,
        release_pin: int,
    ):
        """
        Dispatch GPIO result propagation request. Request will reset trigger pin and make it
        active again allowing inspection requests.
        - raise: SystemServiceException if any exception occur
        """
        try:
            req = GPIOTrigger.Request()

            req.propagate_pin = propagate_pin
            req.release_pin = release_pin

            self.logger.info("GPIO propagation request dispatched")
            return self.gpio_interface_propagate_results_cli.call_async(req)
        except Exception as e:
            self.logger.error(str(e))
            raise SystemServiceException("Failed to propagate GPIO results.") from e


class MediatorClient(BaseClient):
    mediator_inspection_cli: ServiceClient
    mediator_get_status_cli: ServiceClient

    def mediator_inspection(
        self,
        camera_id: Optional[int] = None,
        io_pin: Optional[int] = None,
    ):
        """
        Dispatch inspection request. Inspection may be triggered directly for camera of indirectly for pin,
        which should be assigned to camera in database. Provide ONE of two identifications (camera id or pin number)
        - raise: SystemServiceException if any exception occur.
        """
        assert camera_id is not None or io_pin is not None
        try:
            req = InspectionTrigger.Request()

            req.camera_id = camera_id if camera_id is not None else 0
            req.camera_id_valid = True if camera_id is not None else False

            req.io_pin = io_pin if io_pin is not None else 0
            req.io_pin_valid = True if io_pin is not None else False

            self.logger.info("Inspection request dispatched")
            return self.mediator_inspection_cli.call_async(req)
        except Exception as e:
            self.logger.error(str(e))
            raise SystemServiceException("Failed to inspect product.") from e


class StandardClient(
    Node,
    MediatorClient,
    GPIOInterfaceClient,
    InspectionExecutionClient,
    ProductIdentificationClient,
    ImageAcquisitionClient,
):

    def __init__(self) -> None:
        super().__init__(self.NODE_NAME)
        self.logger = self.get_logger()

        self._group = ReentrantCallbackGroup()

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

        # Image acquisition
        self._acquire_service(
            f"{ImageAcquisitionConstants.NODE_NAME}/capture",
            "image_acquisition_capture_cli",
            ImageAcquisitionTrigger,
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

        # Inspection execution
        self._acquire_service(
            f"{InspectionExecutionConstants.NODE_NAME}/execute_inspection",
            f"inspection_execution_execute_inspection_cli",
            InspectionExecutionTrigger,
        )
        self._acquire_service(
            f"{InspectionExecutionConstants.NODE_NAME}/get_status",
            "inspection_execution_get_status_cli",
            ServiceStatus,
        )

        # GPIO interface
        self._acquire_service(
            f"{GPIOInterfaceConstants.NODE_NAME}/propagate_result",
            f"gpio_interface_propagate_results_cli",
            GPIOTrigger,
        )
        self._acquire_service(
            f"{GPIOInterfaceConstants.NODE_NAME}/get_status",
            "gpio_interface_get_status_cli",
            ServiceStatus,
        )

        self._acquire_service(
            f"{GPIOInterfaceConstants.NODE_NAME}/set_parameters",
            "gpio_interface_set_parameters_cli",
            SetParameters,
        )

        # Mediator
        self._acquire_service(
            f"{MediatorServiceConstants.NODE_NAME}/inspection",
            f"mediator_inspection_cli",
            InspectionTrigger,
        )
        self._acquire_service(
            f"{MediatorServiceConstants.NODE_NAME}/get_status",
            "mediator_get_status_cli",
            ServiceStatus,
        )

    def _acquire_service(self, name: str, property_name: str, msg):
        cli = self.create_client(msg, name, callback_group=self._group)
        setattr(self, property_name, cli)

    def await_dependencies(self, service_cli_list: List[ServiceClient]):
        for cli in service_cli_list:
            while not cli.wait_for_service(timeout_sec=1.0):
                self.logger.info(
                    f"Service {cli.srv_name} not available, waiting again..."
                )

    def await_future(self, future):
        while not future.done():
            time.sleep(0.05)
        return future.result()


class StandardService(StandardClient):
    service_status: str = SystemServiceStatus.IDLE
    service_status_reason: str = ""

    def __init__(self):
        super().__init__()
        self.logger = self.get_logger()

        self._status_service_instance = self.create_service(
            ServiceStatus,
            f"{self.NODE_NAME}/get_status",
            self._get_status,
            callback_group=self._group,
        )
        self.logger.info("Service started")

    def set_status(self, status: str, reason: str = ""):
        self.service_status = status
        self.service_status_reason = reason

    def _get_status(self, request, response):
        response.status = self.service_status.value
        response.reason = self.service_status_reason
        return response
