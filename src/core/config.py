"""
Celsius AI - Configuration Management
=====================================

Description:
------------
This module provides a centralized system for managing the configuration of the
Celsius AI ecosystem. It uses a `dataclass` for a strongly-typed configuration
object, which can be loaded from a JSON file and overridden by environment
variables.

Key Features:
-------------
- **Strongly-Typed Config**: Uses Python's `dataclasses` to define a clear and
  predictable configuration structure.
- **JSON Loading**: Loads default settings from a `config.json` file.
- **Environment Variable Override**: Allows for flexible configuration in different
  environments (development, production) by overriding JSON values with
  environment variables.
- **Automatic Directory Creation**: Ensures that necessary directories for logs and
  data are created on startup.
- **Default Configuration**: Can generate a default `config.json` file if one
  does not exist.

Usage:
------
The `load_config()` function is the primary entry point for the rest of the
application to get configuration settings.

    from core.config import load_config
    config = load_config()
    print(f"Log level is: {config.log_level}")

Environment variables should be prefixed with `CELSIUS_` (e.g., `CELSIUS_LOG_LEVEL=DEBUG`).
"""

import os
import json
from dataclasses import dataclass, field
from typing import Dict, List, Optional, Any
from pathlib import Path

# Define the root of the project to resolve paths correctly
PROJECT_ROOT = Path(__file__).resolve().parents[2]


@dataclass
class CelsiusConfig:
    """
    A dataclass holding all configuration parameters for the Celsius AI Assistant.
    Provides default values for each setting.
    """

    # --- AI Model Configuration ---
    ai_model: str = "microsoft/DialoGPT-medium"
    """Specifies the local Hugging Face model to be used for general NLP tasks."""

    use_openai: bool = False
    """If True, the system will attempt to use the OpenAI API for more advanced queries."""

    openai_api_key: Optional[str] = None
    """The API key for accessing OpenAI services. Loaded from environment variables."""

    # --- Security Configuration ---
    security_scan_interval: int = 300
    """The interval in seconds for periodic automated security scans (default: 5 minutes)."""

    threat_db_path: str = str(PROJECT_ROOT / "data/threats.db")
    """The file path for the SQLite database storing threat intelligence."""

    quarantine_path: str = str(PROJECT_ROOT / "quarantine/")
    """The directory where potentially malicious files are moved for isolation."""

    # --- Device Management ---
    device_discovery_enabled: bool = True
    """If True, the system will periodically scan for and manage connected devices."""

    sync_interval: int = 600
    """The interval in seconds for synchronizing status with managed devices (default: 10 minutes)."""

    # --- Network Configuration ---
    monitor_network: bool = True
    """If True, the system will monitor network traffic for anomalies."""

    network_interface: Optional[str] = None
    """The specific network interface to monitor (e.g., 'eth0'). If None, it may try to find the default."""

    # --- Intelligence Sources ---
    virustotal_api_key: Optional[str] = None
    """API key for VirusTotal to enrich threat intelligence data."""

    misp_url: Optional[str] = None
    """URL for a MISP (Malware Information Sharing Platform) instance."""

    misp_key: Optional[str] = None
    """API key for the MISP instance."""

    # --- Logging ---
    log_level: str = "INFO"
    """The minimum level of logs to record (e.g., DEBUG, INFO, WARNING, ERROR)."""

    log_file: str = str(PROJECT_ROOT / "logs/celsius_ai.log")
    """The path to the main application log file."""

    # --- Database ---
    db_url: str = f"sqlite:///{PROJECT_ROOT / 'data/celsius_ai.db'}"
    """The connection URL for the main application database."""

    # --- API Configuration ---
    api_host: str = "127.0.0.1"
    """The host address for the FastAPI backend."""

    api_port: int = 8000
    """The port for the FastAPI backend."""

    api_enabled: bool = True
    """If True, the FastAPI backend will be enabled."""

    def __post_init__(self):
        """
        Performs validation and setup after the dataclass is initialized.
        This method automatically creates necessary directories.
        """
        # Ensure paths are absolute and directories exist
        for path_attr in ["threat_db_path", "quarantine_path", "log_file", "db_url"]:
            path_val = getattr(self, path_attr)
            # For db_url, we only want the directory part
            if path_val.startswith("sqlite:///"):
                path_val = path_val[10:]

            p = Path(path_val)
            # Create parent directory if it's a file path
            if p.suffix:
                p.parent.mkdir(parents=True, exist_ok=True)
            # Create the directory itself if it's a directory path
            else:
                p.mkdir(parents=True, exist_ok=True)


def load_config(config_path: str = "config.json") -> CelsiusConfig:
    """
    Loads configuration from a JSON file and overrides it with any matching
    environment variables.

    Args:
        config_path (str): The path to the JSON configuration file.

    Returns:
        CelsiusConfig: An instance of the configuration object.
    """
    config_data = {}
    full_config_path = PROJECT_ROOT / config_path

    # Load from config file if it exists
    if full_config_path.exists():
        try:
            with open(full_config_path, "r") as f:
                config_data = json.load(f)
        except Exception as e:
            print(f"Warning: Could not load config file {full_config_path}: {e}")

    # Define mappings from environment variables to config keys
    env_mappings = {
        "CELSIUS_AI_MODEL": "ai_model",
        "CELSIUS_USE_OPENAI": "use_openai",
        "OPENAI_API_KEY": "openai_api_key",
        "VIRUSTOTAL_API_KEY": "virustotal_api_key",
        "MISP_URL": "misp_url",
        "MISP_KEY": "misp_key",
        "CELSIUS_LOG_LEVEL": "log_level",
        "CELSIUS_DB_URL": "db_url",
        "CELSIUS_API_HOST": "api_host",
        "CELSIUS_API_PORT": "api_port",
    }

    # Override with environment variables
    for env_var, config_key in env_mappings.items():
        if env_var in os.environ:
            value = os.environ[env_var]
            # Coerce type for boolean and integer values
            if config_key in ["use_openai", "device_discovery_enabled", "monitor_network", "api_enabled"]:
                value = value.lower() in ("true", "1", "yes", "on")
            elif config_key in ["security_scan_interval", "sync_interval", "api_port"]:
                try:
                    value = int(value)
                except ValueError:
                    print(f"Warning: Could not convert env var {env_var} to int. Using default.")
                    continue
            config_data[config_key] = value

    return CelsiusConfig(**config_data)


def save_config(config: CelsiusConfig, config_path: str = "config.json"):
    """
    Saves the current configuration object to a JSON file.

    Args:
        config (CelsiusConfig): The configuration object to save.
        config_path (str): The path to the destination JSON file.
    """
    # Create a dictionary from the dataclass, excluding sensitive keys if necessary
    config_dict = {
        "ai_model": config.ai_model,
        "use_openai": config.use_openai,
        "security_scan_interval": config.security_scan_interval,
        "threat_db_path": config.threat_db_path,
        "quarantine_path": config.quarantine_path,
        "device_discovery_enabled": config.device_discovery_enabled,
        "sync_interval": config.sync_interval,
        "monitor_network": config.monitor_network,
        "network_interface": config.network_interface,
        "log_level": config.log_level,
        "log_file": config.log_file,
        "db_url": config.db_url,
        "api_host": config.api_host,
        "api_port": config.api_port,
        "api_enabled": config.api_enabled,
    }
    full_config_path = PROJECT_ROOT / config_path

    try:
        with open(full_config_path, "w") as f:
            json.dump(config_dict, f, indent=4)
        print(f"Configuration saved to {full_config_path}")
    except Exception as e:
        print(f"Error: Could not save configuration to {full_config_path}: {e}")


def create_default_config(config_path: str = "config.json") -> CelsiusConfig:
    """
    Creates and saves a default configuration file.

    Args:
        config_path (str): The path where the default config file will be saved.

    Returns:
        CelsiusConfig: The default configuration object.
    """
    print("Creating default configuration file...")
    config = CelsiusConfig()
    save_config(config, config_path)
    return config
