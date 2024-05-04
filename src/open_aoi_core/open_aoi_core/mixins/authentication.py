"""
    Module provide authentication capabilities. Authentication against database is covered by 
    `DatabaseAuthenticationMixin` mixin, session scoped authentication for portal is covered by 
    `SessionAuthenticationMixin` mixin.
"""

import bcrypt

from open_aoi_core.exceptions import AuthenticationException
from open_aoi_core.mixins import Mixin


class DatabaseAuthenticationMixin(Mixin):
    """Provide authentication capabilities against database by username and password"""

    # Accessor's bcrypt encrypted string
    hash: str
    # Accessor's username
    username: str

    def set_password(self, password: str) -> None:
        """Override stored hash with new one"""
        self.hash = self._hash_password(password)

    def test_credentials(self, password: str) -> None:
        """
        Test provided credential against stored
        - raise: AuthenticationException if credentials fails the test
        """

        try:
            assert bcrypt.checkpw(password.encode(), self.hash.encode())
        except AssertionError as e:
            raise AuthenticationException("Credential test failed") from e

    @staticmethod
    def _hash_password(password: str) -> str:
        """Convert password to hash"""
        salt = bcrypt.gensalt()
        return bcrypt.hashpw(password.encode(), salt).decode()


class SessionAuthenticationMixin(Mixin):
    """Provide server side session scoped authentication mechanism"""

    # Accessor's id
    id: int

    def assert_session_access(self, storage: dict):
        """
        Test if access was granted in past
        - raise: AuthenticationException is access was not granted
        """
        try:
            assert storage["access_allowed"]
            assert storage["accessor_id"] == self.id
        except (AssertionError, KeyError) as e:
            raise AuthenticationException("Access assertion failed") from e

    def grant_session_access(self, storage: dict):
        """Push flags and metadata to app store to reflect access has been granted to accessor in past"""
        storage["access_allowed"] = True
        storage["accessor_id"] = self.id

    @staticmethod
    def revoke_session_access(storage: dict):
        """Remove access flags and metadata from session"""
        try:
            del storage["access_allowed"]
        except KeyError:
            pass
        try:
            del storage["accessor_id"]
        except KeyError:
            pass

    @staticmethod
    def identify_session_accessor_id(storage: dict) -> int:
        """
        Return id of accessor if access is allowed
        - raise: AuthenticationException if access was not granted
        """
        try:
            assert storage["access_allowed"]
            assert storage["accessor_id"] is not None
        except (AssertionError, KeyError) as e:
            raise AuthenticationException("Access assertion failed") from e
        return storage["accessor_id"]
