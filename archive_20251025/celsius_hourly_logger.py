#!/usr/bin/env python3
"""
Celsius AI Comprehensive Logging System
Generates detailed hourly reports of system activities, performance, and status
"""

import json
import sqlite3
import subprocess
import psutil
import requests
from datetime import datetime, timedelta
from pathlib import Path
import threading
import time
import os


class CelsiusLogger:
    """Comprehensive logging system for Celsius AI"""

    def __init__(self):
        self.base_dir = Path("C:/Users/micro/Celsius AI")
        self.db_path = self.base_dir / "celsius_activity.db"
        self.logs_dir = self.base_dir / "logs"
        self.logs_dir.mkdir(exist_ok=True)

        self.running = True
        self.last_log_time = datetime.now()

        # Initialize database
        self.init_database()

    def init_database(self):
        """Initialize logging database tables"""
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()

            # Hourly system reports
            cursor.execute(
                """
                CREATE TABLE IF NOT EXISTS hourly_reports (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    timestamp TEXT NOT NULL,
                    system_status TEXT NOT NULL,
                    performance_metrics TEXT NOT NULL,
                    security_status TEXT NOT NULL,
                    network_status TEXT NOT NULL,
                    process_status TEXT NOT NULL,
                    error_summary TEXT,
                    recommendations TEXT
                )
            """
            )

            # Performance metrics
            cursor.execute(
                """
                CREATE TABLE IF NOT EXISTS performance_metrics (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    timestamp TEXT NOT NULL,
                    cpu_percent REAL,
                    memory_percent REAL,
                    disk_usage REAL,
                    network_sent INTEGER,
                    network_recv INTEGER,
                    active_connections INTEGER,
                    response_time REAL
                )
            """
            )

            conn.commit()
            conn.close()
        except Exception as e:
            print(f"Database initialization error: {e}")

    def log_performance_metrics(self):
        """Log current system performance metrics"""
        try:
            # CPU and Memory
            cpu_percent = psutil.cpu_percent(interval=1)
            memory = psutil.virtual_memory()
            disk = psutil.disk_usage("C:")

            # Network
            net_io = psutil.net_io_counters()

            # Network connections
            connections = len(psutil.net_connections())

            # Test response time to local service
            response_time = self.test_response_time()

            # Store metrics
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()

            cursor.execute(
                """
                INSERT INTO performance_metrics 
                (timestamp, cpu_percent, memory_percent, disk_usage, 
                 network_sent, network_recv, active_connections, response_time)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            """,
                (
                    datetime.now().isoformat(),
                    cpu_percent,
                    memory.percent,
                    (disk.used / disk.total) * 100,
                    net_io.bytes_sent,
                    net_io.bytes_recv,
                    connections,
                    response_time,
                ),
            )

            conn.commit()
            conn.close()

        except Exception as e:
            print(f"Performance logging error: {e}")

    def test_response_time(self):
        """Test response time to local Celsius AI service"""
        try:
            start_time = time.time()
            response = requests.get("http://localhost:5000/api/status", timeout=5)
            end_time = time.time()

            if response.status_code == 200:
                return (end_time - start_time) * 1000  # Convert to ms
            else:
                return -1  # Service unavailable
        except:
            return -1  # Service unavailable

    def get_system_status(self):
        """Get comprehensive system status"""
        status = {
            "timestamp": datetime.now().isoformat(),
            "uptime": self.get_system_uptime(),
            "processes": self.get_celsius_processes(),
            "ngrok_status": self.get_ngrok_status(),
            "disk_space": self.get_disk_space(),
            "network_status": self.get_network_status(),
            "security_status": self.get_security_status(),
        }

        return status

    def get_system_uptime(self):
        """Get system uptime"""
        try:
            uptime_seconds = time.time() - psutil.boot_time()
            uptime = str(timedelta(seconds=int(uptime_seconds)))
            return uptime
        except:
            return "Unknown"

    def get_celsius_processes(self):
        """Get status of Celsius AI related processes"""
        processes = {"celsius_ai": False, "ngrok": False, "persistent_service": False, "process_count": 0}

        try:
            for proc in psutil.process_iter(["pid", "name", "cmdline"]):
                cmdline = " ".join(proc.info["cmdline"] or [])

                if "enhanced_mobile_dashboard.py" in cmdline:
                    processes["celsius_ai"] = True
                    processes["process_count"] += 1
                elif "ngrok.exe" in proc.info["name"]:
                    processes["ngrok"] = True
                    processes["process_count"] += 1
                elif "persistent_celsius_service.py" in cmdline:
                    processes["persistent_service"] = True
                    processes["process_count"] += 1
        except:
            pass

        return processes

    def get_ngrok_status(self):
        """Get ngrok tunnel status"""
        tunnels = []
        active_count = 0

        for port in [4040, 4041, 4042, 4043]:
            try:
                response = requests.get(f"http://127.0.0.1:{port}/api/tunnels", timeout=2)
                if response.status_code == 200:
                    data = response.json()
                    for tunnel in data.get("tunnels", []):
                        tunnels.append(
                            {
                                "name": tunnel.get("name"),
                                "public_url": tunnel.get("public_url"),
                                "proto": tunnel.get("proto"),
                                "created_at": tunnel.get("created_at"),
                            }
                        )
                        active_count += 1
            except:
                continue

        return {"active_tunnels": active_count, "tunnel_details": tunnels}

    def get_disk_space(self):
        """Get disk space information"""
        try:
            disk = psutil.disk_usage("C:")
            return {
                "total_gb": round(disk.total / (1024**3), 2),
                "used_gb": round(disk.used / (1024**3), 2),
                "free_gb": round(disk.free / (1024**3), 2),
                "percent_used": round((disk.used / disk.total) * 100, 2),
            }
        except:
            return {"error": "Unable to get disk information"}

    def get_network_status(self):
        """Get network status and statistics"""
        try:
            net_io = psutil.net_io_counters()
            connections = psutil.net_connections()

            # Count connections by status
            conn_status = {}
            for conn in connections:
                status = conn.status
                conn_status[status] = conn_status.get(status, 0) + 1

            return {
                "bytes_sent": net_io.bytes_sent,
                "bytes_recv": net_io.bytes_recv,
                "packets_sent": net_io.packets_sent,
                "packets_recv": net_io.packets_recv,
                "total_connections": len(connections),
                "connection_status": conn_status,
                "internet_connectivity": self.test_internet_connectivity(),
            }
        except:
            return {"error": "Unable to get network information"}

    def test_internet_connectivity(self):
        """Test internet connectivity"""
        try:
            response = requests.get("https://www.google.com", timeout=5)
            return response.status_code == 200
        except:
            return False

    def get_security_status(self):
        """Get basic security status"""
        security = {
            "firewall_status": "unknown",
            "antivirus_running": False,
            "suspicious_processes": [],
            "open_ports": [],
        }

        try:
            # Check for suspicious processes (basic check)
            for proc in psutil.process_iter(["pid", "name", "exe"]):
                name = proc.info["name"].lower()
                if any(suspicious in name for suspicious in ["hack", "crack", "virus", "malware"]):
                    security["suspicious_processes"].append(proc.info["name"])

            # Check for common antivirus processes
            av_processes = ["mcshield.exe", "avp.exe", "avgnt.exe", "mbam.exe", "windefend"]
            for proc in psutil.process_iter(["name"]):
                if proc.info["name"].lower() in av_processes:
                    security["antivirus_running"] = True
                    break

            # Get listening ports
            for conn in psutil.net_connections(kind="inet"):
                if conn.status == "LISTEN":
                    security["open_ports"].append(conn.laddr.port)

        except:
            pass

        return security

    def generate_hourly_report(self):
        """Generate comprehensive hourly report"""
        report_time = datetime.now()

        # Collect all system data
        system_status = self.get_system_status()
        performance_data = self.get_recent_performance(60)  # Last hour
        error_summary = self.get_error_summary()

        # Generate insights and recommendations
        recommendations = self.generate_recommendations(system_status, performance_data)

        # Create detailed report
        report = {
            "report_timestamp": report_time.isoformat(),
            "report_period": "hourly",
            "system_summary": {
                "status": "operational" if system_status["processes"]["celsius_ai"] else "degraded",
                "uptime": system_status["uptime"],
                "active_processes": system_status["processes"]["process_count"],
                "active_tunnels": system_status["ngrok_status"]["active_tunnels"],
            },
            "performance_summary": performance_data,
            "security_assessment": system_status["security_status"],
            "network_overview": system_status["network_status"],
            "disk_status": system_status["disk_space"],
            "error_analysis": error_summary,
            "recommendations": recommendations,
            "detailed_metrics": system_status,
        }

        # Save to database
        self.save_hourly_report(report)

        # Save to JSON file
        self.save_report_file(report)

        # Log the report generation
        try:
            print(f"Hourly report generated at {report_time.strftime('%Y-%m-%d %H:%M:%S')}")
        except UnicodeEncodeError:
            print(f"Hourly report generated at {report_time.strftime('%Y-%m-%d %H:%M:%S')}")

        return report

    def get_recent_performance(self, minutes=60):
        """Get performance metrics from the last N minutes"""
        try:
            since_time = datetime.now() - timedelta(minutes=minutes)

            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()

            cursor.execute(
                """
                SELECT cpu_percent, memory_percent, disk_usage, response_time
                FROM performance_metrics
                WHERE timestamp > ?
                ORDER BY timestamp DESC
            """,
                (since_time.isoformat(),),
            )

            rows = cursor.fetchall()
            conn.close()

            if not rows:
                return {"error": "No performance data available"}

            # Calculate averages
            cpu_avg = sum(row[0] for row in rows if row[0] is not None) / len(rows)
            memory_avg = sum(row[1] for row in rows if row[1] is not None) / len(rows)
            disk_avg = sum(row[2] for row in rows if row[2] is not None) / len(rows)

            # Response times (filter out -1 values)
            response_times = [row[3] for row in rows if row[3] > 0]
            response_avg = sum(response_times) / len(response_times) if response_times else -1

            return {
                "period_minutes": minutes,
                "sample_count": len(rows),
                "cpu_average": round(cpu_avg, 2),
                "memory_average": round(memory_avg, 2),
                "disk_usage": round(disk_avg, 2),
                "response_time_average": round(response_avg, 2) if response_avg > 0 else "Service unavailable",
                "performance_score": self.calculate_performance_score(cpu_avg, memory_avg, response_avg),
            }
        except Exception as e:
            return {"error": str(e)}

    def calculate_performance_score(self, cpu, memory, response_time):
        """Calculate overall performance score (0-100)"""
        score = 100

        # CPU penalty
        if cpu > 80:
            score -= 30
        elif cpu > 60:
            score -= 15

        # Memory penalty
        if memory > 90:
            score -= 30
        elif memory > 75:
            score -= 15

        # Response time penalty
        if response_time > 0:
            if response_time > 1000:  # > 1 second
                score -= 20
            elif response_time > 500:  # > 500ms
                score -= 10
        else:
            score -= 40  # Service unavailable

        return max(0, score)

    def get_error_summary(self):
        """Get summary of recent errors and issues"""
        errors = []

        # Check system logs for the last hour
        since_time = datetime.now() - timedelta(hours=1)

        try:
            # Check if services are running
            processes = self.get_celsius_processes()

            if not processes["celsius_ai"]:
                errors.append(
                    {
                        "level": "critical",
                        "message": "Celsius AI dashboard service not running",
                        "timestamp": datetime.now().isoformat(),
                    }
                )

            if not processes["ngrok"]:
                errors.append(
                    {
                        "level": "warning",
                        "message": "ngrok tunnel service not running",
                        "timestamp": datetime.now().isoformat(),
                    }
                )

            # Check disk space
            disk = self.get_disk_space()
            if isinstance(disk, dict) and disk.get("percent_used", 0) > 90:
                errors.append(
                    {
                        "level": "warning",
                        "message": f'Low disk space: {disk["percent_used"]}% used',
                        "timestamp": datetime.now().isoformat(),
                    }
                )

            # Check response time
            response_time = self.test_response_time()
            if response_time < 0:
                errors.append(
                    {
                        "level": "critical",
                        "message": "Celsius AI service not responding",
                        "timestamp": datetime.now().isoformat(),
                    }
                )
            elif response_time > 2000:
                errors.append(
                    {
                        "level": "warning",
                        "message": f"Slow response time: {response_time}ms",
                        "timestamp": datetime.now().isoformat(),
                    }
                )

        except Exception as e:
            errors.append(
                {
                    "level": "error",
                    "message": f"Error checking system status: {str(e)}",
                    "timestamp": datetime.now().isoformat(),
                }
            )

        return {
            "total_errors": len(errors),
            "critical_count": len([e for e in errors if e["level"] == "critical"]),
            "warning_count": len([e for e in errors if e["level"] == "warning"]),
            "errors": errors,
        }

    def generate_recommendations(self, system_status, performance_data):
        """Generate actionable recommendations based on system analysis"""
        recommendations = []

        # Performance recommendations
        if isinstance(performance_data, dict):
            cpu_avg = performance_data.get("cpu_average", 0)
            memory_avg = performance_data.get("memory_average", 0)

            if cpu_avg > 80:
                recommendations.append(
                    {
                        "category": "performance",
                        "priority": "high",
                        "message": "High CPU usage detected. Consider closing unnecessary applications.",
                        "action": "Monitor running processes and optimize system resources",
                    }
                )

            if memory_avg > 85:
                recommendations.append(
                    {
                        "category": "performance",
                        "priority": "high",
                        "message": "High memory usage detected. System may benefit from more RAM.",
                        "action": "Check for memory leaks or consider hardware upgrade",
                    }
                )

        # Process recommendations
        processes = system_status.get("processes", {})
        if not processes.get("celsius_ai"):
            recommendations.append(
                {
                    "category": "service",
                    "priority": "critical",
                    "message": "Celsius AI service is not running",
                    "action": "Restart the enhanced mobile dashboard service",
                }
            )

        if not processes.get("ngrok"):
            recommendations.append(
                {
                    "category": "network",
                    "priority": "medium",
                    "message": "ngrok tunnel is not active - no external access available",
                    "action": "Start ngrok service for remote access",
                }
            )

        # Disk space recommendations
        disk_status = system_status.get("disk_space", {})
        if isinstance(disk_status, dict):
            percent_used = disk_status.get("percent_used", 0)
            if percent_used > 90:
                recommendations.append(
                    {
                        "category": "storage",
                        "priority": "high",
                        "message": f"Disk space critically low: {percent_used}% used",
                        "action": "Clean temporary files and logs, or add more storage",
                    }
                )
            elif percent_used > 80:
                recommendations.append(
                    {
                        "category": "storage",
                        "priority": "medium",
                        "message": f"Disk space getting low: {percent_used}% used",
                        "action": "Monitor disk usage and plan for cleanup",
                    }
                )

        # Security recommendations
        security = system_status.get("security_status", {})
        if not security.get("antivirus_running"):
            recommendations.append(
                {
                    "category": "security",
                    "priority": "medium",
                    "message": "No active antivirus detected",
                    "action": "Ensure Windows Defender or antivirus software is running",
                }
            )

        return recommendations

    def save_hourly_report(self, report):
        """Save hourly report to database"""
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()

            cursor.execute(
                """
                INSERT INTO hourly_reports 
                (timestamp, system_status, performance_metrics, security_status, 
                 network_status, process_status, error_summary, recommendations)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            """,
                (
                    report["report_timestamp"],
                    json.dumps(report["system_summary"]),
                    json.dumps(report["performance_summary"]),
                    json.dumps(report["security_assessment"]),
                    json.dumps(report["network_overview"]),
                    json.dumps(report["detailed_metrics"]["processes"]),
                    json.dumps(report["error_analysis"]),
                    json.dumps(report["recommendations"]),
                ),
            )

            conn.commit()
            conn.close()

        except Exception as e:
            print(f"Error saving hourly report: {e}")

    def save_report_file(self, report):
        """Save report as JSON file"""
        try:
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            filename = self.logs_dir / f"celsius_report_{timestamp}.json"

            with open(filename, "w", encoding="utf-8") as f:
                json.dump(report, f, indent=2, ensure_ascii=False)

            try:
                print(f"Report saved: {filename}")
            except UnicodeEncodeError:
                print(f"Report saved: {filename}")

            # Keep only last 24 reports (24 hours)
            self.cleanup_old_reports()

        except Exception as e:
            print(f"Error saving report file: {e}")

    def cleanup_old_reports(self):
        """Remove old report files to save space"""
        try:
            report_files = list(self.logs_dir.glob("celsius_report_*.json"))

            # Sort by modification time
            report_files.sort(key=lambda x: x.stat().st_mtime, reverse=True)

            # Keep only the most recent 24 files
            for old_report in report_files[24:]:
                old_report.unlink()
                try:
                    print(f"Cleaned up old report: {old_report.name}")
                except UnicodeEncodeError:
                    print(f"Cleaned up old report: {old_report.name}")

        except Exception as e:
            print(f"Error cleaning up old reports: {e}")

    def start_hourly_logging(self):
        """Start the hourly logging thread"""

        def logging_loop():
            try:
                print("Celsius AI Hourly Logging Started")
            except UnicodeEncodeError:
                print("Celsius AI Hourly Logging Started")

            while self.running:
                try:
                    current_time = datetime.now()

                    # Log performance metrics every 5 minutes
                    if (current_time - self.last_log_time).total_seconds() >= 300:  # 5 minutes
                        self.log_performance_metrics()
                        self.last_log_time = current_time

                    # Generate hourly report at the start of each hour
                    if current_time.minute == 0 and current_time.second < 30:
                        self.generate_hourly_report()
                        time.sleep(30)  # Prevent multiple reports in the same minute

                    time.sleep(30)  # Check every 30 seconds

                except Exception as e:
                    print(f"Logging loop error: {e}")
                    time.sleep(60)

        logging_thread = threading.Thread(target=logging_loop, daemon=True)
        logging_thread.start()
        return logging_thread

    def stop_logging(self):
        """Stop the logging system"""
        self.running = False
        try:
            print("Celsius AI Hourly Logging Stopped")
        except UnicodeEncodeError:
            print("Celsius AI Hourly Logging Stopped")


def main():
    """Run the logging system standalone"""
    try:
        print("[HOURLY-LOGGER] Celsius AI Hourly Logger initializing...")
    except UnicodeEncodeError:
        print("[HOURLY-LOGGER] Celsius AI Hourly Logger initializing...")

    logger = CelsiusLogger()

    # Create lock file to indicate running
    lock_file = Path("celsius_hourly_logger.lock")
    with open(lock_file, "w") as f:
        f.write(str(os.getpid()))

    def cleanup():
        """Cleanup function"""
        try:
            if lock_file.exists():
                lock_file.unlink()
            logger.stop_logging()
        except Exception:
            pass

    # Register cleanup
    import atexit

    atexit.register(cleanup)

    # Generate an immediate report for testing
    try:
        print("[HOURLY-LOGGER] Generating initial report...")
        logger.generate_hourly_report()
        print("[HOURLY-LOGGER] Initial report generated successfully")
    except Exception as e:
        print(f"[HOURLY-LOGGER] Initial report error: {e}")

    # Start continuous logging
    try:
        print("[HOURLY-LOGGER] Starting continuous logging thread...")
        logging_thread = logger.start_hourly_logging()
        print("[HOURLY-LOGGER] Hourly logger is running continuously")

        # Keep main thread alive with status updates
        start_time = time.time()
        while logger.running:
            time.sleep(300)  # Status update every 5 minutes
            uptime = int(time.time() - start_time)
            try:
                print(f"[HOURLY-LOGGER] Status: Running - Uptime: {uptime}s")
            except UnicodeEncodeError:
                print(f"[HOURLY-LOGGER] Status: Running - Uptime: {uptime}s")

    except KeyboardInterrupt:
        print("[HOURLY-LOGGER] Shutdown requested")
    except Exception as e:
        print(f"[HOURLY-LOGGER] Critical error: {e}")
    finally:
        cleanup()
        print("[HOURLY-LOGGER] Hourly Logger stopped")


if __name__ == "__main__":
    main()
