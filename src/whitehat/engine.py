"""
White Hat Hacking Engine - Advanced Ethical Penetration Testing
Celsius AI - Continuous Learning Security Testing Framework

This module provides the core engine for conducting ethical hacking engagements.
It features a dynamic technique library, asynchronous execution of security tests,
and a learning mechanism to improve effectiveness over time.
"""

import asyncio
import logging
import json
import hashlib
import ssl
import uuid
import base64
import re
import ipaddress
import socket
from datetime import datetime
from typing import Dict, List, Optional, Any, Set, Tuple, Coroutine
from pathlib import Path
from urllib.parse import urlparse, urljoin

import aiohttp
import aiodns
import aiofiles
from bs4 import BeautifulSoup

from src.whitehat.authorization import WhiteHatAuthorizationManager

# Configure logging
logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(name)s - %(levelname)s - %(message)s")
logger = logging.getLogger(__name__)


class TechniqueLibrary:
    """
    A dynamic and evolving library of ethical hacking techniques.

    This class manages a collection of penetration testing techniques, tracks their
    success rates, and learns from the results to improve future recommendations.
    Techniques are organized by category and risk level, allowing for controlled
    and authorized execution.
    """

    def __init__(self, techniques_file: Path = Path("learned_techniques.json")):
        """
        Initializes the TechniqueLibrary.

        Args:
            techniques_file: Path to the file for persisting learned techniques.
        """
        self.techniques: Dict[str, Dict[str, Any]] = {}
        self.success_rates: Dict[str, Dict[str, int]] = {}
        self.learned_patterns: Dict[str, List[Dict[str, Any]]] = {}
        self.techniques_file = techniques_file
        self._lock = asyncio.Lock()
        self.load_base_techniques()

    def load_base_techniques(self) -> None:
        """Loads a foundational set of penetration testing techniques."""
        self.techniques = {
            # Reconnaissance
            "passive_dns_enumeration": self._create_technique(
                "reconnaissance", "Passive DNS enumeration", self._passive_dns_enum, "low", "high", 0.8
            ),
            "subdomain_enumeration": self._create_technique(
                "reconnaissance", "Discover subdomains", self._subdomain_enum, "low", "high", 0.7
            ),
            # Network Scanning
            "port_scanning": self._create_technique(
                "network_scanning", "TCP/UDP port scanning", self._port_scan, "low", "medium", 0.9
            ),
            "service_enumeration": self._create_technique(
                "network_scanning", "Enumerate services and versions", self._service_enum, "low", "medium", 0.8
            ),
            # Vulnerability Assessment
            "ssl_tls_testing": self._create_technique(
                "vulnerability_assessment", "Test SSL/TLS configuration", self._ssl_test, "low", "high", 0.9
            ),
            # Web Application Testing
            "web_crawler": self._create_technique(
                "web_application_testing", "Intelligent web application crawling", self._web_crawl, "low", "high", 0.8
            ),
            "sql_injection_detection": self._create_technique(
                "web_application_testing",
                "Detect SQL injection vulnerabilities",
                self._sql_injection_test,
                "medium",
                "medium",
                0.7,
            ),
            "xss_detection": self._create_technique(
                "web_application_testing", "Cross-site scripting detection", self._xss_test, "medium", "medium", 0.6
            ),
            # Exploitation & Social Engineering
            "password_attack": self._create_technique(
                "network_exploitation", "Simulated password attacks", self._password_attack, "high", "low", 0.5
            ),
            "phishing_simulation": self._create_technique(
                "social_engineering", "Controlled phishing awareness testing", self._phishing_sim, "medium", "high", 0.8
            ),
        }

    @staticmethod
    def _create_technique(
        category: str,
        description: str,
        implementation: Coroutine,
        risk_level: str,
        stealth_level: str,
        effectiveness: float,
    ) -> Dict[str, Any]:
        """Helper to create a technique dictionary."""
        return {
            "category": category,
            "description": description,
            "implementation": implementation,
            "risk_level": risk_level,
            "stealth_level": stealth_level,
            "effectiveness": effectiveness,
        }

    async def _passive_dns_enum(
        self, target: str, params: Dict[str, Any], session: aiohttp.ClientSession
    ) -> Dict[str, Any]:
        """Asynchronously performs passive DNS enumeration."""
        resolver = aiodns.DNSResolver()
        results: Dict[str, Any] = {
            "records": {},
            "subdomains": set(),
            "ip_addresses": set(),
        }
        record_types = ["A", "AAAA", "MX", "NS", "TXT", "SOA", "CNAME"]

        async def query(record_type: str):
            try:
                answers = await resolver.query(target, record_type)
                results["records"][record_type] = [str(r.host) if hasattr(r, "host") else str(r.text) for r in answers]
                if record_type in ["A", "AAAA"]:
                    results["ip_addresses"].update(results["records"][record_type])
            except aiodns.error.DNSError:
                results["records"][record_type] = []

        await asyncio.gather(*(query(rt) for rt in record_types))
        results["ip_addresses"] = list(results["ip_addresses"])
        return results

    async def _subdomain_enum(
        self, target: str, params: Dict[str, Any], session: aiohttp.ClientSession
    ) -> Dict[str, Any]:
        """Asynchronously enumerates subdomains."""
        resolver = aiodns.DNSResolver()
        results: Dict[str, Any] = {"subdomains": [], "methods_used": ["dictionary_enumeration"]}

        common_subdomains = params.get(
            "wordlist", ["www", "mail", "ftp", "admin", "test", "dev", "staging", "api", "app", "portal"]
        )

        async def check_subdomain(sub: str):
            full_domain = f"{sub}.{target}"
            try:
                answers = await resolver.query(full_domain, "A")
                if answers:
                    results["subdomains"].append(
                        {"subdomain": full_domain, "ip": [str(a.host) for a in answers], "method": "dictionary"}
                    )
            except aiodns.error.DNSError:
                pass

        await asyncio.gather(*(check_subdomain(s) for s in common_subdomains))
        results["total_found"] = len(results["subdomains"])
        return results

    async def _port_scan(self, target: str, params: Dict[str, Any], session: aiohttp.ClientSession) -> Dict[str, Any]:
        """Asynchronously scans for open TCP ports."""
        results: Dict[str, Any] = {"open_ports": [], "scan_type": "tcp_connect"}
        common_ports = params.get("ports", [21, 22, 25, 53, 80, 443, 3306, 3389, 5432, 8080])
        timeout = params.get("timeout", 1.0)

        async def scan_port(port: int):
            try:
                _, writer = await asyncio.wait_for(asyncio.open_connection(target, port), timeout=timeout)
                writer.close()
                await writer.wait_closed()
                results["open_ports"].append({"port": port, "state": "open", "protocol": "tcp"})
            except (asyncio.TimeoutError, ConnectionRefusedError, OSError):
                pass

        await asyncio.gather(*(scan_port(p) for p in common_ports))
        return results

    async def _service_enum(
        self, target: str, params: Dict[str, Any], session: aiohttp.ClientSession
    ) -> Dict[str, Any]:
        """Asynchronously enumerates services on open ports."""
        results: Dict[str, Any] = {"services": []}
        port_scan_result = await self._port_scan(target, params, session)

        async def grab_banner(port: int):
            service_info = {"port": port, "banner": "", "service": "unknown"}
            try:
                reader, writer = await asyncio.wait_for(asyncio.open_connection(target, port), timeout=3.0)
                writer.write(b"\r\n")
                await writer.drain()
                banner_bytes = await asyncio.wait_for(reader.read(1024), timeout=3.0)
                banner = banner_bytes.decode("utf-8", errors="ignore").strip()
                service_info["banner"] = banner
                service_info["service"] = self._identify_service(port, banner)
                writer.close()
                await writer.wait_closed()
            except (asyncio.TimeoutError, ConnectionRefusedError, OSError) as e:
                logger.debug(f"Could not grab banner from {target}:{port}: {e}")
                service_info["service"] = self._identify_service(port, "")
            finally:
                results["services"].append(service_info)

        if "open_ports" in port_scan_result:
            await asyncio.gather(*(grab_banner(p["port"]) for p in port_scan_result["open_ports"]))
        return results

    def _identify_service(self, port: int, banner: str) -> str:
        """Identifies a service from its port and banner."""
        common_services = {
            21: "FTP",
            22: "SSH",
            23: "Telnet",
            25: "SMTP",
            53: "DNS",
            80: "HTTP",
            110: "POP3",
            143: "IMAP",
            443: "HTTPS",
            993: "IMAPS",
            995: "POP3S",
            3306: "MySQL",
            3389: "RDP",
            5432: "PostgreSQL",
        }

        service = common_services.get(port, "Unknown")

        # Banner-based identification
        if banner:
            banner_lower = banner.lower()
            if "ssh" in banner_lower:
                service = "SSH"
            elif "ftp" in banner_lower:
                service = "FTP"
            elif "http" in banner_lower:
                service = "HTTP"
            elif "smtp" in banner_lower:
                service = "SMTP"

        return service

    async def _ssl_test(self, target: str, params: Dict[str, Any], session: aiohttp.ClientSession) -> Dict[str, Any]:
        """Asynchronously tests SSL/TLS configuration."""
        try:
            results = {
                "target": target,
                "technique": "ssl_tls_testing",
                "timestamp": datetime.now().isoformat(),
                "ssl_info": {},
                "vulnerabilities": [],
            }

            port = params.get("port", 443)

            # Get SSL certificate info
            try:
                context = ssl.create_default_context()
                context.check_hostname = False
                context.verify_mode = ssl.CERT_NONE

                with socket.create_connection((target, port), timeout=10) as sock:
                    with context.wrap_socket(sock, server_hostname=target) as ssock:
                        cert = ssock.getpeercert()
                        cipher = ssock.cipher()

                        results["ssl_info"] = {
                            "version": ssock.version(),
                            "cipher": cipher,
                            "certificate": {
                                "subject": dict(x[0] for x in cert.get("subject", [])),
                                "issuer": dict(x[0] for x in cert.get("issuer", [])),
                                "not_before": cert.get("notBefore"),
                                "not_after": cert.get("notAfter"),
                                "serial_number": cert.get("serialNumber"),
                            },
                        }

                        # Check for weak ciphers
                        if cipher and cipher[1] in ["RC4", "DES", "3DES"]:
                            results["vulnerabilities"].append(
                                {"type": "weak_cipher", "details": f"Weak cipher detected: {cipher[1]}"}
                            )

                        # Check certificate expiry
                        if cert and "notAfter" in cert:
                            try:
                                expiry = datetime.strptime(cert["notAfter"], "%b %d %H:%M:%S %Y %Z")
                                days_until_expiry = (expiry - datetime.now()).days

                                if days_until_expiry < 30:
                                    results["vulnerabilities"].append(
                                        {
                                            "type": "certificate_expiry",
                                            "details": f"Certificate expires in {days_until_expiry} days",
                                        }
                                    )
                            except Exception:
                                pass

            except Exception as e:
                results["ssl_info"] = {"error": str(e)}

            return results

        except Exception as e:
            logger.error(f"SSL testing failed: {e}")
            return {"error": str(e)}

    async def _web_crawl(self, target: str, params: Dict[str, Any], session: aiohttp.ClientSession) -> Dict[str, Any]:
        """Asynchronously crawls a web application."""
        base_url = target if target.startswith("http") else f"http://{target}"
        max_depth = params.get("max_depth", 2)
        results: Dict[str, Any] = {"urls_found": [], "forms_found": [], "interesting_files": []}
        visited = set()
        to_visit = asyncio.Queue()
        to_visit.put_nowait((base_url, 0))

        async def worker():
            while not to_visit.empty():
                url, depth = await to_visit.get()
                if url in visited or depth > max_depth:
                    to_visit.task_done()
                    continue

                visited.add(url)
                try:
                    async with session.get(url, timeout=10, allow_redirects=True) as response:
                        if response.status == 200 and "text/html" in response.content_type:
                            html = await response.text()
                            soup = BeautifulSoup(html, "html.parser")

                            results["urls_found"].append(
                                {
                                    "url": url,
                                    "status": response.status,
                                    "title": soup.title.string if soup.title else "",
                                }
                            )

                            # Find forms
                            results["forms_found"].extend([str(f) for f in soup.find_all("form")])

                            # Find links
                            if depth < max_depth:
                                for link in soup.find_all("a", href=True):
                                    abs_link = urljoin(url, link["href"])
                                    if (
                                        urlparse(abs_link).netloc == urlparse(base_url).netloc
                                        and abs_link not in visited
                                    ):
                                        await to_visit.put((abs_link, depth + 1))
                except (aiohttp.ClientError, asyncio.TimeoutError) as e:
                    logger.warning(f"Failed to crawl {url}: {e}")
                finally:
                    to_visit.task_done()

        workers = [asyncio.create_task(worker()) for _ in range(params.get("concurrency", 4))]
        await to_visit.join()
        for w in workers:
            w.cancel()
        await asyncio.gather(*workers, return_exceptions=True)

        return results

    async def _sql_injection_test(
        self, target: str, params: Dict[str, Any], session: aiohttp.ClientSession
    ) -> Dict[str, Any]:
        """Asynchronously tests for basic SQL injection vulnerabilities."""
        # ... (implementation needs careful async adaptation)
        return {"status": "SQLi test not fully implemented in async."}

    async def _xss_test(self, target: str, params: Dict[str, Any], session: aiohttp.ClientSession) -> Dict[str, Any]:
        """Asynchronously tests for basic XSS vulnerabilities."""
        # ... (implementation needs careful async adaptation)
        return {"status": "XSS test not fully implemented in async."}

    async def _password_attack(
        self, target: str, params: Dict[str, Any], session: aiohttp.ClientSession
    ) -> Dict[str, Any]:
        """Simulates a password attack (demonstration only)."""
        logger.warning("Password attack is a simulation and does not perform real attacks.")
        return {
            "note": "This is a demonstration - no actual authentication attempts were made.",
            "attempts": [{"user": "admin", "pass": "password", "result": "simulated_failure"}],
        }

    async def _phishing_sim(
        self, target: str, params: Dict[str, Any], session: aiohttp.ClientSession
    ) -> Dict[str, Any]:
        """Plans a phishing simulation (demonstration only)."""
        return {
            "simulation_details": {
                "type": "awareness_training",
                "target_group": target,
                "status": "planned",
                "note": "Phishing simulations require careful planning and consent.",
            }
        }

    async def learn_from_result(self, technique: str, result: Dict[str, Any], success: bool):
        """Updates technique effectiveness based on execution results."""
        async with self._lock:
            if technique not in self.success_rates:
                self.success_rates[technique] = {"successes": 0, "total": 0}

            self.success_rates[technique]["total"] += 1
            if success:
                self.success_rates[technique]["successes"] += 1

            rate = self.success_rates[technique]["successes"] / self.success_rates[technique]["total"]
            if technique in self.techniques:
                self.techniques[technique]["effectiveness"] = round(rate, 2)

            # Persist learning
            await self.save_learning_data()

    async def save_learning_data(self):
        """Saves success rates and learned patterns to a file."""
        try:
            async with aiofiles.open(self.techniques_file, "w") as f:
                await f.write(
                    json.dumps(
                        {"success_rates": self.success_rates, "learned_patterns": self.learned_patterns}, indent=4
                    )
                )
        except IOError as e:
            logger.error(f"Failed to save learning data: {e}")

    async def load_learning_data(self):
        """Loads learned data from a file."""
        if not self.techniques_file.exists():
            return
        try:
            async with aiofiles.open(self.techniques_file, "r") as f:
                content = await f.read()
                data = json.loads(content)
                self.success_rates = data.get("success_rates", {})
                self.learned_patterns = data.get("learned_patterns", {})
                # Update effectiveness from loaded data
                for tech, rates in self.success_rates.items():
                    if tech in self.techniques and rates["total"] > 0:
                        self.techniques[tech]["effectiveness"] = round(rates["successes"] / rates["total"], 2)
        except (IOError, json.JSONDecodeError) as e:
            logger.error(f"Failed to load learning data: {e}")


# ---------------------------------------------------------------------------
# Service-name lookup used by port_scan
# ---------------------------------------------------------------------------
_SERVICE_NAMES: Dict[int, str] = {
    21: "FTP", 22: "SSH", 23: "Telnet", 25: "SMTP", 53: "DNS",
    80: "HTTP", 443: "HTTPS", 3306: "MySQL", 5432: "PostgreSQL",
    6379: "Redis", 8080: "HTTP-Alt", 8443: "HTTPS-Alt",
    8888: "Jupyter/Alt-HTTP", 27017: "MongoDB",
}


class WhiteHatEngine:
    """
    The main asynchronous engine for orchestrating white hat hacking engagements.

    This class integrates authorization, technique execution, and learning to
    provide a comprehensive and intelligent security testing framework.
    """

    def __init__(self, config: Dict[str, Any]):
        """
        Initializes the WhiteHatEngine.

        Args:
            config: A dictionary containing configuration for the engine.
        """
        self.config = config
        self.auth_manager = WhiteHatAuthorizationManager()
        self.technique_library = TechniqueLibrary()
        self.active_engagements: Dict[str, Dict[str, Any]] = {}
        self._session: Optional[aiohttp.ClientSession] = None

    async def initialize(self) -> None:
        """Initializes the engine, creating an HTTP session and loading data."""
        logger.info("Initializing White Hat Hacking Engine...")
        self._session = aiohttp.ClientSession(headers={"User-Agent": "CelsiusAI-WhiteHat-Engine/1.0"})
        await self.technique_library.load_learning_data()
        logger.info("White Hat Engine initialized successfully.")

    async def close(self) -> None:
        """Closes the engine's resources, such as the HTTP session."""
        if self._session:
            await self._session.close()
        logger.info("White Hat Engine shut down.")

    async def execute_technique(
        self, technique: str, target: str, params: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """
        Executes a single, authorized penetration testing technique.

        Args:
            technique: The name of the technique to execute.
            target: The target host or URL.
            params: Additional parameters for the technique.

        Returns:
            A dictionary containing the results of the execution.
        """
        if not self.auth_manager.is_authorized(technique, target):
            return {"error": "Technique not authorized", "authorization_required": True}

        tech_info = self.technique_library.techniques.get(technique)
        if not tech_info:
            return {"error": "Unknown technique"}

        logger.info(f"Executing authorized technique: {technique} on {target}")
        params = params or {}

        try:
            if not self._session:
                raise RuntimeError("Engine not initialized. Call initialize() first.")

            result = await tech_info["implementation"](target, params, self._session)

            # Simplified success metric
            success = "error" not in result and bool(result)

            await self.technique_library.learn_from_result(technique, result, success)
            self.auth_manager.log_activity(technique, target, "success" if success else "failed", result)

            return result
        except Exception as e:
            logger.error(f"Technique execution failed for {technique} on {target}: {e}", exc_info=True)
            return {"error": str(e)}

    async def run_engagement(self, target: str, engagement_type: str = "comprehensive") -> Dict[str, Any]:
        """
        Runs a full, multi-phase penetration testing engagement.

        Args:
            target: The primary target for the engagement.
            engagement_type: The type of engagement (e.g., 'comprehensive', 'recon').

        Returns:
            A dictionary summarizing the entire engagement.
        """
        engagement_id = str(uuid.uuid4())
        engagement: Dict[str, Any] = {
            "id": engagement_id,
            "target": target,
            "type": engagement_type,
            "start_time": datetime.now().isoformat(),
            "phases": [],
            "findings": [],
        }
        self.active_engagements[engagement_id] = engagement
        logger.info(f"Starting engagement {engagement_id} against {target}")

        # Define phases and associated techniques
        phases = {
            "reconnaissance": ["passive_dns_enumeration", "subdomain_enumeration"],
            "scanning": ["port_scanning", "service_enumeration"],
            "vulnerability_assessment": ["ssl_tls_testing"],
            "web_testing": ["web_crawler", "sql_injection_detection", "xss_detection"],
        }

        for phase, techniques in phases.items():
            if engagement_type != "comprehensive" and phase not in ["reconnaissance", engagement_type]:
                continue

            phase_results = await self._run_phase(target, phase, techniques)
            engagement["phases"].append(phase_results)

        engagement["findings"] = self._generate_findings(engagement)
        engagement["end_time"] = datetime.now().isoformat()

        logger.info(f"Engagement {engagement_id} completed.")
        return engagement

    async def _run_phase(self, target: str, phase_name: str, techniques: List[str]) -> Dict[str, Any]:
        """Executes all techniques for a given engagement phase."""
        logger.info(f"Running {phase_name} phase...")
        results = []
        for technique in techniques:
            result = await self.execute_technique(technique, target)
            results.append({"technique": technique, "result": result})

        return {"phase": phase_name, "results": results, "completed_at": datetime.now().isoformat()}

    def _generate_findings(self, engagement: Dict[str, Any]) -> List[Dict[str, Any]]:
        """Generates a list of security findings from engagement results."""
        # This is a placeholder for a more sophisticated analysis engine
        findings = []
        for phase in engagement.get("phases", []):
            for res in phase.get("results", []):
                if res.get("result", {}).get("open_ports"):
                    findings.append(
                        {
                            "title": "Open Ports Discovered",
                            "severity": "informational",
                            "description": f"Found open ports: {res['result']['open_ports']}",
                        }
                    )
        return findings

    # -----------------------------------------------------------------------
    # New capabilities added below — all existing methods above are unchanged
    # -----------------------------------------------------------------------

    async def port_scan(self, target: str, ports: Optional[List[int]] = None) -> Dict[str, Any]:
        """TCP connect scan on the given target using asyncio with 1s timeout per port."""
        if ports is None:
            ports = [21, 22, 23, 25, 53, 80, 443, 3306, 5432, 6379, 8080, 8443, 8888, 27017]

        open_ports: List[Dict[str, Any]] = []

        async def probe(port: int):
            try:
                _, writer = await asyncio.wait_for(
                    asyncio.open_connection(target, port), timeout=1.0
                )
                writer.close()
                try:
                    await writer.wait_closed()
                except Exception:
                    pass
                service = _SERVICE_NAMES.get(port, "unknown")
                open_ports.append({"port": port, "state": "open", "service": service})
            except (asyncio.TimeoutError, ConnectionRefusedError, OSError):
                pass

        await asyncio.gather(*(probe(p) for p in ports))
        open_ports.sort(key=lambda x: x["port"])
        return {
            "target": target,
            "scanned_ports": len(ports),
            "open_ports": open_ports,
            "timestamp": datetime.now().isoformat(),
        }

    async def grab_banner(self, host: str, port: int) -> str:
        """Attempt to read a service banner from host:port."""
        try:
            reader, writer = await asyncio.wait_for(
                asyncio.open_connection(host, port), timeout=3.0
            )
            writer.write(b"\r\n")
            await writer.drain()
            data = await asyncio.wait_for(reader.read(1024), timeout=3.0)
            writer.close()
            try:
                await writer.wait_closed()
            except Exception:
                pass
            return data.decode("utf-8", errors="ignore").strip()
        except Exception:
            return ""

    def check_ssl_security(self, hostname: str) -> Dict[str, Any]:
        """Check SSL protocol version, cipher suite, and certificate validity."""
        result: Dict[str, Any] = {"hostname": hostname, "issues": []}
        try:
            context = ssl.create_default_context()
            context.check_hostname = False
            context.verify_mode = ssl.CERT_NONE

            with socket.create_connection((hostname, 443), timeout=10) as sock:
                with context.wrap_socket(sock, server_hostname=hostname) as ssock:
                    version = ssock.version()
                    cipher = ssock.cipher()
                    cert = ssock.getpeercert()

            result["protocol_version"] = version
            result["cipher_suite"] = cipher

            # Flag TLS < 1.2
            if version in ("SSLv2", "SSLv3", "TLSv1", "TLSv1.1"):
                result["issues"].append({"type": "weak_tls", "detail": f"Protocol {version} is insecure (require TLS 1.2+)"})

            if cipher and cipher[1] in ("RC4", "DES", "3DES", "NULL"):
                result["issues"].append({"type": "weak_cipher", "detail": f"Weak cipher: {cipher[1]}"})

            if cert:
                not_after = cert.get("notAfter", "")
                if not_after:
                    try:
                        expiry = datetime.strptime(not_after, "%b %d %H:%M:%S %Y %Z")
                        days_left = (expiry - datetime.utcnow()).days
                        result["days_until_expiry"] = days_left
                        if days_left < 30:
                            result["issues"].append({"type": "cert_expiring", "detail": f"Cert expires in {days_left} days"})
                    except Exception:
                        pass

            result["secure"] = len(result["issues"]) == 0
        except Exception as e:
            result["error"] = str(e)
            result["secure"] = False
        return result

    async def check_http_security(self, url: str) -> Dict[str, Any]:
        """GET the URL and evaluate security headers, server disclosure, and admin path exposure."""
        result: Dict[str, Any] = {"url": url, "issues": []}
        security_headers = [
            "Strict-Transport-Security",
            "X-Content-Type-Options",
            "X-Frame-Options",
            "Content-Security-Policy",
            "Referrer-Policy",
        ]
        admin_paths = ["/admin", "/wp-admin", "/.env", "/config.json"]

        try:
            async with aiohttp.ClientSession() as session:
                async with session.get(url, timeout=aiohttp.ClientTimeout(total=10), ssl=False) as resp:
                    headers = dict(resp.headers)
                    result["status_code"] = resp.status

            # Missing security headers
            missing = [h for h in security_headers if h not in headers]
            if missing:
                result["issues"].append({"type": "missing_headers", "headers": missing})

            # Server version disclosure
            server = headers.get("Server", "")
            if re.search(r"[\d.]{3,}", server):
                result["issues"].append({"type": "server_version_disclosure", "detail": server})

            result["headers"] = headers

            # Admin path exposure
            exposed = []
            base = url.rstrip("/")
            async with aiohttp.ClientSession() as session:
                for path in admin_paths:
                    try:
                        async with session.get(base + path, timeout=aiohttp.ClientTimeout(total=5), ssl=False, allow_redirects=False) as r:
                            if r.status == 200:
                                exposed.append({"path": path, "status": r.status})
                    except Exception:
                        pass
            if exposed:
                result["issues"].append({"type": "admin_paths_exposed", "paths": exposed})

        except Exception as e:
            result["error"] = str(e)

        result["secure"] = len(result.get("issues", [])) == 0
        return result

    async def run_owasp_top10_check(self, url: str) -> Dict[str, Any]:
        """Basic OWASP Top 10 checks: A01 broken access control, A05 misconfiguration, A06 outdated components, A07 auth failures."""
        result: Dict[str, Any] = {"url": url, "checks": [], "timestamp": datetime.now().isoformat()}

        async with aiohttp.ClientSession() as session:
            # A01 - Broken Access Control: /admin and /api/users without auth
            a01_exposed = []
            for path in ["/admin", "/api/users"]:
                try:
                    async with session.get(url.rstrip("/") + path, timeout=aiohttp.ClientTimeout(total=5), ssl=False, allow_redirects=False) as r:
                        if r.status == 200:
                            a01_exposed.append({"path": path, "status": r.status})
                except Exception:
                    pass
            result["checks"].append({
                "id": "A01",
                "name": "Broken Access Control",
                "status": "fail" if a01_exposed else "pass",
                "detail": a01_exposed or "No unauthenticated admin endpoints found",
            })

            # A05 - Security Misconfiguration: server header, debug info
            try:
                async with session.get(url, timeout=aiohttp.ClientTimeout(total=10), ssl=False) as resp:
                    headers = dict(resp.headers)
                    body_snippet = (await resp.text(errors="ignore"))[:2000]

                a05_issues = []
                if re.search(r"[\d.]{3,}", headers.get("Server", "")):
                    a05_issues.append(f"Server version disclosed: {headers['Server']}")
                if re.search(r"(?i)(debug mode|DEBUG=True|werkzeug debugger)", body_snippet):
                    a05_issues.append("Debug mode indicator found in response")

                result["checks"].append({
                    "id": "A05",
                    "name": "Security Misconfiguration",
                    "status": "fail" if a05_issues else "pass",
                    "detail": a05_issues or "No obvious misconfiguration",
                })

                # A06 - Outdated Components: check Server header version
                server_header = headers.get("Server", "")
                a06_issues = []
                version_match = re.search(r"([\d]+)\.([\d]+)", server_header)
                if version_match:
                    a06_issues.append(f"Server header reveals version: {server_header} (verify it is current)")
                result["checks"].append({
                    "id": "A06",
                    "name": "Vulnerable and Outdated Components",
                    "status": "warn" if a06_issues else "pass",
                    "detail": a06_issues or "No obvious outdated component signals",
                })

            except Exception as e:
                for check_id, name in [("A05", "Security Misconfiguration"), ("A06", "Vulnerable and Outdated Components")]:
                    result["checks"].append({"id": check_id, "name": name, "status": "error", "detail": str(e)})

            # A07 - Identification and Authentication Failures: /admin returns 200 without auth
            a07_issues = []
            try:
                async with session.get(url.rstrip("/") + "/admin", timeout=aiohttp.ClientTimeout(total=5), ssl=False, allow_redirects=False) as r:
                    if r.status == 200:
                        a07_issues.append("/admin accessible without authentication (HTTP 200)")
            except Exception:
                pass
            result["checks"].append({
                "id": "A07",
                "name": "Identification and Authentication Failures",
                "status": "fail" if a07_issues else "pass",
                "detail": a07_issues or "No unauthenticated admin access detected",
            })

        fail_count = sum(1 for c in result["checks"] if c["status"] == "fail")
        result["summary"] = {
            "total_checks": len(result["checks"]),
            "failed": fail_count,
            "passed": sum(1 for c in result["checks"] if c["status"] == "pass"),
            "risk_level": "high" if fail_count >= 2 else ("medium" if fail_count == 1 else "low"),
        }
        return result


async def main():
    """Main function to demonstrate WhiteHatEngine usage."""
    config = {}  # Add any necessary config
    engine = WhiteHatEngine(config)

    try:
        await engine.initialize()

        # Example: Request authorization (in a real scenario, this would be interactive)
        # For demo, we assume authorization is granted for specific tests.
        engine.auth_manager.grant_authorization(
            request_id="demo-request",
            authorized_techniques=["passive_dns_enumeration", "port_scanning"],
            target_scope="example.com",
            duration_hours=1,
        )

        # Execute a single technique
        target_host = "example.com"
        print(f"--- Executing single technique on {target_host} ---")
        dns_results = await engine.execute_technique("passive_dns_enumeration", target_host)
        print(json.dumps(dns_results, indent=2))

        # Run a full engagement
        print(f"\n--- Running comprehensive engagement on {target_host} ---")
        engagement_results = await engine.run_engagement(target_host, "comprehensive")
        print(json.dumps(engagement_results, indent=2, default=str))

    except Exception as e:
        logger.error(f"An error occurred during engine execution: {e}", exc_info=True)
    finally:
        await engine.close()


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("Shutting down.")
