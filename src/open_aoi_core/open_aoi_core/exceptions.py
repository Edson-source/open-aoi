from abc import ABC


class OpenAOIGeneralException(Exception, ABC):
    pass


class AuthenticationException:
    """Authentication attempt failed"""


class SystemIntegrityException(OpenAOIGeneralException):
    """System integrity was violated"""


class AssetIntegrityException(OpenAOIGeneralException):
    """Asset integrity was violated"""


class ConnectionFailedException(OpenAOIGeneralException):
    """Connection to service or resource could not be established"""


class SystemServiceException(OpenAOIGeneralException):
    """Open AOI service failed"""
