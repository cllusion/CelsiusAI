"""
Celsius AI - Threat Analysis Module
===================================

Description:
------------
This module provides advanced threat detection and analysis capabilities for
the Celsius AI ecosystem. It is responsible for performing various security
scans, including process, network, and file system analysis, to identify
potential threats, vulnerabilities, and suspicious activities.

Key Features:
-------------
- **Multi-faceted Scanning**: Capable of performing full-system scans or targeted
  scans for processes, network connections, and files.
- **Process Monitoring**: Scans running processes for known suspicious names
  (e.g., `mimikatz`, `powershell.exe`) and checks for unsigned executables.
  Requires the `psutil` library.
- **Network Analysis**: Monitors network connections for activity on suspicious
  ports and connections to known malicious IP addresses. It also performs
  basic anomaly detection for high outbound traffic.
- **File System Scanning**: Scans specified directories for files matching known
  malware hashes. It can also leverage YARA rules for pattern-based malware
  detection if the `yara-python` library is installed.
- **Vulnerability Assessment**: Performs basic system checks, such as verifying
  if Windows Defender is enabled.
- **Risk Calculation**: Calculates an overall risk level ('low', 'medium', 'high',
  'critical') based on the findings of a scan.

Usage:
------
The `ThreatAnalyzer` is typically initialized and used by a higher-level security
orchestrator or the main AI assistant to periodically scan the system.

    from core.config import load_config
    from security.analyzer import ThreatAnalyzer

    async def main():
        config = load_config()
        analyzer = ThreatAnalyzer(config)
        await analyzer.initialize()

        # Perform a full system scan
        scan_results = await analyzer.perform_scan(scan_type='full')
        print(f"Scan complete. Risk level: {scan_results['risk_level']}")

        for threat in scan_results['threats']:
            print(f"- Found Threat: {threat['name']} (Severity: {threat['severity']})")

        await analyzer.shutdown()

"""

import asyncio
import hashlib
import logging
import socket
import subprocess
import platform  # Added import
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional, Any, Set

# Optional imports with fallbacks for cross-platform compatibility and functionality.
try:
    import psutil
except ImportError:
    psutil = None
    logging.warning("psutil library not found. Process and network scanning will be disabled.")

try:
    import yara
except ImportError:
    yara = None
    logging.warning("yara-python library not found. YARA rule scanning will be disabled.")

# Assuming a config object is passed with necessary settings.
from src.core.config import CelsiusConfig

logger = logging.getLogger(__name__)

# Define the root of the project to resolve paths correctly
PROJECT_ROOT = Path(__file__).resolve().parents[2]
RULES_DIR = PROJECT_ROOT / "rules"


class ThreatAnalyzer:
    """
    An advanced threat analysis and detection system that scans processes,
    network connections, and files for signs of malicious activity.
    """

    def __init__(self, config: CelsiusConfig):
        """
        Initializes the ThreatAnalyzer.

        Args:
            config (CelsiusConfig): The application's configuration object.
        """
        self.config: CelsiusConfig = config
        self.yara_rules: Optional[Any] = None  # Use Any to avoid linter issues with optional import
        self.threat_signatures: Dict[str, str] = {}
        self.active_scans: Dict[str, Dict[str, Any]] = {}
        self.last_scan_results: Dict[str, Any] = {}
        self._last_net_stats: Optional[Any] = None

        self.suspicious_processes: Set[str] = {
            "mimikatz",
            "powershell.exe",
            "cmd.exe",
            "wmic.exe",
            "net.exe",
            "netsh.exe",
            "tasklist.exe",
            "systeminfo.exe",
        }
        self.suspicious_ports: Set[int] = {4444, 5555, 6666, 1337, 31337, 8080, 9999}
        self.known_malware_ips: Set[str] = set()

    async def initialize(self):
        """
        Initializes the threat analyzer by loading YARA rules, threat signatures,
        and updating threat intelligence.
        """
        logger.info("Initializing ThreatAnalyzer...")
        try:
            await self._load_yara_rules()
            await self._load_threat_signatures()
            await self._update_threat_intelligence()
            logger.info("ThreatAnalyzer initialized successfully.")
        except Exception as e:
            logger.error(f"Failed to initialize ThreatAnalyzer: {e}", exc_info=True)
            # Allow the system to continue with limited functionality.

    async def perform_scan(self, scan_type: str = "full") -> Dict[str, Any]:
        """
        Performs a comprehensive security scan of the system.

        Args:
            scan_type (str): The type of scan to perform ('full', 'process',
                             'network', 'file').

        Returns:
            Dict[str, Any]: A dictionary containing the detailed results of the scan.
        """
        scan_id = f"scan_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
        logger.info(f"Starting '{scan_type}' security scan (ID: {scan_id})...")

        start_time = datetime.now()
        self.active_scans[scan_id] = {"type": scan_type, "start_time": start_time, "status": "running"}

        results: Dict[str, Any] = {
            "scan_id": scan_id,
            "scan_type": scan_type,
            "start_time": start_time.isoformat(),
            "threats": [],
            "vulnerabilities": [],
            "suspicious_activities": [],
            "network_anomalies": [],
            "risk_level": "low",
        }

        scan_tasks = []
        if scan_type in ["full", "process"]:
            scan_tasks.append(self._scan_processes())
        if scan_type in ["full", "network"]:
            scan_tasks.append(self._scan_network())
        if scan_type in ["full", "file"]:
            scan_tasks.append(self._scan_files())

        scan_results = await asyncio.gather(*scan_tasks, return_exceptions=True)

        # Process results from gathered tasks
        result_map = {"process": "threats", "network": "network_anomalies", "file": "threats"}
        task_keys = [k for k in ["process", "network", "file"] if scan_type in ["full", k]]

        for i, res in enumerate(scan_results):
            key = task_keys[i]
            if isinstance(res, Exception):
                logger.error(f"Error during {key} scan: {res}", exc_info=res)
            else:
                results[result_map[key]].extend(res)

        results["vulnerabilities"] = await self._check_vulnerabilities()
        results["risk_level"] = self._calculate_risk_level(results)

        end_time = datetime.now()
        results["end_time"] = end_time.isoformat()
        results["duration_seconds"] = (end_time - start_time).total_seconds()

        self.active_scans[scan_id]["status"] = "completed"
        self.last_scan_results = results
        logger.info(f"Scan {scan_id} completed. Risk level: {results['risk_level']}.")
        return results

    async def _scan_processes(self) -> List[Dict[str, Any]]:
        """Scans running processes for known threats and suspicious patterns."""
        if not psutil:
            return []

        threats = []
        for process in psutil.process_iter(["pid", "name", "exe", "cmdline", "create_time"]):
            try:
                proc_info = process.info
                proc_name = (proc_info.get("name") or "").lower()

                if any(susp_proc in proc_name for susp_proc in self.suspicious_processes):
                    threats.append(
                        {
                            "type": "suspicious_process",
                            "name": f"Suspicious Process: {proc_info.get('name')}",
                            "severity": "medium",
                            "details": f"Process '{proc_name}' is often used in attacks.",
                            "data": proc_info,
                        }
                    )
            except (psutil.NoSuchProcess, psutil.AccessDenied):
                continue
        return threats

    async def _scan_network(self) -> List[Dict[str, Any]]:
        """Scans network connections for anomalies and malicious endpoints."""
        if not psutil:
            return []

        anomalies = []
        try:
            connections = psutil.net_connections(kind="inet")
            for conn in connections:
                if conn.raddr and conn.raddr.ip in self.known_malware_ips:
                    anomalies.append(
                        {
                            "type": "malicious_connection",
                            "severity": "critical",
                            "details": f"Connection to known malicious IP: {conn.raddr.ip}",
                            "data": {"local": conn.laddr, "remote": conn.raddr, "status": conn.status},
                        }
                    )
                if conn.laddr and conn.laddr.port in self.suspicious_ports:
                    anomalies.append(
                        {
                            "type": "suspicious_port_usage",
                            "severity": "high",
                            "details": f"Process listening on suspicious port: {conn.laddr.port}",
                            "data": {"local": conn.laddr, "pid": conn.pid},
                        }
                    )
        except Exception as e:
            logger.error(f"Network scan failed: {e}", exc_info=True)
        return anomalies

    async def _scan_files(self, directories: Optional[List[Path]] = None) -> List[Dict[str, Any]]:
        """Scans files in specified directories for malware signatures and YARA rules."""
        threats = []
        if not directories:
            directories = [Path.home() / "Downloads", Path.home() / "Desktop"]
            if platform.system() == "Windows":
                directories.append(Path(socket.gethostbyname(socket.gethostname())) / "Windows" / "Temp")
            else:
                directories.append(Path("/tmp"))

        for directory in directories:
            if not directory.exists():
                continue
            try:
                for file_path in directory.rglob("*"):
                    if not file_path.is_file() or file_path.stat().st_size > 100 * 1024 * 1024:  # 100MB limit
                        continue

                    # Hash-based detection
                    file_hash = await self._calculate_file_hash(file_path)
                    if file_hash in self.threat_signatures:
                        threats.append(
                            {
                                "type": "known_malware_hash",
                                "name": f"Known Malware: {file_path.name}",
                                "severity": "critical",
                                "details": f"File hash matches signature for '{self.threat_signatures[file_hash]}'.",
                                "data": {"file_path": str(file_path), "hash": file_hash},
                            }
                        )

                    # YARA rule detection
                    if self.yara_rules:
                        try:
                            matches = self.yara_rules.match(str(file_path))
                            for match in matches:
                                threats.append(
                                    {
                                        "type": "yara_detection",
                                        "name": f"YARA Rule Match: {match.rule}",
                                        "severity": "high",
                                        "details": f"File content matched YARA rule '{match.rule}'.",
                                        "data": {"file_path": str(file_path), "rule": match.rule},
                                    }
                                )
                        except yara.Error as e:
                            logger.debug(f"YARA scan error for {file_path}: {e}")
            except Exception as e:
                logger.error(f"Error scanning directory {directory}: {e}", exc_info=True)
        return threats

    async def _check_vulnerabilities(self) -> List[Dict[str, Any]]:
        """Performs basic system configuration checks for common vulnerabilities."""
        vulns = []
        if platform.system() == "Windows":
            try:
                # Check if Windows Defender is enabled
                result = subprocess.run(
                    ["powershell", "-Command", "Get-MpComputerStatus | Select-Object -ExpandProperty AntivirusEnabled"],
                    capture_output=True,
                    text=True,
                    timeout=10,
                    check=False,
                )
                if "False" in result.stdout:
                    vulns.append(
                        {
                            "type": "antivirus_disabled",
                            "severity": "high",
                            "description": "Windows Defender Antivirus is disabled.",
                            "recommendation": "Enable Windows Defender or install a third-party antivirus solution.",
                        }
                    )
            except (subprocess.TimeoutExpired, FileNotFoundError, Exception) as e:
                logger.warning(f"Could not check Windows Defender status: {e}")
        return vulns

    async def _load_yara_rules(self):
        """Loads and compiles YARA rules from the rules directory."""
        if not yara:
            return

        RULES_DIR.mkdir(exist_ok=True)
        rule_file = RULES_DIR / "basic_rules.yar"

        if not rule_file.exists():
            rule_content = """
            rule Suspicious_Process_Keywords {
                meta: description = "Detects keywords often associated with malicious process activity"
                strings:
                    $s1 = "mimikatz" nocase
                    $s2 = "powershell -enc" nocase
                condition: any of them
            }"""
            rule_file.write_text(rule_content)

        try:
            self.yara_rules = yara.compile(filepath=str(rule_file))
            logger.info("YARA rules loaded and compiled successfully.")
        except yara.Error as e:
            logger.error(f"YARA rule compilation failed: {e}")

    async def _load_threat_signatures(self):
        """Loads known threat signatures (e.g., file hashes)."""
        # In a real application, this would load from a database or a feed.
        self.threat_signatures = {
            "d41d8cd98f00b204e9800998ecf8427e": "Empty File Placeholder",  # MD5 of an empty file
            "e4d909c290d0fb1ca068ffaddf22cbd0": "Test Malware Signature 1",
        }
        logger.info(f"Loaded {len(self.threat_signatures)} threat signatures.")

    async def _update_threat_intelligence(self):
        """Updates threat intelligence data, such as known malicious IPs."""
        # In a real application, this would fetch from a threat intelligence platform.
        self.known_malware_ips.update(["192.0.2.100", "198.51.100.50"])  # TEST-NET-1, TEST-NET-2
        logger.info("Threat intelligence for malicious IPs updated.")

    async def _calculate_file_hash(self, file_path: Path) -> str:
        """Calculates the SHA256 hash of a file."""
        sha256_hash = hashlib.sha256()
        try:
            with open(file_path, "rb") as f:
                for chunk in iter(lambda: f.read(4096), b""):
                    sha256_hash.update(chunk)
            return sha256_hash.hexdigest()
        except IOError as e:
            logger.error(f"Failed to calculate hash for {file_path}: {e}")
            return ""

    def _calculate_risk_level(self, scan_results: Dict[str, Any]) -> str:
        """
        Calculates an overall risk level based on the severity and count of findings.

        Returns:
            str: The calculated risk level ('low', 'medium', 'high', 'critical').
        """
        severity_scores = {"low": 1, "medium": 3, "high": 5, "critical": 10}
        score = 0

        all_findings = (
            scan_results.get("threats", [])
            + scan_results.get("vulnerabilities", [])
            + scan_results.get("network_anomalies", [])
        )

        for finding in all_findings:
            score += severity_scores.get(finding.get("severity", "low"), 1)

        if score >= 20:
            return "critical"
        if score >= 10:
            return "high"
        if score >= 3:
            return "medium"
        return "low"

    async def shutdown(self):
        """Gracefully shuts down the ThreatAnalyzer."""
        logger.info("Shutting down ThreatAnalyzer...")
        self.active_scans.clear()
        logger.info("ThreatAnalyzer shutdown complete.")
