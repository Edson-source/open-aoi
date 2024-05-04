import os
import random
from typing import List, Optional

import rclpy
from pypylon import pylon
from rcl_interfaces.msg import ParameterDescriptor, SetParametersResult

from open_aoi_core.utils import encode_image
from open_aoi_core.constants import ImageAcquisitionConstants, ServiceStatusEnum
from open_aoi_interfaces.srv import ImageAcquisition
from open_aoi_core.services import StandardService

EMULATION_DIR = "./emulation"


class Service(StandardService):
    NODE_NAME = ImageAcquisitionConstants.NODE_NAME

    CAMERA_IP_ADDRESS: str = ""
    CAMERA_ENABLED: bool = False
    CAMERA_EMULATION_MODE: bool = False

    camera: Optional[pylon.InstantCamera] = None

    emulation_images = [f for f in os.listdir(EMULATION_DIR) if '.png' in f]

    def __init__(self):
        super().__init__()

        # --- Services ---
        self.acquire_image_service = self.create_service(
            ImageAcquisition,
            f"{self.NODE_NAME}/capture",
            self.acquire_image,
        )

        # --- Parameters ---
        self.declare_parameter(
            ImageAcquisitionConstants.Parameter.CAMERA_ENABLED,
            value=self.CAMERA_ENABLED,
            descriptor=ParameterDescriptor(
                name="Camera enabled",
                type=rclpy.Parameter.Type.BOOL.value,
                description="If True, connection to camera will be opened. False by default.",
            ),
        )
        self.declare_parameter(
            ImageAcquisitionConstants.Parameter.CAMERA_EMULATION_MODE,
            value=self.CAMERA_EMULATION_MODE,
            descriptor=ParameterDescriptor(
                name="Camera emulation mode",
                type=rclpy.Parameter.Type.BOOL.value,
                description="If True, camera emulation is used. False by default.",
            ),
        )
        self.declare_parameter(
            ImageAcquisitionConstants.Parameter.CAMERA_IP_ADDRESS,
            value=self.CAMERA_IP_ADDRESS,
            descriptor=ParameterDescriptor(
                name="Camera IP address",
                type=rclpy.Parameter.Type.STRING.value,
                description="IP address of camera to use. If not provided, node will connect to the first found camera.",
            ),
        )

        self.add_on_set_parameters_callback(self._update_parameters)
        self._reload_service()

    def _update_parameters(self, parameters: List[rclpy.Parameter]):
        self.logger.info("Parameters update triggered")
        reload = False
        for p in parameters:
            self.logger.info(
                f"Parameter {p.name}: {getattr(self, p.name)} -> {p.value}"
            )
            setattr(self, p.name, p.value)
            if p.name == ImageAcquisitionConstants.Parameter.CAMERA_ENABLED:
                reload = True
        if (
            reload
        ):  # This function is triggered multiple times for unknown reason - reload services only once though
            self._reload_service()
        self.logger.info("Parameters update done")
        return SetParametersResult(successful=True, reason="")

    def _reload_service(self):
        self.logger.info("Service reload requested")
        self.logger.info(f"Service enabled: {self.CAMERA_ENABLED}")
        if self.CAMERA_ENABLED:
            self._acquire_camera()

    def _acquire_camera(self):
        self.logger.info("Camera connection requested")
        if self.camera is not None:
            # TODO: close if ip does not match
            self.logger.info("Existing camera detected. Closing...")
            self.camera.Close()

        # Emulation
        if self.CAMERA_EMULATION_MODE:
            self.logger.info("Running emulation mode")
            try:
                os.environ["PYLON_CAMEMU"] = "1"
                tlf: pylon.TlFactory = pylon.TlFactory.GetInstance()
                self.camera = pylon.InstantCamera(tlf.CreateFirstDevice())
                self.camera.Open()
                sample = f"{EMULATION_DIR}/{random.sample(self.emulation_images, 1)[0]}"
                self.logger.info(f"Sample image selected: {sample}")
                self.camera.ImageFilename = sample
                self.camera.PixelFormat = "RGB8Packed"
                self.camera.ImageFileMode = "On"
                self.camera.TestImageSelector = "Off"
                self.camera.Height = 2048
                self.camera.Width = 2592
                self.set_status(
                    ServiceStatusEnum.IDLE, "Connected to camera: EMULATION"
                )
                return
            except Exception as e:
                self.logger.error(str(e))
                self.set_status(ServiceStatusEnum.ERROR, "Failed to setup emulator")
                return
        # Real camera
        else:
            self.logger.info(f"Running with real camera: {self.CAMERA_IP_ADDRESS}")
            try:
                tlf: pylon.TlFactory = pylon.TlFactory.GetInstance()
                for dev_info in tlf.EnumerateDevices():
                    if (
                        dev_info.GetDeviceClass() == "BaslerGigE"
                        and dev_info.GetIpAddress() == self.CAMERA_IP_ADDRESS
                    ):
                        self.camera = pylon.InstantCamera(tlf.CreateDevice(dev_info))
                        break
                else:
                    self.set_status(
                        ServiceStatusEnum.ERROR,
                        f"Failed to acquire camera with IP: {self.camera_ip_address}",
                    )
                    return
                self.camera.Open()
                self.set_status(
                    ServiceStatusEnum.IDLE,
                    f"Connected to camera: {self.CAMERA_IP_ADDRESS}",
                )
                return
            except Exception as e:
                self.logger.error(str(e))
                self.set_status(ServiceStatusEnum.ERROR, "Failed to setup camera")
                return

    def acquire_image(self, request, response):
        self.logger.info("Image requested")
        self.set_status(ServiceStatusEnum.BUSY)

        if self.camera is None:
            self.logger.error("Camera not initialized")
            response.error = ImageAcquisitionConstants.Error.GENERAL
            response.error_description = (
                "Capture image called before camera initialization"
            )
            self.set_status(ServiceStatusEnum.IDLE)
            self.logger.info("Response returned")
            return response
        try:
            grab_result = self.camera.GrabOne(1000)
            if grab_result.GrabSucceeded():
                # Access the image data
                image = grab_result.Array
                self.logger.info(f"Grabbed successfully: {image.shape}")
                grab_result.Release()
                response.image = encode_image(image)
                response.error = ImageAcquisitionConstants.Error.NONE
                response.error_description = ""
                self.logger.info("Image returned")
                self.set_status(ServiceStatusEnum.IDLE)
                return response
            else:
                self.logger.error("Grabbed unsuccessfully")
                grab_result.Release()
                self.logger.error(
                    "Error: ", grab_result.ErrorCode, grab_result.ErrorDescription
                )
                response.error = ImageAcquisitionConstants.Error.GENERAL
                response.error_description = "Capture image failed"
                self.logger.info("Response returned")
                self.set_status(ServiceStatusEnum.IDLE)
                return response
        except Exception as e:
            self.logger.error(str(e))
            response.error = ImageAcquisitionConstants.Error.GENERAL
            response.error_description = "Capture image failed"
            self.set_status(ServiceStatusEnum.IDLE)
            self.logger.info("Response returned")
            return response


def main():
    rclpy.init()
    service = Service()

    rclpy.spin(service)
    rclpy.shutdown()


if __name__ == "__main__":
    main()
