"""
    Module provide constant values across code base: errors, names, etc.
    class Error is used for service response field `error`. Class Parameter is used for 
    stateful services parameter names.
"""


class SystemLimit:
    TITLE_LENGTH = 200
    DESCRIPTION_LENGTH = 500
    DOCUMENTATION_LENGTH = 8000
    IDENTIFICATION_CODE_LENGTH = 100
    BLOB_UID_LENGTH = 100


class SystemRole:
    """Supported role types (reflected in DB)"""

    OPERATOR = 1
    ADMINISTRATOR = 2


class SystemServiceStatus:
    """Statuses of services"""

    BUSY = "BUSY"  # Service is processing request
    IDLE = "IDLE"  # Service is ready to process another request
    ERROR = "ERROR"  # Valid for stateful services: error occurred after last update


class SystemBuckets:
    """Should be lower case, no special symbols"""

    INSPECTION_IMAGES = "inspections"
    TEMPLATE_IMAGES = "templates"
    MODULE_SOURCES = "modules"


class InspectionExecutionConstants:
    NODE_NAME = "inspection_execution"

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


class GPIOInterfaceConstants:
    NODE_NAME = "gpio_interface"

    class Parameter:
        WATCH_PIN_LIST = "WATCH_PIN_LIST"
