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


class ControlExecutionEnum(Enum):
    NODE_NAME = "control_execution"

    class Error(Enum):
        NONE = "NONE"
        CONTROL_HANDLER_INVALID = "CONTROL_HANDLER_INVALID"
        CONTROL_ZONE_INVALID = "CONTROL_ZONE_INVALID"
        ENVIRONMENT_INVALID = "ENVIRONMENT_INVALID"
        IMAGE_INVALID = "IMAGE_INVALID"
        GENERAL = "GENERAL"


class ProductIdentificationEnum(Enum):
    NODE_NAME = "product_identification"

    class Error(Enum):
        NONE = "NONE"
        GENERAL = "GENERAL"


class ImageAcquisitionEnum(Enum):
    NODE_NAME = "image_acquisition"

    class Error(Enum):
        NONE = "NONE"
        GENERAL = "GENERAL"

    class Parameter(Enum):
        CAMERA_ENABLED = "camera_enabled"
        CAMERA_EMULATION_MODE = "camera_emulation_mode"
        CAMERA_IP_ADDRESS = "camera_ip_address"


class MediatorService:
    NODE_NAME = "mediator"

    class Error:
        NONE = "NONE"
        GENERAL = "GENERAL"
        RESOURCE_FAILED = "RESOURCE_FAILED"
        CAPTURE_FAILED = "CAPTURE_FAILED"
        IDENTIFICATION_FAILED = "IDENTIFICATION_FAILED"
        CONTROL_FAILED = "CONTROL_FAILED"
