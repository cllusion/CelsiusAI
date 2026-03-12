#!/usr/bin/env python3
"""
Celsius AI - Main System Launcher
Complete integration of all Celsius AI components including web learning
"""

import os
import sys
import time
import threading
from datetime import datetime
import json
from pathlib import Path

# Add project root to path for imports
PROJECT_ROOT = Path(__file__).resolve().parents[2]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.append(str(PROJECT_ROOT))

from src.utils.logger import setup_logger

# Apply database migrations at startup (idempotent — safe to call every run)
try:
    from src.utils.db_migrations import apply_all_migrations
    apply_all_migrations(PROJECT_ROOT / "data")
except Exception as _mig_err:
    print(f"Warning: DB migrations failed: {_mig_err}")

# Import CelsiusUltimateHub if it exists, otherwise create a placeholder
try:
    from src.hub.celsius_ultimate_hub import CelsiusUltimateHub
except ImportError:

    class CelsiusUltimateHub:
        def __init__(self):
            print("Warning: src.hub.celsius_ultimate_hub not found. Using placeholder.")

        def run(self):
            print("Placeholder Hub running.")


# Import hardware controller
try:
    from src.hardware.celsius_hardware_controller import CelsiusHardwareController

    HARDWARE_AVAILABLE = True
except ImportError:
    HARDWARE_AVAILABLE = False
    print("Warning: Hardware controller not available")

from src.learning.celsius_web_learning_integration import CelsiusWebLearningIntegration
from src.security.celsius_auth import CelsiusAuth


class CelsiusAIMain:
    """Main Celsius AI system with integrated web learning"""

    def __init__(self):
        self.logger = setup_logger("CelsiusAI", "logs/celsius_main.log")
        self.system_active = False
        self.components = {
            "system_integration": None,
            "server_hub": None,
            "power_manager": None,
            "process_trainer": None,
            "collaborative_engine": None,
            "web_learning": None,
            "authentication": None,
            "hardware_controller": None,
        }

        self.web_learning_active = False
        self.hardware_controller = None

    def display_startup_banner(self):
        """Display Celsius AI startup banner"""
        print()
        print("=" * 70)
        print("                    CELSIUS AI SYSTEM")
        print("              Personal Cybersecurity Defense")
        print("          With Integrated Web Learning Capabilities")
        print("=" * 70)
        print()
        print("Starting Celsius AI with full integration...")
        print()

    def initialize_core_components(self):
        """Initialize all core Celsius AI components"""
        self.logger.info("Initializing core components...")

        try:
            # Authentication System
            self.logger.info("  Loading authentication...")
            self.components["authentication"] = CelsiusAuth()
            self.logger.info("    Authentication system: READY")

        except Exception as e:
            self.logger.error(f"    Authentication system: ERROR - {e}", exc_info=True)

        # Hardware Controller
        if HARDWARE_AVAILABLE:
            try:
                self.logger.info("  Loading hardware controller...")
                self.hardware_controller = CelsiusHardwareController()
                # Initialize hardware controller in a dedicated thread running an asyncio loop
                import threading

                threading.Thread(
                    target=lambda: __import__("asyncio").run(self.hardware_controller.initialize()), daemon=True
                ).start()
                self.components["hardware_controller"] = self.hardware_controller
                self.logger.info("    Hardware controller: READY")
            except Exception as e:
                self.logger.error(f"    Hardware controller: ERROR - {e}", exc_info=True)
        else:
            self.logger.warning("    Hardware controller: NOT AVAILABLE")

    def initialize_web_learning(self):
        """Initialize web learning integration"""
        self.logger.info("Initializing web learning capabilities...")

        try:
            self.components["web_learning"] = CelsiusWebLearningIntegration()
            self.logger.info("    Web learning integration: READY")

            # Show web learning status
            status = self.components["web_learning"].get_learning_status()
            self.logger.info(f"    Learning active: {status['learning_active']}")
            self.logger.info(f"    Content learned: {status['total_content_learned']} articles")
            self.logger.info(f"    Insights generated: {status['total_insights']} insights")

            return True

        except Exception as e:
            self.logger.error(f"    Web learning integration: ERROR - {e}", exc_info=True)
            return False

    def start_server_hub(self):
        """Start the Ultimate Server Hub"""
        try:
            self.logger.info("Starting Ultimate Server Hub...")

            def run_server_hub():
                try:
                    hub_app = CelsiusUltimateHub()
                    # This assumes the hub has a 'run' method or similar entry point.
                    # If the hub is a GUI application, it might need to be run differently.
                    if hasattr(hub_app, "run") and callable(getattr(hub_app, "run")):
                        hub_app.run()
                    else:
                        self.logger.warning("Ultimate Hub does not have a 'run' method. Instantiating only.")

                except Exception as e:
                    self.logger.error(f"Error running Ultimate Hub: {e}", exc_info=True)

            hub_thread = threading.Thread(target=run_server_hub, daemon=True)
            hub_thread.start()

            self.logger.info("    Ultimate Hub: STARTED (running in background)")
            return True

        except Exception as e:
            self.logger.error(f"    Ultimate Hub: ERROR - {e}", exc_info=True)
            return False

    def show_system_status(self):
        """Show current system status"""
        print("\nCELSIUS AI SYSTEM STATUS")
        print("=" * 40)

        # Core components status
        print("Core Components:")
        for component, instance in self.components.items():
            status = "ACTIVE" if instance is not None else "INACTIVE"
            print(f"  {component.replace('_', ' ').title()}: {status}")

        # Web learning specific status
        if self.components["web_learning"]:
            print("\nWeb Learning Status:")
            status = self.components["web_learning"].get_learning_status()
            print(f"  Learning Active: {status['learning_active']}")
            print(f"  Content Database: {status['total_content_learned']} articles")
            print(f"  Insights Generated: {status['total_insights']} insights")
            print(f"  Learning Interval: {status['settings']['learning_interval_hours']} hours")

        # System integration status
        if self.components["system_integration"]:
            try:
                integration_status = self.components["system_integration"].get_status()
                print(f"\nSystem Integration:")
                print(f"  Status: {integration_status.get('status', 'Unknown')}")
                print(f"  Processes Monitored: {len(integration_status.get('processes', []))}")
            except Exception:
                print(f"  System Integration: Status unavailable")

        print(f"\nSystem Active: {self.system_active}")
        print(f"Current Time: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")

    def show_web_learning_insights(self):
        """Show recent web learning insights"""
        if not self.components["web_learning"]:
            print("Web learning not available")
            return

        print("\nRECENT WEB LEARNING INSIGHTS")
        print("=" * 40)

        insights = self.components["web_learning"].get_recent_insights(5)

        if insights:
            for i, insight in enumerate(insights, 1):
                print(f"{i}. Topic: {insight['topic'].title()}")
                print(f"   Confidence: {insight['confidence']:.0%}")
                print(f"   Time: {insight['timestamp']}")
                print(f"   Insight: {insight['insight'][:100]}...")
                print()
        else:
            print("No insights available yet.")
            print("Web learning will generate insights as it processes content.")

    def search_learned_content(self, query):
        """Search through learned content"""
        if not self.components["web_learning"]:
            print("Web learning not available")
            return

        print(f"\nSearching learned content for: '{query}'")
        print("=" * 50)

        results = self.components["web_learning"].search_learned_content(query)

        if results:
            for i, result in enumerate(results, 1):
                print(f"{i}. {result['title']}")
                print(f"   Topic: {result['topic']} | Quality: {result['quality']:.2f}")
                print(f"   URL: {result['url']}")
                print(f"   Summary: {result['summary']}")
                print()
        else:
            print("No results found.")

    def toggle_web_learning(self):
        """Toggle web learning on/off"""
        if not self.components["web_learning"]:
            print("Web learning not available")
            return

        status = self.components["web_learning"].get_learning_status()

        if status["learning_active"]:
            self.components["web_learning"].stop_learning()
            print("Web learning stopped")
        else:
            self.components["web_learning"].start_learning_process()
            print("Web learning started")

    async def control_rgb_lights(self, command):
        """Control RGB lighting through natural language"""
        if not self.hardware_controller:
            print("Hardware controller not available")
            return

        command = command.lower()

        # Color mappings
        colors = {
            "red": (255, 0, 0),
            "green": (0, 255, 0),
            "blue": (0, 0, 255),
            "yellow": (255, 255, 0),
            "purple": (128, 0, 128),
            "cyan": (0, 255, 255),
            "orange": (255, 165, 0),
            "pink": (255, 192, 203),
            "white": (255, 255, 255),
            "off": (0, 0, 0),
            "black": (0, 0, 0),
        }

        try:
            if "off" in command or "turn off" in command:
                await self.hardware_controller.set_rgb_color("all", 0, 0, 0)
                print("🔴 All RGB lights turned OFF")

            elif "motherboard" in command or "mobo" in command:
                # Control motherboard specifically
                for color_name, (r, g, b) in colors.items():
                    if color_name in command:
                        await self.hardware_controller.set_rgb_color("2", r, g, b)
                        print(f"🎨 Motherboard RGB set to {color_name.upper()}")
                        return

            elif "all" in command or "everything" in command:
                # Control all devices
                for color_name, (r, g, b) in colors.items():
                    if color_name in command:
                        await self.hardware_controller.set_rgb_color("all", r, g, b)
                        print(f"🌈 All RGB devices set to {color_name.upper()}")
                        return

            else:
                # Default to motherboard for single color commands
                for color_name, (r, g, b) in colors.items():
                    if color_name in command:
                        await self.hardware_controller.set_rgb_color("2", r, g, b)
                        print(f"🎨 Motherboard RGB set to {color_name.upper()}")
                        return

                print("Color not recognized. Available colors: " + ", ".join(colors.keys()))

        except Exception as e:
            print(f"RGB control error: {e}")

    def control_rgb_sync(self, command):
        """Synchronous wrapper for RGB control"""
        import asyncio

        try:
            asyncio.run(self.control_rgb_lights(command))
        except Exception as e:
            print(f"RGB control failed: {e}")

    async def control_fans(self, command):
        """Control system fans"""
        if not self.hardware_controller:
            print("Hardware controller not available")
            return

        command = command.lower()

        try:
            if "max" in command or "full" in command or "100" in command:
                await self.hardware_controller.set_fan_speed("cpu", 100)
                print("🌪️ CPU fan set to MAXIMUM speed")

            elif "high" in command or "80" in command:
                await self.hardware_controller.set_fan_speed("cpu", 80)
                print("💨 CPU fan set to HIGH speed")

            elif "medium" in command or "normal" in command or "50" in command:
                await self.hardware_controller.set_fan_speed("cpu", 50)
                print("🌬️ CPU fan set to MEDIUM speed")

            elif "low" in command or "quiet" in command or "30" in command:
                await self.hardware_controller.set_fan_speed("cpu", 30)
                print("💨 CPU fan set to LOW speed")

            elif "auto" in command or "automatic" in command:
                await self.hardware_controller.auto_adjust_by_temperature()
                print("🤖 Fan control set to AUTOMATIC based on temperature")

            else:
                print("Fan command not recognized. Try: max, high, medium, low, auto")

        except Exception as e:
            print(f"Fan control error: {e}")

    def control_fans_sync(self, command):
        """Synchronous wrapper for fan control"""
        import asyncio

        try:
            asyncio.run(self.control_fans(command))
        except Exception as e:
            print(f"Fan control failed: {e}")

    def launch_dashboard(self):
        """Launch monitoring dashboard"""
        self.logger.info("Dashboard functionality now integrated into Ultimate Hub.")
        self.logger.info("Launch Ultimate Hub to access system monitoring dashboard.")

    def show_main_menu(self):
        """Show main menu options"""
        print("\nCELSIUS AI COMMAND MENU")
        print("=" * 30)
        print("System Commands:")
        print("  status     - Show system status")
        print("  hub        - Launch Server Hub")
        print("  dashboard  - Launch monitoring dashboard")
        print()
        print("Hardware Control Commands:")
        print("  red        - Set RGB lights to red")
        print("  blue       - Set RGB lights to blue")
        print("  green      - Set RGB lights to green")
        print("  purple     - Set RGB lights to purple")
        print("  yellow     - Set RGB lights to yellow")
        print("  orange     - Set RGB lights to orange")
        print("  white      - Set RGB lights to white")
        print("  lights off - Turn off all RGB lights")
        print("  rgb [color]- Set RGB to any color")
        print("  fan high   - Set fans to high speed")
        print("  fan low    - Set fans to low speed")
        print("  fan auto   - Set automatic fan control")
        print()
        print("Web Learning Commands:")
        print("  insights   - Show recent learning insights")
        print("  search     - Search learned content")
        print("  webtoggle  - Toggle web learning on/off")
        print("  webstatus  - Show web learning status")
        print()
        print("General Commands:")
        print("  help       - Show this menu")
        print("  quit       - Exit Celsius AI")
        print()

    def run_interactive_mode(self):
        """Run interactive command mode"""
        self.show_main_menu()

        while self.system_active:
            try:
                command = input("Celsius AI> ").strip().lower()

                if command == "status":
                    self.show_system_status()

                elif command == "hub":
                    self.start_server_hub()

                elif command == "dashboard":
                    self.launch_dashboard()

                elif command == "insights":
                    self.show_web_learning_insights()

                elif command == "search":
                    query = input("Enter search query: ").strip()
                    if query:
                        self.search_learned_content(query)
                    else:
                        print("No search query provided")

                elif command == "webtoggle":
                    self.toggle_web_learning()

                elif command == "webstatus":
                    if self.components["web_learning"]:
                        print(self.components["web_learning"].get_learning_summary())
                    else:
                        print("Web learning not available")

                elif command.startswith("rgb ") or command.startswith("lights "):
                    # RGB control commands
                    rgb_command = command.replace("rgb ", "").replace("lights ", "")
                    self.control_rgb_sync(rgb_command)

                elif command.startswith("fan ") or command.startswith("fans "):
                    # Fan control commands
                    fan_command = command.replace("fan ", "").replace("fans ", "")
                    self.control_fans_sync(fan_command)

                elif command in ["rgb red", "lights red", "red lights", "red"]:
                    self.control_rgb_sync("red")

                elif command in ["rgb blue", "lights blue", "blue lights", "blue"]:
                    self.control_rgb_sync("blue")

                elif command in ["rgb green", "lights green", "green lights", "green"]:
                    self.control_rgb_sync("green")

                elif command in ["rgb off", "lights off", "turn off lights", "lights out"]:
                    self.control_rgb_sync("off")

                elif command in ["rgb purple", "lights purple", "purple lights", "purple"]:
                    self.control_rgb_sync("purple")

                elif command in ["rgb yellow", "lights yellow", "yellow lights", "yellow"]:
                    self.control_rgb_sync("yellow")

                elif command in ["rgb orange", "lights orange", "orange lights", "orange"]:
                    self.control_rgb_sync("orange")

                elif command in ["rgb white", "lights white", "white lights", "white"]:
                    self.control_rgb_sync("white")

                elif command == "help":
                    self.show_main_menu()

                elif command in ["quit", "exit"]:
                    break

                else:
                    print(f"Unknown command: {command}")
                    print("Type 'help' for available commands")

            except KeyboardInterrupt:
                print("\nShutting down...")
                break
            except EOFError:
                print("\nGoodbye!")
                break
            except Exception as e:
                print(f"Error: {str(e)}")

    def start_system(self):
        """Start the complete Celsius AI system"""
        self.display_startup_banner()

        # Initialize all components
        self.initialize_core_components()
        web_learning_ok = self.initialize_web_learning()

        # Start background services
        print("\nStarting background services...")

        # Start server hub
        self.start_server_hub()

        # System is now active
        self.system_active = True

        print("\n" + "=" * 70)
        print("                CELSIUS AI SYSTEM READY")
        print("=" * 70)
        print()
        print("All components loaded and background services started.")

        if web_learning_ok:
            print("Web learning is ACTIVE - Celsius is learning from the internet!")
            print("Use 'insights' to see what Celsius has learned recently.")

        print("Use 'help' to see available commands.")
        print("Use 'status' to check system health.")
        print()

        # Start interactive mode
        self.run_interactive_mode()

        # Cleanup on exit
        print("Shutting down Celsius AI...")
        if self.components["web_learning"]:
            self.components["web_learning"].stop_learning()
        print("Goodbye!")


def main():
    """Main entry point"""
    try:
        celsius = CelsiusAIMain()
        celsius.start_system()
    except Exception as e:
        print(f"Fatal error starting Celsius AI: {str(e)}")
        print("Check that all required components are installed and configured.")


if __name__ == "__main__":
    main()
