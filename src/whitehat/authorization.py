"""
Celsius AI - White Hat Hacking Authorization Framework
=======================================================

Description:
------------
This module provides a framework for managing authorizations for ethical
hacking and security testing activities within the Celsius AI ecosystem. It
ensures that all security research is conducted within a clearly defined,
approved, and legally compliant scope.

IMPORTANT: This framework is designed for AUTHORIZED security testing only.
All activities must comply with applicable laws and organizational policies.

Key Features:
-------------
- **Structured Authorization Scopes**: Defines the scope of testing using a
  detailed dataclass, including target systems, allowed techniques, impact
  levels, and validity periods.
- **Asynchronous File Operations**: Uses `aiofiles` and `asyncio.Lock` to
  safely manage the authorization configuration file, preventing race
  conditions.
- **Clear Authorization Checks**: Provides a simple `is_authorized` method to
  verify if a specific testing technique is permitted under the current scope.
- **Activity Logging**: Includes a mechanism to log all authorized testing
  activities to a file for auditing and review.
- **Hierarchical Technique Definitions**: Defines a clear hierarchy of testing
  categories and techniques, allowing for granular control over permissions.
- **Graceful State Management**: Loads and saves authorization state from a
  JSON file, allowing persistence across system restarts.

Usage:
------
The `WhiteHatAuthorizationManager` is initialized with a path to a config file.
An authorization scope must be created and set before any testing can be
be performed.

    import asyncio
from pathlib import Path
from src.whitehat.authorization import WhiteHatAuthorizationManager, AuthorizationScope

    async def main():
        config_path = Path("./data/whitehat_auth.json")
        auth_manager = WhiteHatAuthorizationManager(config_path)
        await auth_manager.initialize()

        # Create and set an authorization scope
        scope = AuthorizationScope(
            target_systems=["127.0.0.1"],
            target_description="Local test server",
            authorization_level="advanced",
            network_testing=True,
            valid_from=datetime.now(),
            valid_until=datetime.now() + timedelta(days=1),
            authorized_by="Test Admin"
        )
        await auth_manager.set_authorization(scope)

        # Check if a technique is authorized
        if await auth_manager.is_authorized("port_scanning", target="127.0.0.1"):
            print("Port scanning is authorized.")
            await auth_manager.log_activity("port_scanning", "127.0.0.1", "success")
        else:
            print("Port scanning is NOT authorized.")

"""

import asyncio
import json
import logging
import uuid
from dataclasses import dataclass, asdict, field
from datetime import datetime, timedelta
from pathlib import Path
from typing import Dict, List, Optional, Any, Set

import aiofiles

logger = logging.getLogger(__name__)


@dataclass
class AuthorizationScope:
    """Defines the scope of authorized security testing activities."""

    target_systems: List[str]
    target_description: str
    authorization_level: str  # 'basic', 'intermediate', 'advanced', 'expert'
    authorized_by: str
    valid_from: datetime
    valid_until: datetime

    authorization_id: str = field(default_factory=lambda: str(uuid.uuid4()))

    # Testing Categories
    network_testing: bool = False
    web_application_testing: bool = False
    social_engineering_testing: bool = False
    malware_analysis: bool = False

    # Constraints
    max_impact_level: str = "low"  # 'none', 'low', 'medium', 'high'
    testing_hours: str = "24/7"
    data_handling: str = "no_exfiltration"

    # Legal and Compliance
    legal_authorization: bool = True
    incident_response_contact: str = ""


class WhiteHatAuthorizationManager:
    """Manages authorization for ethical hacking activities asynchronously."""

    def __init__(self, config_path: Path):
        self.config_path: Path = config_path
        self.current_authorization: Optional[AuthorizationScope] = None
        self._lock = asyncio.Lock()

        # Define available testing categories and techniques
        self.testing_categories: Dict[str, Dict[str, Any]] = {
            "network_testing": {
                "description": "Network infrastructure assessment",
                "techniques": {"port_scanning", "service_enumeration", "vulnerability_scanning"},
                "risk_map": {
                    "basic": {"port_scanning"},
                    "intermediate": {"service_enumeration"},
                    "advanced": {"vulnerability_scanning"},
                },
            },
            "web_application_testing": {
                "description": "Web application security assessment",
                "techniques": {"sql_injection", "xss", "csrf"},
                "risk_map": {"intermediate": {"xss"}, "advanced": {"sql_injection", "csrf"}},
            },
            # Add other categories as needed
        }

    async def initialize(self):
        """Loads authorization from the config file."""
        self.config_path.parent.mkdir(parents=True, exist_ok=True)
        await self._load_authorization()

    async def _load_authorization(self):
        """Loads the current authorization scope from the JSON file."""
        async with self._lock:
            if not self.config_path.exists():
                return
            try:
                async with aiofiles.open(self.config_path, "r") as f:
                    content = await f.read()
                    data = json.loads(content)

                if auth_data := data.get("current_authorization"):
                    auth_data["valid_from"] = datetime.fromisoformat(auth_data["valid_from"])
                    auth_data["valid_until"] = datetime.fromisoformat(auth_data["valid_until"])
                    self.current_authorization = AuthorizationScope(**auth_data)
                    logger.info(f"Authorization '{self.current_authorization.authorization_id}' loaded.")
            except (json.JSONDecodeError, TypeError, FileNotFoundError) as e:
                logger.error(f"Failed to load authorization file: {e}")
                self.current_authorization = None

    async def _save_authorization(self):
        """Saves the current authorization scope to the JSON file."""
        async with self._lock:
            data_to_save = {"current_authorization": None, "last_updated": datetime.now().isoformat()}
            if self.current_authorization:
                auth_dict = asdict(self.current_authorization)
                auth_dict["valid_from"] = auth_dict["valid_from"].isoformat()
                auth_dict["valid_until"] = auth_dict["valid_until"].isoformat()
                data_to_save["current_authorization"] = auth_dict

            async with aiofiles.open(self.config_path, "w") as f:
                await f.write(json.dumps(data_to_save, indent=4))

    async def set_authorization(self, scope: AuthorizationScope):
        """Sets and saves a new authorization scope."""
        self.current_authorization = scope
        await self._save_authorization()
        logger.info(f"New authorization set: {scope.authorization_id}")

    async def revoke_authorization(self):
        """Revokes the current authorization."""
        if self.current_authorization:
            logger.info(f"Revoking authorization: {self.current_authorization.authorization_id}")
            self.current_authorization = None
            await self._save_authorization()

    async def is_authorized(self, technique: str, target: Optional[str] = None) -> bool:
        """
        Checks if a specific technique is authorized against a target.
        """
        if not self.current_authorization:
            return False

        # Check validity period
        now = datetime.now()
        if not (self.current_authorization.valid_from <= now <= self.current_authorization.valid_until):
            logger.warning("Authorization is expired or not yet active.")
            return False

        # Check target scope
        if target and not any(t in target for t in self.current_authorization.target_systems):
            logger.warning(f"Target '{target}' is outside the authorized scope.")
            return False

        # Check technique and authorization level
        auth_level = self.current_authorization.authorization_level
        for category_name, category_details in self.testing_categories.items():
            if technique in category_details["techniques"]:
                # Is the category enabled in the scope?
                if not getattr(self.current_authorization, category_name, False):
                    return False

                # Is the technique allowed at the current auth level?
                for level, allowed_techs in category_details["risk_map"].items():
                    if technique in allowed_techs:
                        if auth_level == "basic" and level in ["intermediate", "advanced", "expert"]:
                            return False
                        if auth_level == "intermediate" and level in ["advanced", "expert"]:
                            return False
                        if auth_level == "advanced" and level == "expert":
                            return False
                        return True  # Authorized

        logger.warning(f"Technique '{technique}' not found in any authorized category.")
        return False

    async def get_authorized_techniques(self) -> Set[str]:
        """Returns a set of all currently authorized techniques."""
        if not self.current_authorization:
            return set()

        authorized_techs = set()
        for category_name, category_details in self.testing_categories.items():
            for tech in category_details["techniques"]:
                if await self.is_authorized(tech):
                    authorized_techs.add(tech)
        return authorized_techs

    async def log_activity(self, technique: str, target: str, result: str, details: Optional[Dict] = None):
        """Logs an authorized testing activity to a file."""
        if not self.current_authorization:
            logger.error("Attempted to log activity without active authorization.")
            return

        log_entry = {
            "timestamp": datetime.now().isoformat(),
            "authorization_id": self.current_authorization.authorization_id,
            "technique": technique,
            "target": target,
            "result": result,
            "details": details or {},
        }

        log_file = self.config_path.parent / "whitehat_activity.log"
        async with aiofiles.open(log_file, "a") as f:
            await f.write(json.dumps(log_entry) + "\n")
        logger.info(f"Activity logged: {technique} on {target}")
