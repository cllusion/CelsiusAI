"""
Machine Monitor - Local System Security and Resource Monitoring
Celsius AI - Host-Based Monitoring Module
"""

import logging
import socket
from datetime import datetime
from typing import Dict, List, Any

try:
    import psutil
    PSUTIL_AVAILABLE = True
except ImportError:
    psutil = None
    PSUTIL_AVAILABLE = False
    logging.warning("psutil not available. Machine monitoring will be limited.")

logger = logging.getLogger(__name__)

SUSPICIOUS_PORTS = {21, 23, 25, 4444, 5555, 6666, 7777, 8888, 31337, 12345}

SUSPICIOUS_PROCESS_NAMES = {
    "xmrig", "minerd", "cryptonight", "masscan", "zmap",
    "metasploit", "msfconsole", "hydra", "medusa", "john", "hashcat",
}


class MachineMonitor:
    """Monitor local machine resources and detect suspicious activity."""

    def __init__(self):
        self.available = PSUTIL_AVAILABLE

    def get_cpu_stats(self) -> Dict[str, Any]:
        """Return CPU usage statistics."""
        if not PSUTIL_AVAILABLE:
            return {"error": "psutil not available"}
        try:
            freq = psutil.cpu_freq()
            return {
                "percent": psutil.cpu_percent(interval=1),
                "count_logical": psutil.cpu_count(logical=True),
                "count_physical": psutil.cpu_count(logical=False),
                "freq_mhz": freq.current if freq else None,
                "freq_max_mhz": freq.max if freq else None,
            }
        except Exception as e:
            return {"error": str(e)}

    def get_memory_stats(self) -> Dict[str, Any]:
        """Return virtual and swap memory statistics in GB."""
        if not PSUTIL_AVAILABLE:
            return {"error": "psutil not available"}
        try:
            vm = psutil.virtual_memory()
            sw = psutil.swap_memory()
            return {
                "virtual": {
                    "total_gb": round(vm.total / 1e9, 2),
                    "available_gb": round(vm.available / 1e9, 2),
                    "used_gb": round(vm.used / 1e9, 2),
                    "percent": vm.percent,
                },
                "swap": {
                    "total_gb": round(sw.total / 1e9, 2),
                    "used_gb": round(sw.used / 1e9, 2),
                    "percent": sw.percent,
                },
            }
        except Exception as e:
            return {"error": str(e)}

    def get_disk_stats(self) -> List[Dict[str, Any]]:
        """Return disk usage per mount point."""
        if not PSUTIL_AVAILABLE:
            return [{"error": "psutil not available"}]
        results = []
        try:
            for part in psutil.disk_partitions(all=False):
                try:
                    usage = psutil.disk_usage(part.mountpoint)
                    results.append({
                        "device": part.device,
                        "mountpoint": part.mountpoint,
                        "fstype": part.fstype,
                        "total_gb": round(usage.total / 1e9, 2),
                        "used_gb": round(usage.used / 1e9, 2),
                        "free_gb": round(usage.free / 1e9, 2),
                        "percent": usage.percent,
                    })
                except PermissionError:
                    pass
        except Exception as e:
            results.append({"error": str(e)})
        return results

    def get_network_stats(self) -> Dict[str, Any]:
        """Return network I/O counters and connection info."""
        if not PSUTIL_AVAILABLE:
            return {"error": "psutil not available"}
        try:
            io = psutil.net_io_counters()
            connections = []
            suspicious = []
            try:
                for conn in psutil.net_connections(kind="inet"):
                    entry = {
                        "laddr": f"{conn.laddr.ip}:{conn.laddr.port}" if conn.laddr else None,
                        "raddr": f"{conn.raddr.ip}:{conn.raddr.port}" if conn.raddr else None,
                        "status": conn.status,
                        "pid": conn.pid,
                    }
                    connections.append(entry)
                    if conn.raddr and conn.raddr.port in SUSPICIOUS_PORTS:
                        suspicious.append(entry)
            except (psutil.AccessDenied, AttributeError):
                pass

            return {
                "bytes_sent": io.bytes_sent,
                "bytes_recv": io.bytes_recv,
                "packets_sent": io.packets_sent,
                "packets_recv": io.packets_recv,
                "total_connections": len(connections),
                "suspicious_connections": suspicious,
            }
        except Exception as e:
            return {"error": str(e)}

    def get_suspicious_processes(self) -> List[Dict[str, Any]]:
        """Return processes matching known suspicious/malicious names."""
        if not PSUTIL_AVAILABLE:
            return [{"error": "psutil not available"}]
        results = []
        try:
            for proc in psutil.process_iter(["pid", "name", "username", "cmdline", "cpu_percent"]):
                try:
                    name = (proc.info.get("name") or "").lower()
                    if name in SUSPICIOUS_PROCESS_NAMES:
                        results.append({
                            "pid": proc.info["pid"],
                            "name": proc.info["name"],
                            "username": proc.info.get("username"),
                            "cmdline": " ".join(proc.info.get("cmdline") or []),
                            "cpu_percent": proc.info.get("cpu_percent"),
                            "reason": "known suspicious process name",
                        })
                except (psutil.NoSuchProcess, psutil.AccessDenied):
                    pass
        except Exception as e:
            results.append({"error": str(e)})
        return results

    def check_open_ports(self) -> List[Dict[str, Any]]:
        """Return all listening connections with a suspicious flag."""
        if not PSUTIL_AVAILABLE:
            return [{"error": "psutil not available"}]
        results = []
        try:
            for conn in psutil.net_connections(kind="inet"):
                if conn.status == "LISTEN" and conn.laddr:
                    port = conn.laddr.port
                    results.append({
                        "ip": conn.laddr.ip,
                        "port": port,
                        "pid": conn.pid,
                        "suspicious": port in SUSPICIOUS_PORTS,
                    })
        except (psutil.AccessDenied, AttributeError) as e:
            results.append({"error": str(e)})
        return results

    def check_system_security(self) -> Dict[str, Any]:
        """Comprehensive security check returning alerts and overall status."""
        alerts = []

        cpu = self.get_cpu_stats()
        mem = self.get_memory_stats()
        disks = self.get_disk_stats()
        procs = self.get_suspicious_processes()
        ports = self.check_open_ports()

        if isinstance(cpu, dict) and cpu.get("percent", 0) > 90:
            alerts.append({"type": "high_cpu", "message": f"CPU usage critical: {cpu['percent']}%", "severity": "warning"})

        if isinstance(mem, dict) and "virtual" in mem:
            if mem["virtual"].get("percent", 0) > 90:
                alerts.append({"type": "high_memory", "message": f"RAM usage critical: {mem['virtual']['percent']}%", "severity": "warning"})

        for disk in disks:
            if isinstance(disk, dict) and disk.get("percent", 0) > 90:
                alerts.append({"type": "full_disk", "message": f"Disk {disk.get('mountpoint')} at {disk['percent']}%", "severity": "warning"})

        for proc in procs:
            if "error" not in proc:
                alerts.append({"type": "suspicious_process", "message": f"Suspicious process: {proc['name']} (PID {proc['pid']})", "severity": "critical"})

        suspicious_listeners = [p for p in ports if isinstance(p, dict) and p.get("suspicious")]
        for port_entry in suspicious_listeners:
            alerts.append({"type": "suspicious_port", "message": f"Suspicious listener on port {port_entry['port']}", "severity": "critical"})

        critical_count = sum(1 for a in alerts if a.get("severity") == "critical")
        warning_count = sum(1 for a in alerts if a.get("severity") == "warning")

        if critical_count > 0:
            status = "critical"
        elif warning_count > 0:
            status = "warning"
        else:
            status = "clean"

        return {
            "status": status,
            "alerts": alerts,
            "alert_count": len(alerts),
            "cpu": cpu,
            "memory": mem,
            "disks": disks,
            "suspicious_processes": procs,
            "suspicious_ports": suspicious_listeners,
            "checked_at": datetime.now().isoformat(),
        }

    def get_full_status(self) -> Dict[str, Any]:
        """Combine all stats into a single status report."""
        return {
            "cpu": self.get_cpu_stats(),
            "memory": self.get_memory_stats(),
            "disks": self.get_disk_stats(),
            "network": self.get_network_stats(),
            "suspicious_processes": self.get_suspicious_processes(),
            "open_ports": self.check_open_ports(),
            "timestamp": datetime.now().isoformat(),
        }
