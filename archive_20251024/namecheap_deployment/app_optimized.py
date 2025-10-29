#!/usr/bin/env python3
"""
Celsius AI - cPanel Optimized Startup
Simplified version for environments with limited dependencies
"""

import sys
import os

# Add current directory to Python path
sys.path.append(os.path.dirname(__file__))

try:
    # Try to import the simplified version
    from celsius_simplified import application, celsius

    # This is the WSGI application for cPanel
    if __name__ == "__main__":
        print("Celsius AI - Simplified Version Starting...")
        application.run(host="0.0.0.0", port=5000, debug=False)

except ImportError as e:
    # Fallback to basic Flask app
    print(f"Import error: {e}")

    try:
        from flask import Flask, jsonify

        app = Flask(__name__)

        @app.route("/")
        def index():
            return """
            <html>
            <head><title>Celsius AI</title></head>
            <body style="font-family: Arial; background: linear-gradient(135deg, #667eea, #764ba2); color: white; text-align: center; padding: 50px;">
                <h1>🌡️ Celsius AI</h1>
                <h2>Universal Intelligence System</h2>
                <p>System is initializing... Full functionality loading.</p>
                <div style="background: rgba(76, 175, 80, 0.3); padding: 20px; border-radius: 10px; margin: 20px;">
                    Status: Starting Up | Python: 3.11.13 | Domain: cllusion.me
                </div>
            </body>
            </html>
            """

        @app.route("/api/status")
        def status():
            return jsonify({"status": "initializing", "message": "Celsius AI starting up", "python_version": "3.11.13"})

        # WSGI application
        application = app

        if __name__ == "__main__":
            app.run(host="0.0.0.0", port=5000, debug=False)

    except ImportError:
        # Ultimate fallback - minimal Python server
        import http.server
        import socketserver

        class CelsiusHandler(http.server.SimpleHTTPRequestHandler):
            def do_GET(self):
                self.send_response(200)
                self.send_header("Content-type", "text/html")
                self.end_headers()

                html = """
                <html>
                <head><title>Celsius AI</title></head>
                <body style="font-family: Arial; background: #667eea; color: white; text-align: center; padding: 50px;">
                    <h1>🌡️ Celsius AI</h1>
                    <p>Universal Intelligence System - Minimal Mode</p>
                    <p>Please install Flask for full functionality</p>
                </body>
                </html>
                """
                self.wfile.write(html.encode())

        if __name__ == "__main__":
            with socketserver.TCPServer(("", 5000), CelsiusHandler) as httpd:
                print("Celsius AI - Minimal server starting...")
                httpd.serve_forever()
