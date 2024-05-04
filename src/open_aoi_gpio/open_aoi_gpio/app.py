"""
    This script define GPIO control logic. GPIO node watches requested pins with defined intervals and 
    when pin is in HIGH state will request inspection on that pin from mediator service. The pin
    with on going inspection is not being watched and changes on that pin are ignored. Inspection result will
    be propagated to another (one of two possible) pin as described in Open AOI GPIO protocol and trigger
    pin may trigger inspection again.

    GPIO library should be installed prior to using the interface, otherwise simulation is used.
"""

import time
from typing import List

import rclpy
from rcl_interfaces.msg import ParameterDescriptor, SetParametersResult

from open_aoi_core.services import StandardService, SystemServiceStatus
from open_aoi_core.constants import GPIOInterfaceConstants
from open_aoi_interfaces.srv import GPIOPropagation

try:
    import RPi.GPIO as GPIO  # Should be available in production (in case of deployment to Raspberry Pi)
except ImportError:
    import SimulRPi.GPIO as GPIO


class Service(StandardService):
    NODE_NAME = GPIOInterfaceConstants.NODE_NAME
    WATCH_PINS = []
    WIP_PINS = []

    def __init__(self):
        super().__init__()
        GPIO.setmode(GPIO.BCM)

        # Services
        # Propagation: propagate result of inspection to GPIO pins
        self.propagate_result = self.create_service(
            GPIOPropagation,
            f"{self.NODE_NAME}/propagate_result",
            self.propagate_result,
        )
        # Parameters
        self.declare_parameter(
            GPIOInterfaceConstants.Parameter.WATCH_PINS,
            value=self.WATCH_PINS,
            descriptor=ParameterDescriptor(
                name="Pins watch list",
                type=rclpy.Parameter.Type.INTEGER_ARRAY.value,
                description="Define I/O pins to watch for inspection trigger request.",
            ),
        )
        self.add_on_set_parameters_callback(self._update_parameters)

        # GPIO watch god
        self.timer = self.create_timer(0.1, self._watch_dog)

        self.await_dependencies([self.mediator_inspection_cli])

    def _update_parameters(self, parameters: List[rclpy.Parameter]):
        self.logger.info("Parameters update triggered")
        for p in parameters:
            self.logger.info(
                f"Parameter {p.name}: {getattr(self, p.name)} -> {p.value}"
            )
            setattr(self, p.name, p.value)
        for pin in self.WATCH_PINS:
            GPIO.setup(pin, GPIO.IN, pull_up_down=GPIO.PUD_DOWN)

        self.logger.info("Parameters update done")
        return SetParametersResult(successful=True, reason="")

    def _watch_dog(self):
        for pin in self.WATCH_PINS:
            if pin not in self.WIP_PINS and GPIO.input(pin):
                # Request inspection and stop watching changes on pin
                self.mediator_inspection(io_pin=pin)
                self.WIP_PINS.append(pin)

    def propagate_result(
        self,
        request: GPIOPropagation.Request,
        response: GPIOPropagation.Response,
    ):
        self.logger.info("Propagation request received")
        self.set_status(SystemServiceStatus.BUSY)

        self.WIP_PINS.remove(request.release_pin)
        GPIO.setup(request.propagate_pin, GPIO.OUT)
        GPIO.output(request.propagate_pin, GPIO.HIGH)
        time.sleep(0.5)
        GPIO.output(request.propagate_pin, GPIO.LOW)

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
