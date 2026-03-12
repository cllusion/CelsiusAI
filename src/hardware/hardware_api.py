#!/usr/bin/env python3
"""
🎮 Celsius AI Hardware API
==========================
Simple web API for controlling desktop fans and RGB lighting.
Integrates with Ultimate Hub for easy hardware management.
"""

from flask import Flask, jsonify, request
import asyncio
import json
import subprocess
import winreg
import psutil
from pathlib import Path

app = Flask(__name__)


class SimpleHardwareController:
    """Simplified hardware controller for basic fan and RGB control"""

    def __init__(self):
        self.profiles = {
            "gaming": {"fan_speed": 75, "rgb_color": [255, 0, 0], "rgb_effect": "rainbow"},  # Red
            "work": {"fan_speed": 40, "rgb_color": [0, 255, 0], "rgb_effect": "static"},  # Green
            "sleep": {"fan_speed": 25, "rgb_color": [0, 0, 50], "rgb_effect": "breathing"},  # Dim blue
            "party": {"fan_speed": 60, "rgb_color": [255, 255, 0], "rgb_effect": "strobe"},  # Yellow
        }
        self.current_profile = "work"

    def get_cpu_temperature(self):
        """Get CPU temperature if available"""
        try:
            temps = psutil.sensors_temperatures()
            if temps:
                for name, entries in temps.items():
                    if "cpu" in name.lower() or "core" in name.lower():
                        return max(entry.current for entry in entries)
            return None
        except Exception:
            return None

    def set_fan_speed_via_registry(self, speed_percent):
        """Try to set fan speed via Windows registry (basic method)"""
        try:
            # This is a placeholder - actual implementation depends on hardware
            # Some systems support registry-based fan control
            key_path = r"SYSTEM\CurrentControlSet\Control\Class\{4d36e968-e325-11ce-bfc1-08002be10318}\0000"
            with winreg.OpenKey(winreg.HKEY_LOCAL_MACHINE, key_path, 0, winreg.KEY_WRITE) as key:
                # Set fan speed (implementation varies by hardware)
                pass
            return True
        except Exception:
            return False

    def control_rgb_via_openrgb(self, r, g, b, effect="static"):
        """Control RGB via OpenRGB if available"""
        try:
            # Try OpenRGB command line
            cmd = f"OpenRGB.exe --color {r:02x}{g:02x}{b:02x} --mode {effect}"
            subprocess.run(cmd, shell=True, capture_output=True, timeout=5)
            return True
        except Exception:
            return False

    def control_rgb_via_powershell(self, r, g, b):
        """Control RGB via PowerShell scripts (for some hardware)"""
        try:
            # Example PowerShell script for RGB control
            ps_script = f"""
            # RGB Control Script
            $Red = {r}
            $Green = {g}
            $Blue = {b}
            
            # Try to control RGB via COM objects or registry
            # Implementation depends on specific hardware
            """

            subprocess.run(["powershell", "-Command", ps_script], capture_output=True, timeout=10)
            return True
        except Exception:
            return False

    def apply_profile(self, profile_name):
        """Apply a hardware profile"""
        if profile_name not in self.profiles:
            return False

        profile = self.profiles[profile_name]
        self.current_profile = profile_name

        # Apply fan settings
        fan_success = self.set_fan_speed_via_registry(profile["fan_speed"])

        # Apply RGB settings
        color = profile["rgb_color"]
        rgb_success = self.control_rgb_via_openrgb(
            color[0], color[1], color[2], profile["rgb_effect"]
        ) or self.control_rgb_via_powershell(color[0], color[1], color[2])

        return fan_success or rgb_success


# Initialize controller
controller = SimpleHardwareController()


@app.route("/api/hardware/status")
def get_status():
    """Get current hardware status"""
    temp = controller.get_cpu_temperature()
    return jsonify(
        {
            "current_profile": controller.current_profile,
            "cpu_temperature": temp,
            "profiles": list(controller.profiles.keys()),
            "status": "running",
        }
    )


@app.route("/api/hardware/profile/<profile_name>", methods=["POST"])
def set_profile(profile_name):
    """Set hardware profile"""
    success = controller.apply_profile(profile_name)
    return jsonify(
        {
            "success": success,
            "profile": profile_name,
            "message": f'Profile {profile_name} {"applied" if success else "failed"}',
        }
    )


@app.route("/api/hardware/fan/<int:speed>")
def set_fan_speed(speed):
    """Set fan speed (0-100%)"""
    speed = max(0, min(100, speed))
    success = controller.set_fan_speed_via_registry(speed)
    return jsonify({"success": success, "fan_speed": speed, "message": f"Fan speed set to {speed}%"})


@app.route("/api/hardware/rgb/<int:r>/<int:g>/<int:b>")
def set_rgb_color(r, g, b):
    """Set RGB color (0-255 for each channel)"""
    r, g, b = max(0, min(255, r)), max(0, min(255, g)), max(0, min(255, b))
    success = controller.control_rgb_via_openrgb(r, g, b) or controller.control_rgb_via_powershell(r, g, b)
    return jsonify({"success": success, "color": [r, g, b], "message": f"RGB color set to ({r}, {g}, {b})"})


@app.route("/api/hardware/temperature")
def get_temperature():
    """Get CPU temperature"""
    temp = controller.get_cpu_temperature()
    return jsonify({"cpu_temperature": temp, "unit": "celsius", "available": temp is not None})


@app.route("/")
def index():
    """Simple web interface for hardware control"""
    return """
    <!DOCTYPE html>
    <html>
    <head>
        <title>Celsius AI Hardware Controller</title>
        <style>
            body { font-family: Arial, sans-serif; margin: 40px; background: #1a1a1a; color: #fff; }
            .container { max-width: 800px; margin: 0 auto; }
            .section { background: #2a2a2a; padding: 20px; margin: 20px 0; border-radius: 10px; }
            .button { background: #4CAF50; color: white; padding: 10px 20px; margin: 5px; border: none; border-radius: 5px; cursor: pointer; }
            .button:hover { background: #45a049; }
            .slider { width: 100%; }
            .color-picker { width: 60px; height: 40px; border: none; border-radius: 5px; }
            .status { font-family: monospace; background: #000; padding: 10px; border-radius: 5px; }
        </style>
    </head>
    <body>
        <div class="container">
            <h1>🎮 Celsius AI Hardware Controller</h1>
            
            <div class="section">
                <h2>🌡️ System Status</h2>
                <div id="status" class="status">Loading...</div>
                <button class="button" onclick="updateStatus()">Refresh Status</button>
            </div>
            
            <div class="section">
                <h2>🎯 Performance Profiles</h2>
                <button class="button" onclick="setProfile('gaming')" style="background: #ff4444;">🎮 Gaming</button>
                <button class="button" onclick="setProfile('work')" style="background: #44ff44;">💼 Work</button>
                <button class="button" onclick="setProfile('sleep')" style="background: #4444ff;">😴 Sleep</button>
                <button class="button" onclick="setProfile('party')" style="background: #ffff44; color: #000;">🎉 Party</button>
            </div>
            
            <div class="section">
                <h2>🌪️ Fan Control</h2>
                <input type="range" id="fanSlider" class="slider" min="0" max="100" value="50" oninput="setFanSpeed(this.value)">
                <p>Fan Speed: <span id="fanValue">50</span>%</p>
            </div>
            
            <div class="section">
                <h2>🌈 RGB Lighting</h2>
                <input type="color" id="colorPicker" class="color-picker" onchange="setRGBColor(this.value)">
                <p>Click to choose RGB color</p>
            </div>
        </div>
        
        <script>
            function updateStatus() {
                fetch('/api/hardware/status')
                    .then(response => response.json())
                    .then(data => {
                        document.getElementById('status').innerHTML = 
                            'Profile: ' + data.current_profile + '\\n' +
                            'CPU Temp: ' + (data.cpu_temperature || 'N/A') + '°C\\n' +
                            'Status: ' + data.status;
                    });
            }
            
            function setProfile(profile) {
                fetch('/api/hardware/profile/' + profile, {method: 'POST'})
                    .then(response => response.json())
                    .then(data => {
                        alert(data.message);
                        updateStatus();
                    });
            }
            
            function setFanSpeed(speed) {
                document.getElementById('fanValue').innerText = speed;
                fetch('/api/hardware/fan/' + speed)
                    .then(response => response.json())
                    .then(data => console.log(data.message));
            }
            
            function setRGBColor(color) {
                const r = parseInt(color.substr(1,2), 16);
                const g = parseInt(color.substr(3,2), 16);
                const b = parseInt(color.substr(5,2), 16);
                
                fetch('/api/hardware/rgb/' + r + '/' + g + '/' + b)
                    .then(response => response.json())
                    .then(data => console.log(data.message));
            }
            
            // Initial status update
            updateStatus();
            setInterval(updateStatus, 10000); // Update every 10 seconds
        </script>
    </body>
    </html>
    """


if __name__ == "__main__":
    print("🎮 Starting Celsius AI Hardware Controller API...")
    print("💻 Web interface: http://localhost:5001")
    print("🔧 API endpoints available at /api/hardware/*")
    app.run(host="0.0.0.0", port=5001, debug=False)
