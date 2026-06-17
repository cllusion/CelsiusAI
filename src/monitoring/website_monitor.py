"""
Website Monitor - Uptime, SSL, Security Headers, and Info Leak Detection
Celsius AI - Web-Based Monitoring Module
"""

import asyncio
import re
import ssl
import socket
import logging
from datetime import datetime
from typing import Dict, List, Any, Optional

try:
    import aiohttp
    AIOHTTP_AVAILABLE = True
except ImportError:
    aiohttp = None
    AIOHTTP_AVAILABLE = False

try:
    import requests as _requests
    REQUESTS_AVAILABLE = True
except ImportError:
    _requests = None
    REQUESTS_AVAILABLE = False

logger = logging.getLogger(__name__)

SECURITY_HEADERS = [
    "Strict-Transport-Security",
    "X-Content-Type-Options",
    "X-Frame-Options",
    "Content-Security-Policy",
    "Referrer-Policy",
    "Permissions-Policy",
]

LEAK_PATTERNS = [
    ("stack_trace", r'(?i)(traceback|stack trace|at line \d+|exception in thread|java\.lang\.|at com\.)'),
    ("sql_error", r'(?i)(sql syntax|mysql_fetch|pg_query|ORA-\d+|sqlite3\.OperationalError)'),
    ("server_version", r'(?i)(apache/[\d.]+|nginx/[\d.]+|php/[\d.]+|IIS/[\d.]+)'),
    ("debug_mode", r'(?i)(debug mode|DEBUG=True|APP_DEBUG|werkzeug debugger)'),
    ("api_key_leak", r'(?i)(api[_-]?key|access[_-]?token|secret)["\']?\s*[:=]\s*["\']?[A-Za-z0-9_\-]{16,}'),
]


class WebsiteMonitor:
    """Monitor website health, SSL, security headers, and information leakage."""

    def __init__(self, target_url: str = ""):
        self.target_url = target_url
        self.history: List[Dict[str, Any]] = []

    def check_ssl(self, hostname: str) -> Dict[str, Any]:
        """Check SSL certificate validity and expiry."""
        try:
            context = ssl.create_default_context()
            with socket.create_connection((hostname, 443), timeout=10) as sock:
                with context.wrap_socket(sock, server_hostname=hostname) as ssock:
                    cert = ssock.getpeercert()

            not_after = cert.get("notAfter", "")
            expiry_dt = datetime.strptime(not_after, "%b %d %H:%M:%S %Y %Z")
            days_left = (expiry_dt - datetime.utcnow()).days

            issuer = dict(x[0] for x in cert.get("issuer", []))
            result = {
                "valid": True,
                "hostname": hostname,
                "days_until_expiry": days_left,
                "expires": not_after,
                "issuer": issuer.get("organizationName", str(issuer)),
            }
            if days_left < 30:
                result["warning"] = f"Certificate expires in {days_left} days!"
            return result
        except ssl.SSLError as e:
            return {"valid": False, "hostname": hostname, "error": str(e)}
        except Exception as e:
            return {"valid": False, "hostname": hostname, "error": str(e)}

    def check_security_headers(self, headers: Dict[str, str]) -> Dict[str, Any]:
        """Evaluate security headers and return grade/score."""
        present = []
        missing = []
        warnings = []

        headers_lower = {k.lower(): v for k, v in headers.items()}

        for header in SECURITY_HEADERS:
            if header.lower() in headers_lower:
                present.append(header)
            else:
                missing.append(header)
                warnings.append(f"Missing header: {header}")

        score = int((len(present) / len(SECURITY_HEADERS)) * 100)

        if score >= 90:
            grade = "A"
        elif score >= 70:
            grade = "B"
        elif score >= 50:
            grade = "C"
        else:
            grade = "F"

        return {
            "score": score,
            "grade": grade,
            "present": present,
            "missing": missing,
            "warnings": warnings,
        }

    def scan_response_for_leaks(self, body: str) -> List[Dict[str, Any]]:
        """Scan response body for information leaks."""
        findings = []
        for leak_type, pattern in LEAK_PATTERNS:
            matches = re.findall(pattern, body)
            if matches:
                findings.append({
                    "type": leak_type,
                    "count": len(matches),
                    "sample": matches[0][:100] if matches else "",
                    "severity": "high" if leak_type in ("stack_trace", "sql_error", "api_key_leak") else "medium",
                })
        return findings

    async def full_check(self, url: str = "") -> Dict[str, Any]:
        """Perform a full website security check."""
        target = url or self.target_url
        if not target:
            return {"error": "No URL provided"}

        result: Dict[str, Any] = {
            "url": target,
            "checked_at": datetime.now().isoformat(),
            "risks": [],
            "risk_level": "low",
        }

        start = datetime.now()
        status_code = None
        headers = {}
        body = ""

        try:
            if AIOHTTP_AVAILABLE:
                async with aiohttp.ClientSession() as session:
                    async with session.get(target, timeout=aiohttp.ClientTimeout(total=15), ssl=False) as resp:
                        status_code = resp.status
                        headers = dict(resp.headers)
                        body = await resp.text(errors="ignore")
            elif REQUESTS_AVAILABLE:
                resp = _requests.get(target, timeout=15, verify=False)
                status_code = resp.status_code
                headers = dict(resp.headers)
                body = resp.text
            else:
                result["error"] = "No HTTP library available (aiohttp or requests)"
                return result
        except Exception as e:
            result["error"] = str(e)
            result["risk_level"] = "unknown"
            return result

        elapsed_ms = int((datetime.now() - start).total_seconds() * 1000)

        result["status_code"] = status_code
        result["response_time_ms"] = elapsed_ms

        # Security headers
        header_check = self.check_security_headers(headers)
        result["security_headers"] = header_check
        if header_check["grade"] == "F":
            result["risks"].append({"type": "poor_security_headers", "detail": f"Headers grade: F (score {header_check['score']})"})

        # Info leaks
        leaks = self.scan_response_for_leaks(body)
        result["leaks"] = leaks
        for leak in leaks:
            result["risks"].append({"type": leak["type"], "detail": f"Found {leak['count']} instance(s)", "severity": leak["severity"]})

        # SSL check
        try:
            from urllib.parse import urlparse
            parsed = urlparse(target)
            hostname = parsed.hostname
            if hostname and parsed.scheme == "https":
                ssl_result = self.check_ssl(hostname)
                result["ssl"] = ssl_result
                if not ssl_result.get("valid"):
                    result["risks"].append({"type": "ssl_invalid", "detail": ssl_result.get("error", "Invalid SSL")})
                elif ssl_result.get("warning"):
                    result["risks"].append({"type": "ssl_expiring", "detail": ssl_result["warning"]})
        except Exception as e:
            result["ssl"] = {"error": str(e)}

        # Determine overall risk level
        high_risks = [r for r in result["risks"] if r.get("severity") in ("high", "critical")]
        if high_risks:
            result["risk_level"] = "high"
        elif result["risks"]:
            result["risk_level"] = "medium"
        else:
            result["risk_level"] = "low"

        self.history.append({
            "url": target,
            "status_code": status_code,
            "response_time_ms": elapsed_ms,
            "risk_level": result["risk_level"],
            "checked_at": result["checked_at"],
        })

        return result

    def get_uptime_summary(self) -> Dict[str, Any]:
        """Return a summary of historical checks."""
        if not self.history:
            return {"total_checks": 0, "message": "No checks performed yet"}

        total = len(self.history)
        up = sum(1 for h in self.history if isinstance(h.get("status_code"), int) and h["status_code"] < 400)
        avg_rt = sum(h.get("response_time_ms", 0) for h in self.history) / total

        return {
            "total_checks": total,
            "up_count": up,
            "down_count": total - up,
            "uptime_percent": round((up / total) * 100, 2),
            "avg_response_time_ms": round(avg_rt, 1),
            "last_check": self.history[-1]["checked_at"],
        }
