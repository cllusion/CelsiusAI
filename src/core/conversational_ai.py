"""
Celsius AI - Enhanced Conversational AI
=======================================

Description:
------------
This module provides the core logic for human-like conversational capabilities
in the Celsius AI ecosystem. It endows the AI with personality, long-term memory,
and a degree of emotional intelligence to create more engaging and natural
interactions with the user.

Key Features:
-------------
- **Personality Core**: Defines the AI's personality traits (e.g., helpfulness,
  humor, empathy) and conversation styles (casual, professional, friendly).
- **Conversation Memory**: Persists conversation history, user preferences, topics
  discussed, and mood patterns to a JSON file, allowing for context-aware
  interactions over time.
- **Relationship Building**: Dynamically adjusts its conversation style based on the
  length and depth of the interaction history, moving from "new" to "close".
- **Mood Analysis**: Performs basic sentiment analysis on user messages to detect
  mood (positive, negative, excited) and adapt its responses accordingly.
- **Contextual Greetings**: Generates greetings that are aware of the time elapsed
  since the last interaction.
- **Preference Extraction**: Identifies and stores user preferences mentioned during
  conversation (e.g., workout times, communication style).
- **Insight Generation**: Provides a summary of conversation patterns, including
  relationship level, mood trends, and favorite topics.

Usage:
------
This module is typically used by the main assistant to process and enhance
responses.

    from core.conversational_ai import ConversationalAI

    convo_ai = ConversationalAI()

    # Process a user message to get context
    context = convo_ai.process_conversation("That's great news!", topic="general")

    # Generate a base response from another module (e.g., a knowledge base)
    base_response = "The task was completed successfully."

    # Enhance the response with personality and context
    enhanced_response = convo_ai.enhance_response(base_response, context)
    print(enhanced_response)
    # >> "That's awesome! The task was completed successfully."
"""

import json
import asyncio
import random
import re
import os
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any, Literal
from dataclasses import dataclass, asdict, field
from pathlib import Path

# Define the root of the project to resolve paths correctly
PROJECT_ROOT = Path(__file__).resolve().parents[2]
MEMORY_FILE_PATH = PROJECT_ROOT / "data" / "conversation_memory.json"

RelationshipLevel = Literal["new", "casual", "familiar", "close"]
UserMood = Literal["positive", "negative", "neutral", "excited", "curious"]
ConversationStyle = Literal["casual", "professional", "friendly"]


@dataclass
class ConversationMemory:
    """
    Stores the long-term memory of conversations, including user preferences,
    history, and relationship status.
    """

    user_preferences: Dict[str, Any] = field(default_factory=dict)
    conversation_history: List[Dict[str, Any]] = field(default_factory=list)
    topics_discussed: List[str] = field(default_factory=list)
    user_mood_pattern: List[UserMood] = field(default_factory=list)
    relationship_level: RelationshipLevel = "new"
    last_interaction: datetime = field(default_factory=datetime.now)


class PersonalityCore:
    """
    Defines the core personality traits and conversational styles for Celsius AI.
    This class provides the building blocks for generating human-like text.
    """

    def __init__(self):
        """Initializes the personality with predefined traits and styles."""
        self.personality_traits: Dict[str, float] = {
            "helpfulness": 0.9,
            "curiosity": 0.8,
            "empathy": 0.85,
            "humor": 0.6,
            "professionalism": 0.8,
            "enthusiasm": 0.7,
            "patience": 0.9,
        }

        self.conversation_styles: Dict[ConversationStyle, Dict[str, List[str]]] = {
            "casual": {
                "greetings": ["Hey there!", "What's up?", "Good to see you again!", "How's it going?"],
                "confirmations": ["Got it!", "Makes sense!", "Absolutely!", "I hear you!"],
                "thinking": ["Hmm, let me think about that...", "That's interesting...", "Good question!"],
                "enthusiasm": ["That's awesome!", "Nice!", "Love it!", "Fantastic!"],
            },
            "professional": {
                "greetings": ["Good morning.", "Good afternoon.", "Hello.", "Welcome back."],
                "confirmations": ["Understood.", "Certainly.", "Of course.", "I see."],
                "thinking": ["Let me analyze that...", "I'm processing this information...", "Allow me to consider..."],
                "enthusiasm": ["Excellent.", "Outstanding.", "Very good.", "Impressive."],
            },
            "friendly": {
                "greetings": ["Hi there!", "Great to see you!", "Welcome back, friend!", "Hope you're doing well!"],
                "confirmations": ["Sounds good!", "Perfect!", "I'm with you!", "Totally understand!"],
                "thinking": ["Ooh, that's a great question!", "Let me dive into that...", "This is interesting!"],
                "enthusiasm": ["That's amazing!", "So cool!", "I love that!", "Brilliant!"],
            },
        }


class ConversationalAI:
    """
    Manages the conversational aspects of the AI, integrating personality,
    memory, and emotional analysis to produce human-like responses.
    """

    def __init__(self, memory_path: Path = MEMORY_FILE_PATH):
        """
        Initializes the ConversationalAI.

        Args:
            memory_path (Path): The file path to store and retrieve conversation memory.
        """
        self.personality: PersonalityCore = PersonalityCore()
        self.memory_file: Path = memory_path
        self.conversation_memory: ConversationMemory = self._load_memory()
        self.context_window: List[Dict[str, Any]] = []
        self.emotional_state: str = "neutral"  # The AI's current internal emotional state

    def _load_memory(self) -> ConversationMemory:
        """
        Loads conversation memory from the specified JSON file.
        If the file doesn't exist or is invalid, creates a new memory object.

        Returns:
            ConversationMemory: The loaded or newly created conversation memory.
        """
        try:
            if self.memory_file.exists():
                with open(self.memory_file, "r", encoding="utf-8") as f:
                    data = json.load(f)
                    data["last_interaction"] = datetime.fromisoformat(data["last_interaction"])
                    return ConversationMemory(**data)
        except (json.JSONDecodeError, TypeError, KeyError) as e:
            print(f"Warning: Could not load or parse memory file: {e}. Starting fresh.")

        return ConversationMemory()

    def _save_memory(self):
        """
        Saves the current conversation memory to the JSON file.
        Ensures the directory exists before writing.
        """
        try:
            self.memory_file.parent.mkdir(parents=True, exist_ok=True)

            data = asdict(self.conversation_memory)
            data["last_interaction"] = data["last_interaction"].isoformat()

            with open(self.memory_file, "w", encoding="utf-8") as f:
                json.dump(data, f, indent=4)
        except (IOError, TypeError) as e:
            print(f"Error: Could not save conversation memory to {self.memory_file}: {e}")

    def _analyze_user_mood(self, message: str) -> UserMood:
        """
        Performs a basic analysis of the user's mood from their message.

        Args:
            message (str): The user's input message.

        Returns:
            UserMood: The detected mood.
        """
        message_lower = message.lower()

        positive_words = ["great", "awesome", "good", "happy", "excited", "love", "amazing", "fantastic"]
        negative_words = ["bad", "terrible", "sad", "angry", "frustrated", "hate", "awful", "worried"]

        if any(word in message_lower for word in positive_words):
            return "positive"
        if any(word in message_lower for word in negative_words):
            return "negative"
        if "!" in message or message.isupper():
            return "excited"
        if "?" in message:
            return "curious"

        return "neutral"

    def _determine_conversation_style(self) -> ConversationStyle:
        """
        Determines the appropriate conversation style based on the relationship level.

        Returns:
            ConversationStyle: The chosen style for the next response.
        """
        relationship = self.conversation_memory.relationship_level

        if relationship == "new":
            return "professional"
        if relationship == "casual":
            return random.choice(["casual", "friendly"])
        if relationship in ["familiar", "close"]:
            return "friendly"

        return "casual"

    def _get_contextual_greeting(self) -> str:
        """
        Generates a contextual greeting based on the time since the last interaction.

        Returns:
            str: A situationally appropriate greeting message.
        """
        now = datetime.now()
        time_since_last = now - self.conversation_memory.last_interaction

        style = self._determine_conversation_style()
        greetings = self.personality.conversation_styles[style]["greetings"]

        if time_since_last.days > 7:
            return f"{random.choice(greetings)} It's been a while! How have you been?"
        if time_since_last.days > 1:
            return f"{random.choice(greetings)} How was your day yesterday?"
        if time_since_last.total_seconds() > 3600 * 6:  # 6 hours
            return f"{random.choice(greetings)} Hope you're having a good day!"

        return random.choice(greetings)

    def _add_personality_to_response(self, base_response: str, user_mood: UserMood) -> str:
        """
        Enhances a base response with personality elements like enthusiasm or empathy.

        Args:
            base_response (str): The core, factual response.
            user_mood (UserMood): The user's detected mood.

        Returns:
            str: The response enhanced with personality.
        """
        style = self._determine_conversation_style()
        prefix = ""

        if user_mood == "positive":
            enthusiasm = self.personality.conversation_styles[style]["enthusiasm"]
            prefix = f"{random.choice(enthusiasm)} "
        elif user_mood == "negative":
            prefix = "I'm sorry to hear that. "
        elif user_mood == "excited":
            prefix = "I can feel your excitement! "

        # Add a "thinking" phrase for complex responses
        if len(base_response) > 200:
            thinking = self.personality.conversation_styles[style]["thinking"]
            base_response = f"{random.choice(thinking)} {base_response}"

        # Add a touch of humor or enthusiasm based on personality traits
        if self.personality.personality_traits["humor"] > 0.5 and random.random() < 0.2:
            humor_additions = [
                " (I find this stuff fascinating!)",
                " - always happy to dive deep into topics like this!",
            ]
            base_response += random.choice(humor_additions)

        return prefix + base_response

    def _update_relationship_level(self):
        """Updates the relationship level based on the number of interactions."""
        history_length = len(self.conversation_memory.conversation_history)

        if history_length < 5:
            self.conversation_memory.relationship_level = "new"
        elif history_length < 20:
            self.conversation_memory.relationship_level = "casual"
        elif history_length < 50:
            self.conversation_memory.relationship_level = "familiar"
        else:
            self.conversation_memory.relationship_level = "close"

    def _extract_user_preferences(self, message: str, topic: str):
        """
        Extracts and stores user preferences from the conversation.

        Args:
            message (str): The user's message.
            topic (str): The topic of the conversation.
        """
        message_lower = message.lower()
        prefs = self.conversation_memory.user_preferences

        # Example: Extracting fitness preferences
        if "fitness" in topic.lower() or "health" in topic.lower():
            if "morning" in message_lower and ("workout" in message_lower or "exercise" in message_lower):
                prefs["workout_time"] = "morning"
            elif "evening" in message_lower and ("workout" in message_lower or "exercise" in message_lower):
                prefs["workout_time"] = "evening"

            goal_keywords = {
                "weight loss": "lose weight",
                "muscle": "build muscle",
                "cardio": "improve cardio",
                "strength": "build strength",
                "endurance": "improve endurance",
            }

            current_goals = prefs.setdefault("fitness_goals", [])
            for keyword, goal in goal_keywords.items():
                if keyword in message_lower and goal not in current_goals:
                    current_goals.append(goal)

        # Example: Extracting communication style preference
        if "formal" in message_lower or "professional" in message_lower:
            prefs["communication_style"] = "professional"
        elif "casual" in message_lower or "relaxed" in message_lower:
            prefs["communication_style"] = "casual"

    def process_conversation(self, user_message: str, topic: str = "general") -> Dict[str, Any]:
        """
        Processes a user's message, updates memory, and prepares a context for response generation.

        Args:
            user_message (str): The raw message from the user.
            topic (str): The general topic of the message.

        Returns:
            Dict[str, Any]: A context dictionary for use in `enhance_response`.
        """
        user_mood = self._analyze_user_mood(user_message)
        now = datetime.now()

        # Update short-term context window
        self.context_window.append(
            {"timestamp": now, "user_message": user_message, "user_mood": user_mood, "topic": topic}
        )
        self.context_window = self.context_window[-10:]  # Keep it to the last 10 entries

        # Extract and update long-term memory
        self._extract_user_preferences(user_message, topic)

        self.conversation_memory.conversation_history.append(
            {"timestamp": now.isoformat(), "user_message": user_message, "user_mood": user_mood, "topic": topic}
        )

        if topic not in self.conversation_memory.topics_discussed:
            self.conversation_memory.topics_discussed.append(topic)

        self.conversation_memory.user_mood_pattern.append(user_mood)
        self.conversation_memory.user_mood_pattern = self.conversation_memory.user_mood_pattern[-20:]

        self._update_relationship_level()
        self.conversation_memory.last_interaction = now

        self._save_memory()

        # Prepare context for the response enhancer
        response_context = {
            "greeting": self._get_contextual_greeting() if len(self.context_window) == 1 else None,
            "user_mood": user_mood,
            "conversation_style": self._determine_conversation_style(),
            "relationship_level": self.conversation_memory.relationship_level,
            "user_preferences": self.conversation_memory.user_preferences,
            "recent_topics": self.conversation_memory.topics_discussed[-5:],
            "context_for_personality": True,
        }

        return response_context

    def enhance_response(self, base_response: str, context: Dict[str, Any]) -> str:
        """
        Enhances a base AI response with conversational personality and context.

        Args:
            base_response (str): The core, un-enhanced response.
            context (Dict[str, Any]): The context from `process_conversation`.

        Returns:
            str: The fully enhanced, human-like response.
        """
        if not context.get("context_for_personality"):
            return base_response

        user_mood = context.get("user_mood", "neutral")
        enhanced_response = self._add_personality_to_response(base_response, user_mood)

        if context.get("greeting"):
            enhanced_response = f"{context['greeting']}\n\n{enhanced_response}"

        # Add personalized touches based on stored preferences
        preferences = context.get("user_preferences", {})
        if "fitness_goals" in preferences and "fitness" in base_response.lower():
            goals = ", ".join(preferences["fitness_goals"])
            enhanced_response += f"\n\nBy the way, I remember you're working on {goals}. This could definitely help!"

        return enhanced_response

    def get_conversation_insights(self) -> Dict[str, Any]:
        """
        Provides a summary of conversation history and user patterns.

        Returns:
            Dict[str, Any]: A dictionary of insights.
        """
        history = self.conversation_memory.conversation_history
        first_interaction = datetime.fromisoformat(history[0]["timestamp"]) if history else datetime.now()

        return {
            "total_interactions": len(history),
            "relationship_level": self.conversation_memory.relationship_level,
            "recent_mood_pattern": self.conversation_memory.user_mood_pattern[-5:],
            "favorite_topics": self.conversation_memory.topics_discussed,
            "user_preferences": self.conversation_memory.user_preferences,
            "days_since_first_chat": (datetime.now() - first_interaction).days,
        }
