#!/usr/bin/env python3
"""
Celsius AI - Authentication & Session Management
================================================

Description:
------------
This module provides a comprehensive, file-based authentication and session
management system for the Celsius AI ecosystem. It is designed to be secure,
easy to integrate, and compatible with both web interfaces and backend services.

Key Features:
-------------
- **Secure Password Storage**: Uses `hashlib.pbkdf2_hmac` with a per-user salt
  to securely store password hashes, preventing rainbow table attacks.
- **User & Role Management**: Supports creating users with different roles (e.g.,
  'admin', 'user') and associated permissions.
- **Session Management**: Creates cryptographically secure session tokens using
  `secrets.token_urlsafe` with configurable expiration times.
- **Persistent Storage**: Stores user credentials and active sessions in JSON
  files within a dedicated data directory.
- **Graceful Initialization**: Automatically sets up default credentials and
  configuration if none exist.
- **Thread-Safe Operations**: Uses `asyncio.Lock` to ensure that file read/write
  operations are atomic, preventing race conditions in concurrent environments.

Usage:
------
The `CelsiusAuth` class should be instantiated with the path to a data directory.
It can then be used to authenticate users, validate sessions, and manage users.

    import asyncio
    from pathlib import Path
    from src.utils.celsius_auth import CelsiusAuth

    async def main():
        data_dir = Path("./data")
        auth = CelsiusAuth(data_dir)
        await auth.initialize() # Sets up default files if needed

        # --- Authentication ---
        success, result = await auth.authenticate("cllusion001", "T3qy22ny*@dyu0ppn*pG")
        if success:
            print(f"Login successful for user: {result['username']}")
            session_token = result['session_token']

            # --- Session Validation ---
            is_valid, session_data = await auth.validate_session(session_token)
            if is_valid:
                print(f"Session is valid for user: {session_data['username']}")

            # --- Logout ---
            await auth.logout(session_token)
            print("User logged out.")
        else:
            print(f"Login failed: {result}")

"""

import asyncio
import hashlib
import json
import logging
import os
import secrets
from datetime import datetime, timedelta
from pathlib import Path
from typing import Dict, Any, Tuple, Optional, List

logger = logging.getLogger(__name__)

AUTH_FILE_NAME = "celsius_auth.json"
SESSION_FILE_NAME = "celsius_sessions.json"
DEFAULT_SALT_LENGTH = 16
HASH_ITERATIONS = 260000  # Recommended by OWASP for SHA-256


class CelsiusAuth:
    """
    Manages user authentication and session handling for the Celsius AI system,
    using file-based storage for credentials and sessions.
    """

    def __init__(self, data_path: Path):
        """
        Initializes the authentication manager.

        Args:
            data_path (Path): The directory path for storing auth and session files.
        """
        self.data_path: Path = data_path
        self.auth_file: Path = self.data_path / AUTH_FILE_NAME
        self.session_file: Path = self.data_path / SESSION_FILE_NAME
        self._lock = asyncio.Lock()

    async def initialize(self):
        """
        Ensures the data directory and default authentication files exist.
        Should be called once before using other methods.
        """
        async with self._lock:
            try:
                start = datetime.now()
                logger.debug("Auth.initialize: ensuring data directory %s", self.data_path)
                self.data_path.mkdir(parents=True, exist_ok=True)
                if not self.auth_file.exists():
                    logger.debug("Auth.initialize: auth file missing, creating default at %s", self.auth_file)
                    await self._setup_default_auth()
                if not self.session_file.exists():
                    logger.debug("Auth.initialize: session file missing, creating at %s", self.session_file)
                    await self._save_json(self.session_file, {})
                logger.debug("Auth.initialize: completed in %s ms", int((datetime.now() - start).total_seconds() * 1000))
            except OSError as e:
                logger.critical(f"Failed to initialize auth data directory at {self.data_path}: {e}", exc_info=True)
                raise

    async def _load_json(self, file_path: Path) -> Dict[str, Any]:
        """Loads data from a JSON file."""
        try:
            start = datetime.now()
            logger.debug("Auth._load_json: loading %s", file_path)
            with open(file_path, "r", encoding="utf-8") as f:
                data = json.load(f)
            logger.debug("Auth._load_json: loaded %s in %d ms", file_path, int((datetime.now() - start).total_seconds() * 1000))
            return data
        except (FileNotFoundError, json.JSONDecodeError):
            return {}

    async def _save_json(self, file_path: Path, data: Dict[str, Any]):
        """Saves data to a JSON file."""
        start = datetime.now()
        logger.debug("Auth._save_json: saving %s", file_path)
        with open(file_path, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=4)
        logger.debug("Auth._save_json: saved %s in %d ms", file_path, int((datetime.now() - start).total_seconds() * 1000))

    def _hash_password(self, password: str, salt: Optional[bytes] = None) -> Tuple[str, str]:
        """
        Hashes a password with a salt using PBKDF2-HMAC-SHA256.

        Returns:
            A tuple containing the password hash and the salt, both hex-encoded.
        """
        if salt is None:
            salt = secrets.token_bytes(DEFAULT_SALT_LENGTH)

        pwd_hash = hashlib.pbkdf2_hmac("sha256", password.encode("utf-8"), salt, HASH_ITERATIONS)
        return pwd_hash.hex(), salt.hex()

    def _verify_password(self, stored_hash: str, stored_salt: str, provided_password: str) -> bool:
        """Verifies a provided password against a stored hash and salt."""
        try:
            # If stored_salt is missing or empty, support legacy plain-sha256 hashes
            if not stored_salt:
                legacy_hash = hashlib.sha256(provided_password.encode("utf-8")).hexdigest()
                return secrets.compare_digest(legacy_hash, stored_hash)

            salt = bytes.fromhex(stored_salt)
            new_hash, _ = self._hash_password(provided_password, salt)
            return secrets.compare_digest(new_hash, stored_hash)
        except (ValueError, TypeError):
            return False

    async def _setup_default_auth(self):
        """Sets up default authentication credentials and settings if none exist."""
        logger.info(f"Creating default authentication file at {self.auth_file}")
        password_hash, salt = self._hash_password("T3qy22ny*@dyu0ppn*pG")
        default_creds = {
            "users": {
                "cllusion001": {
                    "password_hash": password_hash,
                    "salt": salt,
                    "role": "admin",
                    "created": datetime.now().isoformat(),
                    "last_login": None,
                    "permissions": ["full_access", "system_control", "web_learning", "code_approval"],
                }
            },
            "settings": {"session_timeout_hours": 1, "max_login_attempts": 5, "lockout_duration_minutes": 5},
        }
        await self._save_json(self.auth_file, default_creds)
        logger.info("Default admin account 'cllusion001' created.")

    async def authenticate(self, username: str, password: str) -> Tuple[bool, Dict[str, Any]]:
        """
        Authenticates a user and creates a session upon success.

        Returns:
            A tuple of (bool, dict) indicating success and providing user data
            or an error message.
        """
        # Acquire the lock only for reading/updating credential files. Create
        # the session after releasing the lock to avoid deadlocks because
        # create_session itself acquires the same lock.
        start = datetime.now()
        logger.debug("Auth.authenticate: authenticating user %s", username)
        missing_user = False
        invalid_creds = False
        user_data = None

        async with self._lock:
            auth_data = await self._load_json(self.auth_file)
            users = auth_data.get("users", {})

            if username not in users:
                missing_user = True
            else:
                user_data = users[username]
                # Verify password (supports legacy unsalted SHA-256).
                verified = self._verify_password(
                    user_data.get("password_hash", ""), user_data.get("salt", ""), password
                )
                if not verified:
                    invalid_creds = True
                else:
                    # Upgrade legacy entry (missing salt) to modern salted hash
                    if not user_data.get("salt"):
                        try:
                            new_hash, new_salt = self._hash_password(password)
                            user_data["password_hash"] = new_hash
                            user_data["salt"] = new_salt
                            # persist upgrade
                            await self._save_json(self.auth_file, auth_data)
                            logger.info(f"Upgraded auth record for user {username} to salted PBKDF2 format")
                        except Exception:
                            # If upgrade fails, continue without blocking login
                            logger.exception("Failed to upgrade legacy auth record for user %s", username)

                    user_data["last_login"] = datetime.now().isoformat()
                    await self._save_json(self.auth_file, auth_data)

        # Now that credential updates are persisted and the lock released,
        # create the session (which will acquire the lock safely).
        if missing_user or invalid_creds:
            logger.debug(
                "Auth.authenticate: invalid credentials for %s (took %d ms)",
                username,
                int((datetime.now() - start).total_seconds() * 1000),
            )
            return False, {"message": "Invalid username or password"}

        session_token = await self.create_session(username)
        logger.debug(
            "Auth.authenticate: user %s authenticated in %d ms",
            username,
            int((datetime.now() - start).total_seconds() * 1000),
        )
        return True, {
            "message": "Authentication successful",
            "username": username,
            "role": user_data.get("role"),
            "permissions": user_data.get("permissions", []),
            "session_token": session_token,
        }
    async def create_session(self, username: str) -> str:
        """
        Creates a new, secure session token for a user.
        """
        async with self._lock:
            sessions = await self._load_json(self.session_file)

            # Clean expired sessions first
            current_time = datetime.now()
            sessions = {
                token: data
                for token, data in sessions.items()
                if datetime.fromisoformat(data["expires"]) > current_time
            }

            session_token = secrets.token_urlsafe(32)
            auth_data = await self._load_json(self.auth_file)
            timeout_hours = auth_data.get("settings", {}).get("session_timeout_hours", 1)

            sessions[session_token] = {
                "username": username,
                "created": datetime.now().isoformat(),
                "expires": (datetime.now() + timedelta(hours=timeout_hours)).isoformat(),
            }

            await self._save_json(self.session_file, sessions)
            return session_token

    async def validate_session(self, session_token: str) -> Tuple[bool, Dict[str, Any]]:
        """
        Validates if a session token is active and not expired.

        Returns:
            A tuple of (bool, dict) indicating validity and providing session data
            or an error message.
        """
        if not session_token:
            return False, {"message": "No session token provided"}

        async with self._lock:
            sessions = await self._load_json(self.session_file)
            session_data = sessions.get(session_token)

            if not session_data:
                return False, {"message": "Invalid session token"}

            if datetime.fromisoformat(session_data["expires"]) < datetime.now():
                # Clean up expired session
                del sessions[session_token]
                await self._save_json(self.session_file, sessions)
                return False, {"message": "Session expired"}

            return True, session_data

    async def logout(self, session_token: str) -> Tuple[bool, str]:
        """Logs out a user by invalidating their session token."""
        if not session_token:
            return False, "No session token provided."

        async with self._lock:
            sessions = await self._load_json(self.session_file)
            if session_token in sessions:
                del sessions[session_token]
                await self._save_json(self.session_file, sessions)
                return True, "Logged out successfully."
            return False, "Session token not found."

    async def create_user(
        self, username: str, password: str, role: str = "user", permissions: Optional[List[str]] = None
    ) -> Tuple[bool, str]:
        """Creates a new user account."""
        async with self._lock:
            auth_data = await self._load_json(self.auth_file)
            if username in auth_data.get("users", {}):
                return False, "Username already exists."

            if permissions is None:
                permissions = ["reports", "monitoring"] if role == "user" else ["full_access"]

            password_hash, salt = self._hash_password(password)
            auth_data["users"][username] = {
                "password_hash": password_hash,
                "salt": salt,
                "role": role,
                "created": datetime.now().isoformat(),
                "last_login": None,
                "permissions": permissions,
            }
            await self._save_json(self.auth_file, auth_data)
            return True, f"User '{username}' created successfully."

    async def change_password(self, username: str, new_password: str) -> Tuple[bool, str]:
        """Change an existing user's password to a new one (stores as salted PBKDF2).

        Returns (success, message).
        """
        async with self._lock:
            auth_data = await self._load_json(self.auth_file)
            users = auth_data.get("users", {})
            if username not in users:
                return False, "User does not exist."

            try:
                new_hash, new_salt = self._hash_password(new_password)
                users[username]["password_hash"] = new_hash
                users[username]["salt"] = new_salt
                await self._save_json(self.auth_file, auth_data)
                return True, "Password changed successfully."
            except Exception as e:
                logger.exception("Failed to change password for user %s: %s", username, e)
                return False, f"Failed to change password: {e}"

    async def get_user_info(self, username: str) -> Optional[Dict[str, Any]]:
        """Retrieves user information, excluding sensitive data."""
        async with self._lock:
            auth_data = await self._load_json(self.auth_file)
            user_data = auth_data.get("users", {}).get(username)
            if user_data:
                # Return a copy without sensitive fields
                return {
                    "username": username,
                    "role": user_data.get("role"),
                    "created": user_data.get("created"),
                    "last_login": user_data.get("last_login"),
                    "permissions": user_data.get("permissions", []),
                }
            return None


async def test_auth_system():
    """Provides a basic test and demonstration of the CelsiusAuth system."""
    print("🔐 TESTING CELSIUS AI AUTHENTICATION SYSTEM")
    print("=" * 50)

    test_data_dir = Path("./test_auth_data")
    auth = CelsiusAuth(test_data_dir)
    await auth.initialize()

    print("\n🧪 Testing Admin Login:")
    success, result = await auth.authenticate("cllusion001", "T3qy22ny*@dyu0ppn*pG")
    if success:
        print(f"✅ Admin login successful: {result['username']} ({result['role']})")
        session_token = result["session_token"]

        print("\n🧪 Testing Session Validation:")
        valid, session_data = await auth.validate_session(session_token)
        print(
            f"✅ Session valid for user: {session_data['username']}" if valid else f"❌ Session invalid: {session_data}"
        )

        print("\n🧪 Testing Logout:")
        logout_success, logout_msg = await auth.logout(session_token)
        print(f"✅ {logout_msg}" if logout_success else f"❌ {logout_msg}")

        valid_after_logout, _ = await auth.validate_session(session_token)
        print(
            "✅ Session is invalid after logout."
            if not valid_after_logout
            else "❌ Session is still valid after logout."
        )

    else:
        print(f"❌ Admin login failed: {result['message']}")

    print("\n🧪 Testing Invalid Login (wrong password):")
    success, result = await auth.authenticate("cllusion001", "wrong_password")
    print(
        f"✅ Test passed: Login failed as expected ({result['message']})."
        if not success
        else "❌ Test failed: Invalid login succeeded."
    )

    print("\n🧪 Testing User Creation:")
    create_success, create_msg = await auth.create_user("testuser", "password123")
    print(f"✅ {create_msg}" if create_success else f"❌ {create_msg}")

    print("\n🧪 Testing New User Login:")
    login_success, login_result = await auth.authenticate("testuser", "password123")
    print(
        f"✅ New user login successful."
        if login_success
        else f"❌ New user login failed: {login_result.get('message')}"
    )

    print("\n🧹 Cleaning up test files...")
    try:
        os.remove(test_data_dir / AUTH_FILE_NAME)
        os.remove(test_data_dir / SESSION_FILE_NAME)
        os.rmdir(test_data_dir)
        print("✅ Cleanup complete.")
    except OSError as e:
        print(f"❌ Error during cleanup: {e}")

    print("\n✅ Authentication system test completed!")


if __name__ == "__main__":
    asyncio.run(test_auth_system())
