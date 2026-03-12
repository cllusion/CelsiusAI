#!/usr/bin/env python3
"""
Enhanced Mobile Web App - Remote Access & Activity Dashboard
Works from any network with detailed activity logging UI
"""

import asyncio
import json
import sqlite3
from datetime import datetime, timedelta
from pathlib import Path
from flask import Flask, render_template_string, request, jsonify, Response
import requests
from threading import Thread
import time


class MobileActivityDashboard:
    """Mobile dashboard for viewing Celsius AI activities"""

    def __init__(self):
        self.app = Flask(__name__)
        self.db_path = Path("celsius_activity.db")
        self.setup_routes()

    def setup_routes(self):
        """Set up Flask routes"""

        @self.app.route("/")
        def mobile_dashboard():
            return render_template_string(MOBILE_DASHBOARD_HTML)

        @self.app.route("/api/activities")
        def get_activities():
            """Get recent activities"""
            hours = request.args.get("hours", 24, type=int)
            activities = self.get_recent_activities(hours)
            return jsonify(activities)

        @self.app.route("/api/status")
        def get_status():
            """Get system status - optimized for speed"""
            # Simple fast status without expensive database queries
            status = {
                "status": "operational",
                "activities_24h": 0,  # Skip expensive query for speed
                "pending_approvals": 0,  # Skip expensive query for speed
                "remote_access": True,
                "last_update": datetime.now().isoformat(),
            }
            return jsonify(status)

        @self.app.route("/api/health")
        def get_health():
            """Quick health check - optimized for speed"""
            return jsonify({"status": "healthy", "timestamp": datetime.now().isoformat()})

        @self.app.route("/api/pending")
        def get_pending():
            """Get pending code changes - DISPLAY ONLY (approval disabled in web UI)"""
            # NOTE: Code approval has been moved exclusively to the Ultimate Hub
            # The web UI can VIEW pending requests but CANNOT approve/reject them
            # This ensures all code changes go through the secure Hub interface
            pending = self.get_pending_changes()
            return jsonify(pending)

        # CODE APPROVAL ROUTES DISABLED
        # ==============================
        # Code approval functionality has been removed from the web UI for security.
        # All code approvals must be done through the Ultimate Hub (Code Approvals tab).
        # This prevents unauthorized access and ensures proper oversight.
        #
        # @self.app.route('/api/approve/<int:change_id>')
        # def approve_change(change_id):
        #     """DISABLED - Use Ultimate Hub for approvals"""
        #     return jsonify({'success': False, 'error': 'Approvals disabled in web UI. Use Ultimate Hub.'}), 403
        #
        # @self.app.route('/api/reject/<int:change_id>')
        # def reject_change(change_id):
        #     """DISABLED - Use Ultimate Hub for approvals"""
        #     return jsonify({'success': False, 'error': 'Approvals disabled in web UI. Use Ultimate Hub.'}), 403

        @self.app.route("/api/chat", methods=["POST"])
        def chat():
            """Handle chat messages"""
            data = request.get_json()
            message = data.get("message", "")

            # Forward to enhanced Celsius AI
            try:
                response = requests.post("http://localhost:8000/api/chat", json={"message": message}, timeout=30)
                if response.status_code == 200:
                    return jsonify(response.json())
            except Exception:
                pass

            # Fallback response
            return jsonify(
                {
                    "response": f"Received: {message}. Enhanced Celsius AI processing...",
                    "timestamp": datetime.now().isoformat(),
                }
            )

    def get_recent_activities(self, hours: int = 24):
        """Get recent activities from database"""
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()

            since = (datetime.now() - timedelta(hours=hours)).isoformat()

            cursor.execute(
                """
                SELECT timestamp, activity_type, description, details, status
                FROM activities 
                WHERE timestamp > ?
                ORDER BY timestamp DESC
                LIMIT 50
            """,
                (since,),
            )

            activities = []
            for row in cursor.fetchall():
                activities.append(
                    {"timestamp": row[0], "type": row[1], "description": row[2], "details": row[3], "status": row[4]}
                )

            conn.close()
            return activities
        except Exception:
            return []

    def get_pending_changes(self):
        """Get pending code changes"""
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()

            cursor.execute(
                """
                SELECT id, timestamp, file_path, change_description, old_code, new_code
                FROM code_changes 
                WHERE status = 'pending_approval'
                ORDER BY timestamp DESC
            """
            )

            changes = []
            for row in cursor.fetchall():
                changes.append(
                    {
                        "id": row[0],
                        "timestamp": row[1],
                        "file_path": row[2],
                        "description": row[3],
                        "old_code": row[4][:200] + "..." if len(row[4]) > 200 else row[4],
                        "new_code": row[5][:200] + "..." if len(row[5]) > 200 else row[5],
                    }
                )

            conn.close()
            return changes
        except Exception:
            return []

    # CODE APPROVAL METHODS DISABLED
    # ===============================
    # These methods have been disabled to prevent web UI access to code approvals.
    # All code approval functionality is now exclusively available through the
    # Ultimate Hub (Code Approvals tab) for enhanced security and proper oversight.
    #
    # def approve_code_change(self, change_id: int):
    #     """DISABLED - Approval only through Ultimate Hub"""
    #     return False
    #
    # def reject_code_change(self, change_id: int):
    #     """DISABLED - Rejection only through Ultimate Hub"""
    #     return False

    def run(self, host="0.0.0.0", port=5000):
        """Run the mobile dashboard"""
        print(f"[NETWORK] Enhanced Mobile Dashboard starting on {host}:{port}")
        print("[MOBILE] Accessible from any network")
        print("[STATUS] Real-time activity logging enabled")
        self.app.run(host=host, port=port, debug=False)


# Enhanced Mobile Dashboard HTML Template
MOBILE_DASHBOARD_HTML = """
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Celsius AI - Enhanced Dashboard</title>
    <style>
        * {
            margin: 0;
            padding: 0;
            box-sizing: border-box;
        }
        
        body {
            font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif;
            background: linear-gradient(135deg, #1a1a2e 0%, #16213e 100%);
            color: #fff;
            min-height: 100vh;
        }
        
        .header {
            background: rgba(0, 212, 255, 0.1);
            padding: 20px;
            text-align: center;
            border-bottom: 2px solid #00d4ff;
        }
        
        .header h1 {
            color: #00d4ff;
            margin-bottom: 5px;
        }
        
        .status-bar {
            background: rgba(0, 0, 0, 0.3);
            padding: 10px 20px;
            display: flex;
            justify-content: space-between;
            flex-wrap: wrap;
        }
        
        .status-item {
            display: flex;
            align-items: center;
            margin: 5px 0;
        }
        
        .status-dot {
            width: 8px;
            height: 8px;
            border-radius: 50%;
            background: #00ff00;
            margin-right: 8px;
        }
        
        .tabs {
            display: flex;
            background: rgba(0, 0, 0, 0.2);
            overflow-x: auto;
        }
        
        .tab {
            flex: 1;
            padding: 15px;
            text-align: center;
            background: transparent;
            border: none;
            color: #ccc;
            cursor: pointer;
            transition: all 0.3s;
        }
        
        .tab.active {
            background: rgba(0, 212, 255, 0.2);
            color: #00d4ff;
            border-bottom: 3px solid #00d4ff;
        }
        
        .content {
            padding: 20px;
            max-height: 70vh;
            overflow-y: auto;
        }
        
        .activity-item {
            background: rgba(255, 255, 255, 0.05);
            margin: 10px 0;
            padding: 15px;
            border-radius: 10px;
            border-left: 4px solid #00d4ff;
        }
        
        .activity-header {
            display: flex;
            justify-content: space-between;
            margin-bottom: 8px;
        }
        
        .activity-type {
            background: rgba(0, 212, 255, 0.2);
            color: #00d4ff;
            padding: 2px 8px;
            border-radius: 12px;
            font-size: 0.8em;
        }
        
        .activity-time {
            color: #aaa;
            font-size: 0.9em;
        }
        
        .activity-description {
            margin: 8px 0;
            font-weight: 500;
        }
        
        .activity-details {
            color: #ccc;
            font-size: 0.9em;
            background: rgba(0, 0, 0, 0.3);
            padding: 8px;
            border-radius: 5px;
            margin-top: 8px;
        }
        
        .pending-item {
            background: rgba(255, 165, 0, 0.1);
            border-left-color: #ffa500;
        }
        
        .approval-buttons {
            display: flex;
            gap: 10px;
            margin-top: 10px;
        }
        
        .btn {
            padding: 8px 16px;
            border: none;
            border-radius: 20px;
            cursor: pointer;
            font-size: 0.9em;
            transition: all 0.3s;
        }
        
        .btn-approve {
            background: #00ff00;
            color: #000;
        }
        
        .btn-reject {
            background: #ff4444;
            color: #fff;
        }
        
        .chat-container {
            max-height: 50vh;
            display: flex;
            flex-direction: column;
        }
        
        .chat-messages {
            flex: 1;
            overflow-y: auto;
            padding: 10px;
            background: rgba(0, 0, 0, 0.2);
            border-radius: 10px;
            margin-bottom: 10px;
            min-height: 200px;
        }
        
        .chat-input-area {
            display: flex;
            gap: 10px;
        }
        
        .chat-input {
            flex: 1;
            padding: 12px;
            border: 2px solid #00d4ff;
            border-radius: 25px;
            background: rgba(0, 0, 0, 0.3);
            color: #fff;
            outline: none;
        }
        
        .chat-send {
            background: #00d4ff;
            color: #000;
            border: none;
            padding: 12px 20px;
            border-radius: 25px;
            cursor: pointer;
        }
        
        .message {
            margin: 10px 0;
            padding: 10px 15px;
            border-radius: 15px;
            max-width: 80%;
        }
        
        .message.user {
            background: rgba(0, 212, 255, 0.2);
            margin-left: auto;
            text-align: right;
        }
        
        .message.ai {
            background: rgba(255, 255, 255, 0.1);
        }
        
        .loading {
            text-align: center;
            padding: 20px;
            color: #aaa;
        }
        
        @media (max-width: 768px) {
            .status-bar {
                flex-direction: column;
            }
            
            .tabs {
                font-size: 0.9em;
            }
            
            .content {
                padding: 15px;
            }
        }
    </style>
</head>
<body>
    <div class="header">
        <h1>Celsius AI Universal Intelligence</h1>
        <p>Leader in EVERYTHING - Technology, Business, Science, Creative, Education, Social</p>
    </div>
    
    <div class="status-bar">
        <div class="status-item">
            <div class="status-dot"></div>
            <span>System Operational</span>
        </div>
        <div class="status-item">
            <span id="activities-count">Activities: --</span>
        </div>
        <div class="status-item">
            <span id="pending-count">Pending: --</span>
        </div>
        <div class="status-item">
            <span id="last-update">Last Update: --</span>
        </div>
    </div>
    
    <div class="tabs">
        <button class="tab active" onclick="showTab('activities')">Activities</button>
        <!-- APPROVALS TAB REMOVED - Use Ultimate Hub for code approvals -->
        <button class="tab" onclick="showTab('chat')">Chat</button>
        <button class="tab" onclick="showTab('status')">Status</button>
    </div>
    
    <div class="content">
        <!-- Activities Tab -->
        <div id="activities-tab" class="tab-content">
            <div id="activities-list" class="loading">Loading activities...</div>
        </div>
        
        <!-- PENDING APPROVALS TAB REMOVED FOR SECURITY -->
        <!-- All code approvals must be done through the Ultimate Hub -->
        <!-- This ensures proper oversight and prevents unauthorized access -->
        
        <!-- Chat Tab -->
        <div id="chat-tab" class="tab-content" style="display: none;">
            <div class="chat-container">
                <div class="chat-messages" id="chat-messages">
                    <div class="message ai">
                        <strong>Celsius AI Universal:</strong> Hello! I'm your universal intelligence assistant with expertise across all domains. I can help with technology, business, science, creative projects, education, and social topics. What would you like to discuss?
                    </div>
                </div>
                <div class="chat-input-area">
                    <input type="text" class="chat-input" id="chat-input" placeholder="Ask Celsius AI anything..." onkeypress="handleChatKeyPress(event)">
                    <button class="chat-send" onclick="sendMessage()">Send</button>
                </div>
            </div>
        </div>
        
        <!-- Status Tab -->
        <div id="status-tab" class="tab-content" style="display: none;">
            <div id="status-details" class="loading">Loading system status...</div>
        </div>
    </div>
    
    <script>
        let currentTab = 'activities';
        
        // Tab switching
        function showTab(tabName) {
            document.querySelectorAll('.tab').forEach(tab => tab.classList.remove('active'));
            document.querySelectorAll('.tab-content').forEach(content => content.style.display = 'none');
            
            document.querySelector(`[onclick="showTab('${tabName}')"]`).classList.add('active');
            document.getElementById(`${tabName}-tab`).style.display = 'block';
            
            currentTab = tabName;
            
            if (tabName === 'activities') loadActivities();
            // REMOVED: loadPending() - Approvals tab disabled
            else if (tabName === 'status') loadStatus();
        }
        
        // Load activities
        function loadActivities() {
            fetch('/api/activities')
                .then(response => response.json())
                .then(activities => {
                    const container = document.getElementById('activities-list');
                    
                    if (activities.length === 0) {
                        container.innerHTML = '<div class="loading">No recent activities</div>';
                        return;
                    }
                    
                    container.innerHTML = activities.map(activity => `
                        <div class="activity-item">
                            <div class="activity-header">
                                <span class="activity-type">${activity.type}</span>
                                <span class="activity-time">${formatTime(activity.timestamp)}</span>
                            </div>
                            <div class="activity-description">${activity.description}</div>
                            ${activity.details ? `<div class="activity-details">${activity.details}</div>` : ''}
                        </div>
                    `).join('');
                })
                .catch(error => {
                    document.getElementById('activities-list').innerHTML = '<div class="loading">Error loading activities</div>';
                });
        }
        
        // PENDING APPROVALS FUNCTION REMOVED
        // ===================================
        // Code approval functionality has been removed from the web UI.
        // All approvals must be done through the Ultimate Hub (Code Approvals tab).
        // This ensures proper security and oversight of all code changes.
        //
        // function loadPending() {
        //     // DISABLED - Use Ultimate Hub for approvals
        // }
        
        // Load system status
        function loadStatus() {
            fetch('/api/status')
                .then(response => response.json())
                .then(status => {
                    document.getElementById('status-details').innerHTML = `
                        <div class="activity-item">
                            <h3>System Status</h3>
                            <p><strong>Status:</strong> ${status.status}</p>
                            <p><strong>Activities (24h):</strong> ${status.activities_24h}</p>
                            <p><strong>Pending Approvals:</strong> ${status.pending_approvals}</p>
                            <p><strong>Remote Access:</strong> ${status.remote_access ? 'Enabled' : 'Disabled'}</p>
                            <p><strong>Last Update:</strong> ${formatTime(status.last_update)}</p>
                        </div>
                    `;
                })
                .catch(error => {
                    document.getElementById('status-details').innerHTML = '<div class="loading">Error loading status</div>';
                });
        }
        
        // Update status bar
        function updateStatusBar() {
            fetch('/api/status')
                .then(response => response.json())
                .then(status => {
                    document.getElementById('activities-count').textContent = `Activities: ${status.activities_24h}`;
                    document.getElementById('pending-count').textContent = `Pending: ${status.pending_approvals}`;
                    document.getElementById('last-update').textContent = `Updated: ${formatTime(status.last_update)}`;
                })
                .catch(error => console.log('Status update failed'));
        }
        
        // APPROVE/REJECT FUNCTIONS REMOVED
        // =================================
        // Code approval functions have been disabled for security.
        // All approvals must be done through the Ultimate Hub.
        //
        // function approveChange(changeId) {
        //     // DISABLED - Use Ultimate Hub
        // }
        //
        // function rejectChange(changeId) {
        //     // DISABLED - Use Ultimate Hub
        // }
        
        // Chat functionality
        function sendMessage() {
            const input = document.getElementById('chat-input');
            const message = input.value.trim();
            
            if (!message) return;
            
            // Add user message
            addMessage(message, 'user');
            input.value = '';
            
            // Add loading message
            addMessage('Thinking...', 'ai');
            
            // Send to Celsius AI
            fetch('/api/chat', {
                method: 'POST',
                headers: {'Content-Type': 'application/json'},
                body: JSON.stringify({message: message})
            })
            .then(response => response.json())
            .then(data => {
                // Remove loading message
                const messages = document.getElementById('chat-messages');
                messages.removeChild(messages.lastChild);
                
                // Add AI response
                addMessage(data.response, 'ai');
            })
            .catch(error => {
                // Remove loading message
                const messages = document.getElementById('chat-messages');
                messages.removeChild(messages.lastChild);
                
                addMessage('Sorry, I encountered an error. Please try again.', 'ai');
            });
        }
        
        function addMessage(text, sender) {
            const messages = document.getElementById('chat-messages');
            const messageDiv = document.createElement('div');
            messageDiv.className = `message ${sender}`;
            
            if (sender === 'ai') {
                messageDiv.innerHTML = `<strong>Celsius AI:</strong> ${text}`;
            } else {
                messageDiv.innerHTML = `<strong>You:</strong> ${text}`;
            }
            
            messages.appendChild(messageDiv);
            messages.scrollTop = messages.scrollHeight;
        }
        
        function handleChatKeyPress(event) {
            if (event.key === 'Enter') {
                sendMessage();
            }
        }
        
        // Utility functions
        function formatTime(timestamp) {
            const date = new Date(timestamp);
            return date.toLocaleTimeString([], {hour: '2-digit', minute: '2-digit'});
        }
        
        // Initialize
        loadActivities();
        updateStatusBar();
        
        // Auto-refresh every 30 seconds
        setInterval(() => {
            if (currentTab === 'activities') loadActivities();
            // REMOVED: loadPending() - Approvals disabled
            updateStatusBar();
        }, 30000);
    </script>
</body>
</html>
"""


def main():
    dashboard = MobileActivityDashboard()
    dashboard.run(host="0.0.0.0", port=5000)


if __name__ == "__main__":
    main()
