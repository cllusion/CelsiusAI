#!/usr/bin/env python3
"""
Celsius AI - Simplified cPanel Version
Optimized for environments with limited dependencies
"""

import os
import sys
import json
from datetime import datetime
import sqlite3
from pathlib import Path

# Try to import Flask, fallback to minimal server if not available
try:
    from flask import Flask, render_template_string, request, jsonify

    FLASK_AVAILABLE = True
    print("Flask 2.0.3 loaded successfully")
except ImportError:
    FLASK_AVAILABLE = False
    print("Flask not available, using fallback server")
    import http.server
    import socketserver
    from urllib.parse import parse_qs, urlparse


class CelsiusAISimplified:
    """Simplified Celsius AI for cPanel deployment"""

    def __init__(self):
        self.db_path = Path("celsius_activity.db")
        self.setup_database()

        # Core responses and patterns
        self.expertise_domains = {
            "technology": "AI/ML, Cybersecurity, Software Development, Cloud Computing, Blockchain",
            "business": "Strategy, Finance, Marketing, Operations, Entrepreneurship",
            "science": "Physics, Chemistry, Biology, Mathematics, Research",
            "creative": "Art, Design, Writing, Music, Innovation",
            "education": "Teaching, Learning, Curriculum, Training",
            "social": "Communication, Leadership, Psychology, Culture",
        }

        self.responses = {
            "greeting": "Hello! I'm Celsius AI, your Universal Intelligence System. I'm a leader in technology, business, science, creative work, education, and social intelligence. How can I help you today?",
            "status": "System operational - Universal Intelligence active across all domains",
            "capabilities": "I excel in 6 major domains: Technology (AI/ML, cybersecurity), Business (strategy, finance), Science (research, analysis), Creative (innovation, design), Education (teaching, learning), and Social intelligence (leadership, communication).",
            "help": "I can assist with any question or challenge across technology, business, science, creative work, education, or social topics. What specific area interests you?",
            "default": "That's an interesting question. As your Universal Intelligence System, I can provide expert guidance on that topic. Could you give me more context about what specifically you'd like to know?",
        }

    def setup_database(self):
        """Initialize the learning database"""
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()

            # Create activities table
            cursor.execute(
                """
                CREATE TABLE IF NOT EXISTS activities (
                    id INTEGER PRIMARY KEY,
                    timestamp TEXT,
                    query TEXT,
                    response TEXT,
                    domain TEXT,
                    user_ip TEXT
                )
            """
            )

            conn.commit()
            conn.close()
        except Exception as e:
            print(f"Database setup error: {e}")

    def log_interaction(self, query, response, domain="general", user_ip=""):
        """Log user interactions for learning"""
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()

            cursor.execute(
                """
                INSERT INTO activities (timestamp, query, response, domain, user_ip)
                VALUES (?, ?, ?, ?, ?)
            """,
                (datetime.now().isoformat(), query, response, domain, user_ip),
            )

            conn.commit()
            conn.close()
        except Exception as e:
            print(f"Logging error: {e}")

    def identify_domain(self, query):
        """Identify the expertise domain for a query"""
        query_lower = query.lower()

        tech_keywords = [
            "ai",
            "software",
            "code",
            "programming",
            "cyber",
            "security",
            "cloud",
            "blockchain",
            "tech",
            "computer",
        ]
        business_keywords = [
            "business",
            "strategy",
            "finance",
            "marketing",
            "sales",
            "entrepreneur",
            "startup",
            "money",
        ]
        science_keywords = ["science", "physics", "chemistry", "biology", "research", "study", "experiment", "analysis"]
        creative_keywords = ["creative", "art", "design", "writing", "music", "innovation", "idea", "brand"]
        education_keywords = ["education", "teaching", "learning", "study", "training", "coaching", "academic"]
        social_keywords = ["social", "leadership", "communication", "team", "culture", "psychology", "relationship"]

        if any(keyword in query_lower for keyword in tech_keywords):
            return "technology"
        elif any(keyword in query_lower for keyword in business_keywords):
            return "business"
        elif any(keyword in query_lower for keyword in science_keywords):
            return "science"
        elif any(keyword in query_lower for keyword in creative_keywords):
            return "creative"
        elif any(keyword in query_lower for keyword in education_keywords):
            return "education"
        elif any(keyword in query_lower for keyword in social_keywords):
            return "social"

        return "general"

    def process_query(self, query, user_ip=""):
        """Process user query and generate response"""
        query_lower = query.lower()
        domain = self.identify_domain(query)

        # Generate response based on query type
        if any(word in query_lower for word in ["hello", "hi", "hey", "greeting"]):
            response = self.responses["greeting"]
        elif any(word in query_lower for word in ["status", "health", "operational"]):
            response = self.responses["status"]
        elif any(word in query_lower for word in ["help", "what can you do", "capabilities"]):
            response = self.responses["capabilities"]
        elif "domain" in query_lower or "expertise" in query_lower:
            domain_info = self.expertise_domains.get(domain, "general intelligence")
            response = f"In the {domain} domain, I specialize in: {domain_info}. What specific aspect would you like to explore?"
        else:
            # Domain-specific response
            domain_expertise = self.expertise_domains.get(domain, "comprehensive analysis")
            response = f"As your Universal Intelligence System, I can help with {domain_expertise}. {self.responses['default']}"

        # Log the interaction
        self.log_interaction(query, response, domain, user_ip)

        return response, domain

    def get_stats(self):
        """Get system statistics"""
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()

            cursor.execute("SELECT COUNT(*) FROM activities")
            total_interactions = cursor.fetchone()[0]

            cursor.execute("SELECT domain, COUNT(*) FROM activities GROUP BY domain")
            domain_stats = dict(cursor.fetchall())

            conn.close()

            return {
                "total_interactions": total_interactions,
                "domain_distribution": domain_stats,
                "status": "operational",
                "last_update": datetime.now().isoformat(),
            }
        except Exception as e:
            return {
                "total_interactions": 0,
                "domain_distribution": {},
                "status": "operational",
                "error": str(e),
                "last_update": datetime.now().isoformat(),
            }


# Flask Application (if available)
if FLASK_AVAILABLE:
    app = Flask(__name__)
    celsius = CelsiusAISimplified()

    @app.route("/")
    def index():
        return render_template_string(MAIN_TEMPLATE)

    @app.route("/api/status")
    def api_status():
        stats = celsius.get_stats()
        return jsonify(stats)

    @app.route("/api/chat", methods=["POST"])
    def api_chat():
        data = request.get_json()
        query = data.get("message", "")
        user_ip = request.remote_addr

        if not query:
            return jsonify({"error": "No message provided"}), 400

        response, domain = celsius.process_query(query, user_ip)

        return jsonify({"response": response, "domain": domain, "timestamp": datetime.now().isoformat()})

    @app.route("/chat")
    def chat_interface():
        return render_template_string(CHAT_TEMPLATE)

    # WSGI application object for cPanel
    application = app

# HTML Templates
MAIN_TEMPLATE = """
<!DOCTYPE html>
<html>
<head>
    <title>Celsius AI - Universal Intelligence System</title>
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <style>
        body { 
            font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            color: white; margin: 0; padding: 20px; min-height: 100vh; 
        }
        .container { max-width: 800px; margin: 0 auto; }
        .header { text-align: center; margin-bottom: 30px; }
        .logo { font-size: 48px; font-weight: bold; margin-bottom: 10px; color: #FFD700; }
        .tagline { font-size: 18px; opacity: 0.9; }
        .status { 
            background: rgba(76, 175, 80, 0.3); padding: 20px; border-radius: 10px; 
            text-align: center; margin: 20px 0; 
        }
        .features { 
            display: grid; grid-template-columns: repeat(auto-fit, minmax(250px, 1fr)); 
            gap: 20px; margin: 30px 0; 
        }
        .feature { 
            background: rgba(255,255,255,0.1); padding: 20px; border-radius: 10px;
            backdrop-filter: blur(10px);
        }
        .feature h3 { margin-top: 0; color: #FFD700; }
        .chat-link { 
            display: block; background: #4CAF50; color: white; padding: 15px 30px;
            text-align: center; border-radius: 25px; text-decoration: none;
            font-weight: bold; margin: 20px auto; max-width: 200px;
        }
        .chat-link:hover { background: #45a049; }
    </style>
</head>
<body>
    <div class="container">
        <div class="header">
            <div class="logo">🌡️ Celsius AI</div>
            <div class="tagline">Universal Intelligence System - Leader in Everything</div>
        </div>
        
        <div class="status">
            🚀 System Operational | Interactive Mode Active | Ready for Queries
        </div>
        
        <div class="features">
            <div class="feature">
                <h3>🔬 Technology</h3>
                <p>AI/ML, Cybersecurity, Software Development, Cloud Computing, Blockchain</p>
            </div>
            <div class="feature">
                <h3>💼 Business</h3>
                <p>Strategy, Finance, Marketing, Operations, Entrepreneurship</p>
            </div>
            <div class="feature">
                <h3>🧪 Science</h3>
                <p>Physics, Chemistry, Biology, Mathematics, Research</p>
            </div>
            <div class="feature">
                <h3>🎨 Creative</h3>
                <p>Art, Design, Writing, Music, Innovation</p>
            </div>
        </div>
        
        <a href="/chat" class="chat-link">💬 Start Chatting</a>
        
        <div style="text-align: center; margin-top: 30px;">
            <p><strong>API Endpoints:</strong></p>
            <p><a href="/api/status" style="color: #FFD700;">/api/status</a> - System Status</p>
            <p><strong>Domain:</strong> cllusion.me | <strong>Python:</strong> 3.11.13</p>
        </div>
    </div>
</body>
</html>
"""

CHAT_TEMPLATE = """
<!DOCTYPE html>
<html>
<head>
    <title>Chat with Celsius AI</title>
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <style>
        body { 
            font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            color: white; margin: 0; padding: 20px; min-height: 100vh; 
        }
        .chat-container { max-width: 600px; margin: 0 auto; }
        .header { text-align: center; margin-bottom: 30px; }
        .messages { 
            height: 400px; overflow-y: auto; background: rgba(0,0,0,0.2);
            padding: 20px; border-radius: 10px; margin-bottom: 20px;
        }
        .message { margin-bottom: 15px; }
        .user { text-align: right; }
        .ai { text-align: left; }
        .message-content { 
            display: inline-block; padding: 10px 15px; border-radius: 15px; max-width: 80%;
        }
        .user .message-content { background: rgba(255,255,255,0.2); }
        .ai .message-content { background: rgba(76, 175, 80, 0.3); }
        .input-area { display: flex; gap: 10px; }
        .input-field { 
            flex: 1; padding: 15px; border: none; border-radius: 25px;
            background: rgba(255,255,255,0.9); color: #333; font-size: 16px;
        }
        .send-btn { 
            padding: 15px 30px; border: none; border-radius: 25px;
            background: #4CAF50; color: white; font-weight: bold; cursor: pointer;
        }
        .send-btn:hover { background: #45a049; }
    </style>
</head>
<body>
    <div class="chat-container">
        <div class="header">
            <h1>🌡️ Chat with Celsius AI</h1>
            <p>Universal Intelligence System</p>
        </div>
        
        <div id="messages" class="messages">
            <div class="message ai">
                <div class="message-content">
                    Hello! I'm Celsius AI, your Universal Intelligence System. I'm ready to help with any questions across technology, business, science, creative work, education, or social topics. What can I assist you with?
                </div>
            </div>
        </div>
        
        <div class="input-area">
            <input type="text" id="messageInput" class="input-field" 
                   placeholder="Ask me anything..." onkeypress="handleKeyPress(event)">
            <button class="send-btn" onclick="sendMessage()">Send</button>
        </div>
    </div>

    <script>
        function handleKeyPress(event) {
            if (event.key === 'Enter') {
                sendMessage();
            }
        }
        
        async function sendMessage() {
            const input = document.getElementById('messageInput');
            const message = input.value.trim();
            
            if (!message) return;
            
            // Add user message
            addMessage(message, 'user');
            input.value = '';
            
            try {
                const response = await fetch('/api/chat', {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify({ message: message })
                });
                
                const data = await response.json();
                addMessage(data.response || 'Sorry, I encountered an error.', 'ai');
            } catch (error) {
                addMessage('Connection error. Please try again.', 'ai');
            }
        }
        
        function addMessage(text, sender) {
            const messages = document.getElementById('messages');
            const messageDiv = document.createElement('div');
            messageDiv.className = `message ${sender}`;
            
            const contentDiv = document.createElement('div');
            contentDiv.className = 'message-content';
            contentDiv.textContent = text;
            
            messageDiv.appendChild(contentDiv);
            messages.appendChild(messageDiv);
            messages.scrollTop = messages.scrollHeight;
        }
    </script>
</body>
</html>
"""

if __name__ == "__main__":
    if FLASK_AVAILABLE:
        # For development/testing
        app.run(host="0.0.0.0", port=5000, debug=False)
    else:
        print("Flask not available. Please install Flask to run the full application.")
        print("Minimal version: Use static HTML files instead.")
