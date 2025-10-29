#!/usr/bin/env python3
"""
Celsius AI Authentication System
Cross-compatible authentication for Web UI and Server Hub
"""

import hashlib
import json
import os
from datetime import datetime, timedelta
import secrets


class CelsiusAuth:
    """Authentication manager for Celsius AI system"""

    def __init__(self):
        self.auth_file = "celsius_auth.json"
        self.session_file = "celsius_sessions.json"
        self.setup_default_auth()

    def setup_default_auth(self):
        """Setup default authentication if none exists"""
        if not os.path.exists(self.auth_file):
            # Create default credentials - single admin account
            default_creds = {
                "users": {
                    "cllusion001": {
                        "password_hash": self.hash_password("T3qy22ny*@dyu0ppn*pG"),
                        "role": "admin",
                        "created": datetime.now().isoformat(),
                        "last_login": None,
                        "permissions": [
                            "full_access",
                            "system_control",
                            "reports",
                            "settings",
                            "web_learning",
                            "code_approval",
                        ],
                    }
                },
                "settings": {
                    "session_timeout": 3600,  # 1 hour
                    "max_login_attempts": 5,
                    "lockout_duration": 300,  # 5 minutes
                },
            }

            with open(self.auth_file, "w") as f:
                json.dump(default_creds, f, indent=4)

            print("🔐 Default authentication setup completed:")
            print("   Admin: cllusion001 / T3qy22ny*@dyu0ppn*pG")

    def hash_password(self, password):
        """Hash password with salt"""
        salt = "celsius_ai_salt_2025"
        return hashlib.sha256((password + salt).encode()).hexdigest()

    def authenticate(self, username, password):
        """Authenticate user credentials"""
        try:
            with open(self.auth_file, "r") as f:
                auth_data = json.load(f)

            if username not in auth_data["users"]:
                return False, "Invalid username"

            user_data = auth_data["users"][username]
            password_hash = self.hash_password(password)

            if password_hash != user_data["password_hash"]:
                return False, "Invalid password"

            # Update last login
            user_data["last_login"] = datetime.now().isoformat()

            with open(self.auth_file, "w") as f:
                json.dump(auth_data, f, indent=4)

            # Create session
            session_token = self.create_session(username)

            return True, {
                "username": username,
                "role": user_data["role"],
                "permissions": user_data["permissions"],
                "session_token": session_token,
            }

        except Exception as e:
            return False, f"Authentication error: {str(e)}"

    def create_session(self, username):
        """Create secure session token"""
        session_token = secrets.token_urlsafe(32)
        session_data = {
            "username": username,
            "created": datetime.now().isoformat(),
            "expires": (datetime.now() + timedelta(hours=1)).isoformat(),
            "active": True,
        }

        # Load existing sessions
        sessions = {}
        if os.path.exists(self.session_file):
            with open(self.session_file, "r") as f:
                sessions = json.load(f)

        sessions[session_token] = session_data

        # Clean expired sessions
        current_time = datetime.now()
        sessions = {
            token: data for token, data in sessions.items() if datetime.fromisoformat(data["expires"]) > current_time
        }

        with open(self.session_file, "w") as f:
            json.dump(sessions, f, indent=4)

        return session_token

    def validate_session(self, session_token):
        """Validate session token"""
        try:
            if not os.path.exists(self.session_file):
                return False, "No active sessions"

            with open(self.session_file, "r") as f:
                sessions = json.load(f)

            if session_token not in sessions:
                return False, "Invalid session token"

            session_data = sessions[session_token]
            expires = datetime.fromisoformat(session_data["expires"])

            if datetime.now() > expires:
                # Clean expired session
                del sessions[session_token]
                with open(self.session_file, "w") as f:
                    json.dump(sessions, f, indent=4)
                return False, "Session expired"

            return True, session_data

        except Exception as e:
            return False, f"Session validation error: {str(e)}"

    def logout(self, session_token):
        """Logout and invalidate session"""
        try:
            if os.path.exists(self.session_file):
                with open(self.session_file, "r") as f:
                    sessions = json.load(f)

                if session_token in sessions:
                    del sessions[session_token]

                    with open(self.session_file, "w") as f:
                        json.dump(sessions, f, indent=4)

            return True, "Logged out successfully"

        except Exception as e:
            return False, f"Logout error: {str(e)}"

    def create_user(self, username, password, role="user"):
        """Create new user account"""
        try:
            with open(self.auth_file, "r") as f:
                auth_data = json.load(f)

            if username in auth_data["users"]:
                return False, "Username already exists"

            permissions = ["reports", "monitoring"]
            if role == "admin":
                permissions = ["full_access", "system_control", "reports", "settings"]

            auth_data["users"][username] = {
                "password_hash": self.hash_password(password),
                "role": role,
                "created": datetime.now().isoformat(),
                "last_login": None,
                "permissions": permissions,
            }

            with open(self.auth_file, "w") as f:
                json.dump(auth_data, f, indent=4)

            return True, "User created successfully"

        except Exception as e:
            return False, f"User creation error: {str(e)}"

    def get_user_info(self, username):
        """Get user information"""
        try:
            with open(self.auth_file, "r") as f:
                auth_data = json.load(f)

            if username not in auth_data["users"]:
                return None

            user_data = auth_data["users"][username].copy()
            del user_data["password_hash"]  # Don't return password hash
            return user_data

        except Exception as e:
            return None


def test_auth_system():
    """Test the authentication system"""
    print("🔐 TESTING CELSIUS AI AUTHENTICATION SYSTEM")
    print("=" * 50)

    auth = CelsiusAuth()

    # Test authentication
    print("\n🧪 Testing Login:")
    success, result = auth.authenticate("celsius_admin", "celsius2025")
    if success:
        print(f"✅ Admin login successful: {result['username']} ({result['role']})")
        session_token = result["session_token"]

        # Test session validation
        print("\n🧪 Testing Session Validation:")
        valid, session_data = auth.validate_session(session_token)
        if valid:
            print(f"✅ Session valid: {session_data['username']}")
        else:
            print(f"❌ Session invalid: {session_data}")

        # Test logout
        print("\n🧪 Testing Logout:")
        logout_success, logout_msg = auth.logout(session_token)
        print(f"{'✅' if logout_success else '❌'} {logout_msg}")

    else:
        print(f"❌ Admin login failed: {result}")

    # Test invalid login
    print("\n🧪 Testing Invalid Login:")
    success, result = auth.authenticate("invalid_user", "wrong_password")
    print(f"{'❌' if not success else '✅'} Expected failure: {result}")

    print("\n✅ Authentication system test completed!")


if __name__ == "__main__":
    test_auth_system()
