from enum import Enum


class RoleEnum(Enum):
    """Supported role types (reflected in DB)"""

    OPERATOR = 1
    ADMINISTRATOR = 2


class AccessorEnum(Enum):
    """Supported accessors (reflected in DB)"""

    OPERATOR = 1
    ADMINISTRATOR = 2
