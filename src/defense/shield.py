"""
Defense Shield - IP Blocklist, Log Analysis, and Hardening Recommendations
Celsius AI - Active Defense Module
"""

import json
import re
import logging
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Any, Optional

logger = logging.getLogger(__name__)

LOG_ATTACK_PATTERNS = {
    "sql_injection": r"(?i)('|--|;|\bunion\b|\bselect\b|\bdrop\b|\binsert\b|\bdelete\b|\bexec\b|xp_)",
    "xss": r"(?i)(<script|javascript:|onerror=|onload=|alert\(|document\.cookie)",
    "path_traversal": r"(\.\./|%2e%2e%2f|%252e%252e|/etc/passwd|/etc/shadow|\\\\windows)",
    "brute_force": r"(?i)(failed password|authentication failure|invalid credentials|login failed)",
    "scanner": r"(?i)(nikto|sqlmap|gobuster|nuclei|nmap|masscan|dirbuster|wfuzz)",
    "command_injection": r"(?i)(;\s*(?:cat|ls|id|whoami|curl|wget)|\|\s*(?:bash|sh|cmd)|`[^`]+`)",
}

IP_REGEX = re.compile(
    r'\b((?:(?:25[0-5]|2[0-4]\d|[01]?\d\d?)\.){3}(?:25[0-5]|2[0-4]\d|[01]?\d\d?))\b'
)

HARDENING_CHECKLIST = [
    {"priority": 1, "category": "authentication", "title": "Enable Multi-Factor Authentication",
     "detail": "Require MFA for all admin and privileged accounts."},
    {"priority": 2, "category": "headers", "title": "Set Security HTTP Headers",
     "detail": "Add HSTS, CSP, X-Frame-Options, X-Content-Type-Options headers."},
    {"priority": 3, "category": "firewall", "title": "Configure Host Firewall",
     "detail": "Allow only necessary inbound ports; deny all by default."},
    {"priority": 4, "category": "updates", "title": "Apply Security Patches",
     "detail": "Keep OS, runtimes, and dependencies up-to-date; enable auto-updates."},
    {"priority": 5, "category": "logging", "title": "Enable Centralised Logging",
     "detail": "Forward logs to a SIEM or centralised log store with alerting."},
    {"priority": 6, "category": "backups", "title": "Implement Tested Backups",
     "detail": "Schedule automated backups; test restoration regularly."},
    {"priority": 7, "category": "secrets", "title": "Rotate Secrets and Keys",
     "detail": "Store credentials in a vault; rotate API keys and passwords on schedule."},
    {"priority": 8, "category": "network", "title": "Segment the Network",
     "detail": "Isolate services into network segments; restrict lateral movement."},
    {"priority": 9, "category": "monitoring", "title": "Deploy Intrusion Detection",
     "detail": "Use an IDS/IPS to detect and alert on anomalous traffic patterns."},
]


class DefenseShield:
    """Active defense: IP blocklist management, log analysis, and hardening."""

    def __init__(self, blocklist_path: str = "data/blocklist.json"):
        self.blocklist_path = Path(blocklist_path)
        self.blocklist: Dict[str, Dict[str, Any]] = {}
        self.threat_log: List[Dict[str, Any]] = []
        self._load_blocklist()

    def _load_blocklist(self) -> None:
        if self.blocklist_path.exists():
            try:
                with open(self.blocklist_path, "r") as f:
                    self.blocklist = json.load(f)
            except (json.JSONDecodeError, OSError) as e:
                logger.warning(f"Could not load blocklist: {e}")
                self.blocklist = {}
        else:
            self.blocklist = {}

    def _save_blocklist(self) -> None:
        try:
            self.blocklist_path.parent.mkdir(parents=True, exist_ok=True)
            with open(self.blocklist_path, "w") as f:
                json.dump(self.blocklist, f, indent=2)
        except OSError as e:
            logger.error(f"Could not save blocklist: {e}")

    def block_ip(self, ip: str, reason: str) -> Dict[str, Any]:
        """Add an IP to the blocklist and return firewall commands."""
        entry = {
            "ip": ip,
            "reason": reason,
            "blocked_at": datetime.now().isoformat(),
        }
        self.blocklist[ip] = entry
        self._save_blocklist()

        self.threat_log.append({"action": "block_ip", **entry})

        return {
            "blocked": True,
            "ip": ip,
            "reason": reason,
            "firewall_commands": {
                "linux": f"iptables -I INPUT -s {ip} -j DROP",
                "windows": f'netsh advfirewall firewall add rule name="Block {ip}" dir=in action=block remoteip={ip}',
            },
        }

    def unblock_ip(self, ip: str) -> bool:
        """Remove an IP from the blocklist."""
        if ip in self.blocklist:
            del self.blocklist[ip]
            self._save_blocklist()
            self.threat_log.append({"action": "unblock_ip", "ip": ip, "at": datetime.now().isoformat()})
            return True
        return False

    def analyze_log_file(self, log_path: str, max_lines: int = 10000) -> Dict[str, Any]:
        """Read a log file and detect attack patterns."""
        try:
            with open(log_path, "r", encoding="utf-8", errors="ignore") as f:
                lines = [f.readline() for _ in range(max_lines)]
        except OSError as e:
            return {"error": str(e)}

        ip_requests: Dict[str, int] = {}
        ip_attack_types: Dict[str, set] = {}
        all_findings: List[Dict[str, Any]] = []

        for lineno, line in enumerate(lines, start=1):
            if not line:
                break
            ips = IP_REGEX.findall(line)
            for ip in ips:
                ip_requests[ip] = ip_requests.get(ip, 0) + 1

            for attack_type, pattern in LOG_ATTACK_PATTERNS.items():
                if re.search(pattern, line):
                    all_findings.append({
                        "line": lineno,
                        "type": attack_type,
                        "content": line.strip()[:200],
                    })
                    for ip in ips:
                        if ip not in ip_attack_types:
                            ip_attack_types[ip] = set()
                        ip_attack_types[ip].add(attack_type)

        # Brute force: IPs with > 100 requests
        brute_force_ips = [ip for ip, count in ip_requests.items() if count > 100]
        for ip in brute_force_ips:
            if ip not in ip_attack_types:
                ip_attack_types[ip] = set()
            ip_attack_types[ip].add("brute_force_volume")

        # Recommend blocking IPs with 2+ attack types
        recommend_block = [
            {"ip": ip, "attack_types": list(types), "request_count": ip_requests.get(ip, 0)}
            for ip, types in ip_attack_types.items()
            if len(types) >= 2
        ]

        return {
            "log_path": log_path,
            "lines_analyzed": lineno,
            "total_findings": len(all_findings),
            "findings_by_type": {
                t: sum(1 for f in all_findings if f["type"] == t)
                for t in LOG_ATTACK_PATTERNS
            },
            "unique_ips": len(ip_requests),
            "brute_force_ips": brute_force_ips,
            "recommend_block": recommend_block,
            "sample_findings": all_findings[:10],
        }

    def analyze_text(self, text: str) -> List[Dict[str, Any]]:
        """Scan arbitrary text for attack patterns."""
        findings = []
        for attack_type, pattern in LOG_ATTACK_PATTERNS.items():
            matches = re.findall(pattern, text)
            if matches:
                findings.append({
                    "type": attack_type,
                    "count": len(matches),
                    "sample": matches[0][:100] if matches else "",
                })
        return findings

    def get_hardening_checklist(self) -> List[Dict[str, Any]]:
        """Return the prioritised hardening checklist."""
        return HARDENING_CHECKLIST

    def get_status(self) -> Dict[str, Any]:
        """Return blocked IP count and recent threat log entries."""
        return {
            "blocked_ip_count": len(self.blocklist),
            "blocked_ips": list(self.blocklist.keys()),
            "recent_threats": self.threat_log[-10:],
            "threat_log_total": len(self.threat_log),
        }
