#!/usr/bin/env python3
"""
Test mobile server startup exactly like the guardian does
"""

import subprocess
import time
import sys
import os


def test_guardian_startup():
    """Test startup exactly like guardian"""

    os.chdir("C:/Users/micro/Celsius AI")

    print("Testing mobile server startup like guardian...")

    # Start exactly like guardian does
    proc = subprocess.Popen(
        [sys.executable, "enhanced_mobile_dashboard.py"],
        cwd="C:/Users/micro/Celsius AI",
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        creationflags=subprocess.CREATE_NO_WINDOW | subprocess.CREATE_NEW_PROCESS_GROUP,
    )

    print(f"Started PID: {proc.pid}")

    # Wait and check like guardian does
    time.sleep(5)

    if proc.poll() is not None:
        # Process terminated
        stdout, stderr = proc.communicate()
        print(f"Process terminated with return code: {proc.returncode}")
        print(f"STDOUT:\n{stdout.decode()}")
        print(f"STDERR:\n{stderr.decode()}")
        return False
    else:
        print("Process still running - SUCCESS!")

        # Test guardian detection
        import psutil

        if psutil.pid_exists(proc.pid):
            process = psutil.Process(proc.pid)
            cmdline = " ".join(process.cmdline())
            print(f"Guardian would detect: {cmdline}")
            if "enhanced_mobile_dashboard.py" in cmdline:
                print("Guardian detection: SUCCESS")
            else:
                print("Guardian detection: FAILED")

        # Clean up
        proc.terminate()
        return True


if __name__ == "__main__":
    test_guardian_startup()
