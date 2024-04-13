import bcrypt

from open_aoi.exceptions import AuthException
from open_aoi.mixins import Mixin


class AuthMixin(Mixin):
    """Basic authentication"""

    hash: str

    def set_password(self, password: str) -> None:
        """Override stored hash with new one"""
        self.hash = self._hash_password(password)

    def test_credentials(self, password: str) -> None:
        """Test password against stored hash"""

        try:
            assert bcrypt.checkpw(password.encode(), self.hash.encode())
        except AssertionError as e:
            raise AuthException("Credential test failed") from e

    @staticmethod
    def _hash_password(password: str) -> str:
        """Convert password to hash"""
        salt = bcrypt.gensalt()
        return bcrypt.hashpw(password.encode(), salt).decode()


class SessionCredentialsMixin(Mixin):
    """Server side credentials"""

    def assert_session_access(self, storage: dict):
        """Test storage record for access granted in past"""
        try:
            assert storage["access_allowed"]
            assert storage["accessor"] == self.id
        except (AssertionError, KeyError) as e:
            raise AuthException("Access assertion failed") from e

    def grant_session_access(self, storage: dict):
        """Push flags and metadata to app store to reflect access has been granted to accessor in past"""
        storage["access_allowed"] = True
        storage["accessor"] = self.id

    @staticmethod
    def identify_session_access(storage: dict) -> int:
        """Return id of accessor if access is allowed and record exist"""
        try:
            assert storage["access_allowed"]
            assert storage["accessor"] is not None
        except (AssertionError, KeyError) as e:
            raise AuthException("Access assertion failed") from e
        return storage["accessor"]

    @staticmethod
    def revoke_session_access(storage: dict):
        """Remove access flags and metadata from session"""
        del storage["access_allowed"]
        del storage["accessor"]
