#!/usr/bin/env python3
"""
Celsius AI - cPanel Startup Script
This is the main entry point for cPanel hosting
"""
import sys
import os

# Add current directory to path
sys.path.append(os.path.dirname(__file__))

# Import your Celsius AI components
try:
    from enhanced_mobile_dashboard import MobileActivityDashboard
except ImportError:
    # Fallback if mobile dashboard not available
    from flask import Flask

    app = Flask(__name__)

    @app.route("/")
    def hello():
        return """
        <html>
        <body>
            <h1>Celsius AI</h1>
            <p>Loading... Please wait while the system initializes.</p>
            <script>
                setTimeout(() => {
                    window.location.reload();
                }, 5000);
            </script>
        </body>
        </html>
        """


# Create Flask application
if __name__ == "__main__":
    try:
        # Try to start full dashboard
        dashboard = MobileActivityDashboard()
        application = dashboard.app  # For WSGI

        # Run if called directly
        dashboard.app.run(host="0.0.0.0", port=5000, debug=False)
    except Exception as e:
        # Fallback basic Flask app
        print(f"Error starting full dashboard: {e}")
        app.run(host="0.0.0.0", port=5000, debug=False)

# WSGI application for cPanel
try:
    dashboard = MobileActivityDashboard()
    application = dashboard.app
except:
    from flask import Flask

    application = Flask(__name__)

    @application.route("/")
    def index():
        return "<h1>Celsius AI - Initializing...</h1>"
