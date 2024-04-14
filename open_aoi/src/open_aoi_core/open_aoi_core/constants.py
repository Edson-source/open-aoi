from enum import Enum


class RoleEnum(Enum):
    """Supported role types (reflected in DB)"""

    OPERATOR = 1
    ADMINISTRATOR = 2


class AccessorEnum(Enum):
    """Supported accessors (reflected in DB)"""

    OPERATOR = 1
    ADMINISTRATOR = 2


class ServiceStatusEnum(Enum):
    BUSY = "BUSY"
    IDLE = "IDLE"
    ERROR = "ERROR"


class ControlExecutionConstants:
    NODE_NAME = "control_execution"

    class Error:
        NONE = "NONE"
        CONTROL_HANDLER_INVALID = "CONTROL_HANDLER_INVALID"
        CONTROL_ZONE_INVALID = "CONTROL_ZONE_INVALID"
        ENVIRONMENT_INVALID = "ENVIRONMENT_INVALID"
        IMAGE_INVALID = "IMAGE_INVALID"
        GENERAL = "GENERAL"


class ProductIdentificationConstants:
    NODE_NAME = "product_identification"

    class Error:
        NONE = "NONE"
        GENERAL = "GENERAL"


class ImageAcquisitionConstants:
    NODE_NAME = "image_acquisition"

    class Error:
        NONE = "NONE"
        GENERAL = "GENERAL"

    class Parameter:
        CAMERA_ENABLED = "CAMERA_ENABLED"
        CAMERA_EMULATION_MODE = "CAMERA_EMULATION_MODE"
        CAMERA_IP_ADDRESS = "CAMERA_IP_ADDRESS"


class MediatorServiceConstants:
    NODE_NAME = "mediator"

    class Error:
        NONE = "NONE"
        GENERAL = "GENERAL"
        RESOURCE_FAILED = "RESOURCE_FAILED"
        CAPTURE_FAILED = "CAPTURE_FAILED"
        IDENTIFICATION_FAILED = "IDENTIFICATION_FAILED"
        CONTROL_FAILED = "CONTROL_FAILED"
