#!/usr/bin/env python3
"""
⚡ CELSIUS AI - PERFORMANCE OPTIMIZER ⚡
═══════════════════════════════════════════════════════════════════════════════════════════

Advanced performance optimization tool for the unified Celsius AI system.
Analyzes and optimizes startup times, memory usage, and database operations.

═══════════════════════════════════════════════════════════════════════════════════════════
"""

import time
import psutil
import sqlite3
import os
import gc
import platform
from pathlib import Path
import json
from datetime import datetime


class CelsiusOptimizer:
    """Advanced performance optimization system"""

    def __init__(self):
        self.base_dir = Path.cwd()
        self.optimization_results = {}

    def analyze_startup_performance(self):
        """Analyze and optimize startup performance"""
        print("⚡ Analyzing startup performance...")

        # Test import times
        import_tests = [
            ("tkinter", "import tkinter as tk"),
            ("sqlite3", "import sqlite3"),
            ("psutil", "import psutil"),
            ("requests", "import requests"),
            ("flask", "import flask"),
            ("threading", "import threading"),
            ("pathlib", "from pathlib import Path"),
            ("datetime", "from datetime import datetime"),
        ]

        import_times = {}

        for module_name, import_statement in import_tests:
            start_time = time.time()
            try:
                exec(import_statement)
                import_time = time.time() - start_time
                import_times[module_name] = import_time * 1000  # Convert to ms
                print(f"   ✅ {module_name}: {import_time*1000:.2f}ms")
            except ImportError:
                import_times[module_name] = -1
                print(f"   ❌ {module_name}: Not available")

        self.optimization_results["import_times"] = import_times
        return import_times

    def optimize_database_operations(self):
        """Optimize database performance"""
        print("🗄️  Optimizing database operations...")

        databases = ["celsius_activity.db", "celsius_system.db", "celsius_monitoring.db"]

        optimization_report = {}

        for db_name in databases:
            db_path = self.base_dir / db_name
            if not db_path.exists():
                continue

            print(f"   📊 Optimizing {db_name}...")

            try:
                conn = sqlite3.connect(db_path)
                cursor = conn.cursor()

                # Analyze database
                cursor.execute("PRAGMA page_count")
                page_count = cursor.fetchone()[0]

                cursor.execute("PRAGMA page_size")
                page_size = cursor.fetchone()[0]

                db_size_mb = (page_count * page_size) / 1024 / 1024

                # Optimize database
                start_time = time.time()

                # Vacuum database
                cursor.execute("VACUUM")

                # Analyze database for query optimization
                cursor.execute("ANALYZE")

                # Set performance pragmas
                cursor.execute("PRAGMA synchronous = NORMAL")
                cursor.execute("PRAGMA cache_size = -64000")  # 64MB cache
                cursor.execute("PRAGMA temp_store = MEMORY")
                cursor.execute("PRAGMA journal_mode = WAL")

                conn.commit()

                optimization_time = time.time() - start_time

                # Check new size
                cursor.execute("PRAGMA page_count")
                new_page_count = cursor.fetchone()[0]
                new_size_mb = (new_page_count * page_size) / 1024 / 1024

                space_saved = db_size_mb - new_size_mb

                conn.close()

                optimization_report[db_name] = {
                    "original_size_mb": db_size_mb,
                    "optimized_size_mb": new_size_mb,
                    "space_saved_mb": space_saved,
                    "optimization_time_s": optimization_time,
                }

                print(f"      ✅ Size: {db_size_mb:.2f}MB → {new_size_mb:.2f}MB (saved {space_saved:.2f}MB)")
                print(f"      ⏱️  Time: {optimization_time:.2f}s")

            except Exception as e:
                print(f"      ❌ Error optimizing {db_name}: {e}")
                optimization_report[db_name] = {"error": str(e)}

        self.optimization_results["database_optimization"] = optimization_report
        return optimization_report

    def analyze_memory_usage(self):
        """Analyze and optimize memory usage"""
        print("💾 Analyzing memory usage...")

        process = psutil.Process()

        # Initial memory state
        initial_memory = process.memory_info()
        print(f"   📊 Initial Memory: {initial_memory.rss / 1024 / 1024:.2f} MB")

        # Force garbage collection
        collected = gc.collect()
        print(f"   🧹 Garbage collected: {collected} objects")

        # Memory after cleanup
        cleaned_memory = process.memory_info()
        memory_saved = (initial_memory.rss - cleaned_memory.rss) / 1024 / 1024

        print(f"   📊 After cleanup: {cleaned_memory.rss / 1024 / 1024:.2f} MB")
        print(f"   💾 Memory saved: {memory_saved:.2f} MB")

        memory_analysis = {
            "initial_memory_mb": initial_memory.rss / 1024 / 1024,
            "cleaned_memory_mb": cleaned_memory.rss / 1024 / 1024,
            "memory_saved_mb": memory_saved,
            "gc_objects_collected": collected,
        }

        self.optimization_results["memory_analysis"] = memory_analysis
        return memory_analysis

    def optimize_file_system(self):
        """Optimize file system operations"""
        print("📁 Optimizing file system...")

        # Check for temporary files
        temp_patterns = ["*.tmp", "*.temp", "__pycache__", "*.pyc", "*.log~"]
        temp_files_found = []

        for pattern in temp_patterns:
            matches = list(self.base_dir.glob(f"**/{pattern}"))
            temp_files_found.extend(matches)

        total_temp_size = 0
        cleaned_files = 0

        for temp_file in temp_files_found:
            try:
                if temp_file.is_file():
                    file_size = temp_file.stat().st_size
                    total_temp_size += file_size

                    # Only clean safe temporary files
                    if temp_file.suffix in [".tmp", ".temp", ".pyc"] or temp_file.name.endswith("~"):
                        temp_file.unlink()
                        cleaned_files += 1
                        print(f"   🗑️  Removed: {temp_file.name}")

            except Exception as e:
                print(f"   ⚠️  Could not remove {temp_file.name}: {e}")

        fs_optimization = {
            "temp_files_found": len(temp_files_found),
            "temp_files_cleaned": cleaned_files,
            "space_recovered_mb": total_temp_size / 1024 / 1024,
        }

        print(f"   📊 Found {len(temp_files_found)} temp files")
        print(f"   🧹 Cleaned {cleaned_files} files")
        print(f"   💾 Recovered {total_temp_size / 1024 / 1024:.2f} MB")

        self.optimization_results["filesystem_optimization"] = fs_optimization
        return fs_optimization

    def benchmark_system_performance(self):
        """Run comprehensive system performance benchmarks"""
        print("🎯 Running performance benchmarks...")

        benchmarks = {}

        # CPU benchmark
        print("   🖥️  CPU benchmark...")
        start_time = time.time()
        cpu_test_result = sum(i**2 for i in range(100000))
        cpu_time = time.time() - start_time
        benchmarks["cpu_benchmark_ms"] = cpu_time * 1000
        print(f"      CPU test: {cpu_time*1000:.2f}ms")

        # Disk I/O benchmark
        print("   💿 Disk I/O benchmark...")
        test_file = self.base_dir / "temp_benchmark.dat"

        start_time = time.time()
        with open(test_file, "wb") as f:
            f.write(b"0" * 1024 * 1024)  # Write 1MB
        write_time = time.time() - start_time

        start_time = time.time()
        with open(test_file, "rb") as f:
            data = f.read()
        read_time = time.time() - start_time

        test_file.unlink()  # Clean up

        benchmarks["disk_write_ms"] = write_time * 1000
        benchmarks["disk_read_ms"] = read_time * 1000

        print(f"      Disk write: {write_time*1000:.2f}ms")
        print(f"      Disk read: {read_time*1000:.2f}ms")

        # Database benchmark
        print("   🗄️  Database benchmark...")
        test_db = self.base_dir / "benchmark.db"

        start_time = time.time()
        conn = sqlite3.connect(test_db)
        cursor = conn.cursor()

        cursor.execute("CREATE TABLE test (id INTEGER, data TEXT)")

        # Insert test
        for i in range(1000):
            cursor.execute("INSERT INTO test VALUES (?, ?)", (i, f"test_data_{i}"))

        conn.commit()
        insert_time = time.time() - start_time

        # Query test
        start_time = time.time()
        cursor.execute("SELECT COUNT(*) FROM test")
        result = cursor.fetchone()
        query_time = time.time() - start_time

        conn.close()
        test_db.unlink()  # Clean up

        benchmarks["db_insert_1000_ms"] = insert_time * 1000
        benchmarks["db_query_ms"] = query_time * 1000

        print(f"      DB insert (1000 rows): {insert_time*1000:.2f}ms")
        print(f"      DB query: {query_time*1000:.2f}ms")

        self.optimization_results["performance_benchmarks"] = benchmarks
        return benchmarks

    def generate_optimization_report(self):
        """Generate comprehensive optimization report"""
        print("\n" + "=" * 70)
        print("⚡ CELSIUS AI PERFORMANCE OPTIMIZATION REPORT")
        print("=" * 70)

        # System info
        print(f"\n🖥️  System Information:")
        print(f"   Platform: {platform.system()} {platform.release()}")
        print(f"   CPU cores: {psutil.cpu_count()}")
        print(f"   Memory: {psutil.virtual_memory().total / 1024**3:.1f} GB")
        print(f"   Python version: {platform.python_version()}")

        # Import performance
        if "import_times" in self.optimization_results:
            print(f"\n📦 Import Performance:")
            for module, time_ms in self.optimization_results["import_times"].items():
                if time_ms > 0:
                    status = "⚡" if time_ms < 10 else "⚠️" if time_ms < 50 else "🐌"
                    print(f"   {status} {module}: {time_ms:.2f}ms")

        # Database optimization
        if "database_optimization" in self.optimization_results:
            print(f"\n🗄️  Database Optimization:")
            total_space_saved = 0
            for db_name, results in self.optimization_results["database_optimization"].items():
                if "space_saved_mb" in results:
                    print(f"   ✅ {db_name}: {results['space_saved_mb']:.2f}MB saved")
                    total_space_saved += results["space_saved_mb"]
            print(f"   💾 Total space saved: {total_space_saved:.2f}MB")

        # Memory optimization
        if "memory_analysis" in self.optimization_results:
            memory = self.optimization_results["memory_analysis"]
            print(f"\n💾 Memory Optimization:")
            print(f"   📊 Memory usage: {memory['cleaned_memory_mb']:.2f}MB")
            print(f"   🧹 Memory saved: {memory['memory_saved_mb']:.2f}MB")
            print(f"   🗑️  GC objects: {memory['gc_objects_collected']}")

        # File system optimization
        if "filesystem_optimization" in self.optimization_results:
            fs = self.optimization_results["filesystem_optimization"]
            print(f"\n📁 File System Optimization:")
            print(f"   🧹 Files cleaned: {fs['temp_files_cleaned']}")
            print(f"   💾 Space recovered: {fs['space_recovered_mb']:.2f}MB")

        # Performance benchmarks
        if "performance_benchmarks" in self.optimization_results:
            bench = self.optimization_results["performance_benchmarks"]
            print(f"\n🎯 Performance Benchmarks:")
            print(f"   🖥️  CPU test: {bench['cpu_benchmark_ms']:.2f}ms")
            print(f"   💿 Disk write: {bench['disk_write_ms']:.2f}ms")
            print(f"   💿 Disk read: {bench['disk_read_ms']:.2f}ms")
            print(f"   🗄️  DB insert: {bench['db_insert_1000_ms']:.2f}ms")
            print(f"   🗄️  DB query: {bench['db_query_ms']:.2f}ms")

        # Save report
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        report_file = self.base_dir / f"optimization_report_{timestamp}.json"

        report_data = {
            "timestamp": datetime.now().isoformat(),
            "optimization_results": self.optimization_results,
            "recommendations": self.generate_recommendations(),
        }

        with open(report_file, "w") as f:
            json.dump(report_data, f, indent=2)

        print(f"\n📋 Report saved to: {report_file.name}")

        return report_data

    def generate_recommendations(self):
        """Generate optimization recommendations"""
        recommendations = []

        # Check import times
        if "import_times" in self.optimization_results:
            slow_imports = {k: v for k, v in self.optimization_results["import_times"].items() if v > 50 and v > 0}
            if slow_imports:
                recommendations.append(f"Consider lazy loading for slow imports: {list(slow_imports.keys())}")

        # Check memory usage
        if "memory_analysis" in self.optimization_results:
            memory = self.optimization_results["memory_analysis"]
            if memory["cleaned_memory_mb"] > 100:
                recommendations.append("Memory usage is high - consider optimizing data structures")

        # Check database performance
        if "performance_benchmarks" in self.optimization_results:
            bench = self.optimization_results["performance_benchmarks"]
            if bench["db_insert_1000_ms"] > 1000:
                recommendations.append("Database insert performance is slow - consider batch operations")
            if bench["db_query_ms"] > 100:
                recommendations.append("Database query performance is slow - consider adding indexes")

        return recommendations

    def run_full_optimization(self):
        """Run complete optimization suite"""
        print("🚀 Starting Celsius AI Performance Optimization")
        print("=" * 50)

        start_time = time.time()

        # Run all optimization steps
        self.analyze_startup_performance()
        print()

        self.optimize_database_operations()
        print()

        self.analyze_memory_usage()
        print()

        self.optimize_file_system()
        print()

        self.benchmark_system_performance()

        total_time = time.time() - start_time

        # Generate final report
        report = self.generate_optimization_report()

        print(f"\n⏱️  Total optimization time: {total_time:.2f} seconds")
        print("🎉 Optimization complete!")

        return report


def main():
    """Run the optimization suite"""
    optimizer = CelsiusOptimizer()

    print("⚡ Celsius AI Performance Optimizer")
    print("=" * 40)

    response = input("Run full optimization? (Y/n): ").strip().lower()

    if response != "n":
        optimizer.run_full_optimization()
    else:
        print("🔍 Skipping optimization. Use 'y' to run full suite.")


if __name__ == "__main__":
    main()
