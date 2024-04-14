"""
    This script is an image acquisition node. See service definition for request format.
    Request format is mutual for simulation and real node (this nodes are interchangeable). Node
    provide interface to real camera hiding hardware set up and communication routines. 
    TODO: error collection to services init
"""

import os
from typing import List, Optional

import rclpy
import numpy as np
from pypylon import pylon
from rcl_interfaces.msg import ParameterDescriptor, SetParametersResult

from open_aoi_core.utils import encode_image
from open_aoi_core.enums import ImageAcquisitionEnum
from open_aoi_ros_interfaces.srv import ImageAcquisition
from open_aoi_ros_services import StandardService


EMULATION_DIR = "./emulation"


class Service(StandardService):
    NODE_NAME = ImageAcquisitionEnum.NODE_NAME.value

    camera_ip_address: str = ""
    camera_enabled: bool = False
    camera_emulation_mode: bool = False
    camera: Optional[pylon.InstantCamera] = None

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
            ImageAcquisitionEnum.Parameter.CAMERA_ENABLED.value,
            value=self.camera_enabled,
            descriptor=ParameterDescriptor(
                name="Camera enabled",
                type=rclpy.Parameter.Type.BOOL.value,
                description="If True, connection to camera will be opened. False by default.",
            ),
        )
        self.declare_parameter(
            ImageAcquisitionEnum.Parameter.CAMERA_EMULATION_MODE.value,
            value=self.camera_emulation_mode,
            descriptor=ParameterDescriptor(
                name="Camera emulation mode",
                type=rclpy.Parameter.Type.BOOL.value,
                description="If True, camera emulation is used. False by default.",
            ),
        )
        self.declare_parameter(
            ImageAcquisitionEnum.Parameter.CAMERA_IP_ADDRESS.value,
            value=self.camera_ip_address,
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
            if p.name == "camera_enabled":
                reload = True
        if (
            reload
        ):  # This function is triggered multiple times for unknown reason - reload services only once though
            self._reload_service()
        return SetParametersResult(successful=True, reason="")

    def _reload_service(self):
        self.logger.info("Service reload requested")
        self.logger.info(f"Service enabled: {self.camera_enabled}")
        if self.camera_enabled:
            self._acquire_camera()

    def _acquire_camera(self):
        self.logger.info("Camera connection requested")
        if self.camera is not None:
            self.logger.info("Existing camera detected. Closing...")
            self.camera.Close()

        # Emulation
        if self.camera_emulation_mode:
            self.logger.info("Running emulation mode")
            try:
                os.environ["PYLON_CAMEMU"] = "1"
                tlf: pylon.TlFactory = pylon.TlFactory.GetInstance()
                self.camera = pylon.InstantCamera(tlf.CreateFirstDevice())
                self.camera.Open()
                self.camera.ImageFilename = EMULATION_DIR
                self.camera.ImageFileMode = "On"
                self.camera.TestImageSelector = "Off"
                self.camera.Height = 2048
                self.camera.Width = 2592
                self._set_status = "Connected to camera: EMULATION"
            except Exception as e:
                self.logger.exception(e)
                self._set_status("Failed to setup emulator")
                return
        # Real camera
        else:
            self.logger.info(f"Running with real camera: {self.camera_ip_address}")
            try:
                tlf: pylon.TlFactory = pylon.TlFactory.GetInstance()
                for dev_info in tlf.EnumerateDevices():
                    if (
                        dev_info.GetDeviceClass() == "BaslerGigE"
                        and dev_info.GetIpAddress() == self.camera_ip_address
                    ):
                        self.camera = pylon.InstantCamera(tlf.CreateDevice(dev_info))
                        break
                else:
                    self._set_status(
                        f"Failed to acquire camera with IP: {self.camera_ip_address}"
                    )
                    return
                self.camera.Open()
                self.service_status = f"Connected to camera: {self.camera_ip_address}"
            except Exception as e:
                self.logger.exception(e)
                self._set_status("Failed to setup camera")
                return

    def acquire_image(self, request, response):
        self.logger.info("Image requested")

        if self.camera is None:
            response.image = encode_image(np.zeros((1, 1, 1)))
            response.error = ImageAcquisitionEnum.Error.GENERAL.value
            response.error_description = (
                "Capture image called before camera initialization"
            )
            return response
        try:
            grab_result = self.camera.GrabOne(1000)
            if grab_result.GrabSucceeded():
                # Access the image data
                image = grab_result.Array
                grab_result.Release()
                response.image = encode_image(image)
                response.error = ImageAcquisitionEnum.Error.NONE.value
                response.error_description = ""
                return response
            else:
                grab_result.Release()
                self.logger.error(
                    "Error: ", grab_result.ErrorCode, grab_result.ErrorDescription
                )
                response.image = encode_image(np.zeros((1, 1, 1)))
                response.error = ImageAcquisitionEnum.Error.GENERAL.value
                response.error_description = "Capture image failed"
                return response
        except Exception as e:
            self.logger.exception(e)
            response.image = encode_image(np.zeros((1, 1, 1)))
            response.error = ImageAcquisitionEnum.Error.GENERAL.value
            response.error_description = "Capture image failed"
            return response


def main():
    rclpy.init()
    service = Service()

    rclpy.spin(service)
    rclpy.shutdown()


if __name__ == "__main__":
    main()
