"""
Celsius AI - Health and Fitness Data Management
===============================================

Description:
------------
This module provides a comprehensive system for managing health and fitness
data within the Celsius AI ecosystem. It supports tracking various health
metrics, setting and monitoring fitness goals, and logging workout sessions.

The system is designed to be data-source agnostic, with built-in support for
importing data from various formats, including a text-based format from
conversational inputs (referred to as "Gemini" format).

Key Features:
-------------
- **Structured Data Models**: Uses `dataclasses` for strongly-typed and clear
  representation of health metrics, fitness goals, and workout sessions.
- **Persistent Storage**: Saves all health-related data to JSON files in a
  dedicated `data/health` directory.
- **Data Import**: Includes a flexible parser to import health data from
  unstructured text, such as a conversation with an AI assistant.
- **User Profile**: Manages a user's health profile, including demographic data,
  health conditions, and fitness preferences.
- **Data Analysis**: Provides functions to analyze trends in health metrics (e.g.,
  weight, steps) and calculate progress towards fitness goals.
- **Comprehensive Summary**: Can generate a full health summary, including recent
  trends, goal progress, and workout statistics.
- **Natural Language Search**: Allows searching through health data using simple
  text queries.

Usage:
------
The `HealthDataManager` is the main class for interacting with the system.

    from core.health_data import HealthDataManager, MetricType, HealthMetric, DataSource
    from datetime import datetime

    manager = HealthDataManager()

    # Add a new health metric
    new_metric = HealthMetric(
        metric_type=MetricType.WEIGHT,
        value=80.5,
        unit="kg",
        timestamp=datetime.now(),
        source=DataSource.MANUAL
    )
    manager.add_health_metric(new_metric)

    # Get a health summary
    summary = manager.get_health_summary()
    print(summary)

    # Import data from a text snippet
    gemini_text = "My weight was 81kg this morning. I also did a 30 minute run."
    import_result = await manager.import_gemini_data(gemini_text)
    print(import_result)
"""

import json
import asyncio
import re
import os
import statistics
from datetime import datetime, timedelta, date
from typing import Dict, List, Optional, Any, Union
from dataclasses import dataclass, asdict, field
from enum import Enum
from pathlib import Path

# Define the root of the project to resolve paths correctly
PROJECT_ROOT = Path(__file__).resolve().parents[2]
DATA_DIR = PROJECT_ROOT / "data" / "health"


class DataSource(Enum):
    """Enumeration for the source of a health data entry."""

    GEMINI = "gemini"
    MANUAL = "manual"
    WEARABLE = "wearable"
    IMPORTED = "imported"
    API = "api"


class MetricType(Enum):
    """Enumeration for the type of health metric being recorded."""

    WEIGHT = "weight"
    HEIGHT = "height"
    BODY_FAT = "body_fat"
    MUSCLE_MASS = "muscle_mass"
    STEPS = "steps"
    HEART_RATE = "heart_rate"
    SLEEP = "sleep"
    CALORIES = "calories"
    WATER = "water"
    EXERCISE = "exercise"
    BLOOD_PRESSURE = "blood_pressure"
    GLUCOSE = "glucose"
    MOOD = "mood"


@dataclass
class HealthMetric:
    """
    Represents a single, time-stamped health measurement.
    """

    metric_type: MetricType
    value: Union[float, int, str, Dict]
    unit: str
    timestamp: datetime
    source: DataSource
    notes: Optional[str] = None
    confidence: float = 1.0  # Confidence score from 0.0 to 1.0

    def to_dict(self) -> Dict[str, Any]:
        """Serializes the dataclass to a dictionary."""
        data = asdict(self)
        data["timestamp"] = self.timestamp.isoformat()
        data["metric_type"] = self.metric_type.value
        data["source"] = self.source.value
        return data

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "HealthMetric":
        """Creates an instance from a dictionary."""
        data["timestamp"] = datetime.fromisoformat(data["timestamp"])
        data["metric_type"] = MetricType(data["metric_type"])
        data["source"] = DataSource(data["source"])
        return cls(**data)


@dataclass
class FitnessGoal:
    """
    Represents a user-defined fitness goal with progress tracking.
    """

    goal_id: str
    title: str
    description: str
    target_value: Union[float, int]
    current_value: Union[float, int]
    unit: str
    target_date: date
    category: str  # e.g., weight_loss, muscle_gain, endurance
    created_date: date
    is_active: bool = True
    milestones: List[Dict[str, Any]] = field(default_factory=list)

    @property
    def progress_percentage(self) -> float:
        """Calculates the completion percentage of the goal."""
        if self.target_value == 0:
            return 100.0 if self.current_value >= 0 else 0.0
        # Handle goals where lower is better (e.g., weight loss from a starting point)
        if self.target_value < self.current_value:
            # This logic might need to be more sophisticated, e.g., storing start_value
            return max(0.0, min(100.0, (self.current_value / self.target_value) * 100))
        return max(0.0, min(100.0, (self.current_value / self.target_value) * 100))

    @property
    def days_remaining(self) -> int:
        """Calculates the number of days remaining to reach the target date."""
        return (self.target_date - date.today()).days

    def to_dict(self) -> Dict[str, Any]:
        """Serializes the dataclass to a dictionary."""
        data = asdict(self)
        data["target_date"] = self.target_date.isoformat()
        data["created_date"] = self.created_date.isoformat()
        return data

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "FitnessGoal":
        """Creates an instance from a dictionary."""
        data["target_date"] = date.fromisoformat(data["target_date"])
        data["created_date"] = date.fromisoformat(data["created_date"])
        return cls(**data)


@dataclass
class WorkoutSession:
    """
    Represents a single workout session, including exercises and duration.
    """

    session_id: str
    date: date
    workout_type: str
    duration_minutes: int
    exercises: List[Dict[str, Any]]
    calories_burned: Optional[int] = None
    notes: Optional[str] = None
    rating: Optional[int] = None  # Subjective rating from 1 to 10
    source: DataSource = DataSource.MANUAL

    def to_dict(self) -> Dict[str, Any]:
        """Serializes the dataclass to a dictionary."""
        data = asdict(self)
        data["date"] = self.date.isoformat()
        data["source"] = self.source.value
        return data

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "WorkoutSession":
        """Creates an instance from a dictionary."""
        data["date"] = date.fromisoformat(data["date"])
        data["source"] = DataSource(data["source"])
        return cls(**data)


class HealthDataManager:
    """
    Manages all health and fitness data, including loading, saving,
    importing, and analysis.
    """

    def __init__(self, data_directory: Path = DATA_DIR):
        """
        Initializes the HealthDataManager.

        Args:
            data_directory (Path): The directory to store health data files.
        """
        self.data_dir: Path = data_directory
        self.metrics_file: Path = self.data_dir / "health_metrics.json"
        self.goals_file: Path = self.data_dir / "fitness_goals.json"
        self.workouts_file: Path = self.data_dir / "workouts.json"
        self.profile_file: Path = self.data_dir / "user_profile.json"

        self.data_dir.mkdir(parents=True, exist_ok=True)

        self.metrics: List[HealthMetric] = self._load_data(self.metrics_file, HealthMetric)
        self.goals: List[FitnessGoal] = self._load_data(self.goals_file, FitnessGoal)
        self.workouts: List[WorkoutSession] = self._load_data(self.workouts_file, WorkoutSession)
        self.user_profile: Dict[str, Any] = self._load_user_profile()

    def _load_data(self, file_path: Path, data_class: type) -> List[Any]:
        """
        Generic method to load a list of dataclass objects from a JSON file.

        Args:
            file_path (Path): The path to the JSON file.
            data_class (type): The dataclass type to instantiate (e.g., HealthMetric).

        Returns:
            List[Any]: A list of instantiated dataclass objects.
        """
        if not file_path.exists():
            return []
        try:
            with open(file_path, "r", encoding="utf-8") as f:
                data = json.load(f)
                return [data_class.from_dict(item) for item in data]
        except (json.JSONDecodeError, TypeError, KeyError) as e:
            print(f"Warning: Could not load or parse {file_path}: {e}. Starting with an empty list.")
            return []

    def _save_data(self, file_path: Path, data: List[Any]):
        """
        Generic method to save a list of dataclass objects to a JSON file.

        Args:
            file_path (Path): The path to the JSON file.
            data (List[Any]): A list of dataclass objects to save.
        """
        try:
            with open(file_path, "w", encoding="utf-8") as f:
                json.dump([item.to_dict() for item in data], f, indent=4)
        except (IOError, TypeError) as e:
            print(f"Error: Could not save data to {file_path}: {e}")

    def _load_user_profile(self) -> Dict[str, Any]:
        """Loads the user's health profile from a JSON file."""
        if not self.profile_file.exists():
            return self._get_default_profile()
        try:
            with open(self.profile_file, "r", encoding="utf-8") as f:
                return json.load(f)
        except (json.JSONDecodeError, TypeError):
            return self._get_default_profile()

    def _save_user_profile(self):
        """Saves the user's health profile to a JSON file."""
        self._save_data(self.profile_file, [self.user_profile])  # Re-using generic save
        try:
            with open(self.profile_file, "w", encoding="utf-8") as f:
                json.dump(self.user_profile, f, indent=4)
        except (IOError, TypeError) as e:
            print(f"Error: Could not save user profile to {self.profile_file}: {e}")

    @staticmethod
    def _get_default_profile() -> Dict[str, Any]:
        """Returns a default user profile structure."""
        return {
            "age": None,
            "gender": None,
            "height_cm": None,
            "activity_level": "moderate",
            "health_conditions": [],
            "medications": [],
            "allergies": [],
            "fitness_level": "intermediate",
            "preferred_workout_times": [],
            "fitness_interests": [],
        }

    async def import_gemini_data(self, gemini_data: str) -> Dict[str, Any]:
        """
        Imports health data from a Gemini conversation or text export.

        Args:
            gemini_data (str): The unstructured text data to parse.

        Returns:
            Dict[str, Any]: A report of the import process.
        """
        imported_count = 0
        errors = []

        try:
            parsed_data = self._parse_gemini_health_data(gemini_data)

            for entry in parsed_data:
                try:
                    entry_type = entry.get("type")
                    if entry_type == "metric":
                        metric = HealthMetric.from_dict({**entry, "source": DataSource.GEMINI.value})
                        self.add_health_metric(metric)
                        imported_count += 1
                    elif entry_type == "goal":
                        goal = FitnessGoal.from_dict({**entry, "created_date": date.today().isoformat()})
                        self.add_fitness_goal(goal)
                        imported_count += 1
                    elif entry_type == "workout":
                        workout = WorkoutSession.from_dict({**entry, "source": DataSource.GEMINI.value})
                        self.add_workout_session(workout)
                        imported_count += 1
                except (KeyError, TypeError, ValueError) as e:
                    errors.append(f"Error importing entry {entry}: {e}")

            return {
                "success": True,
                "imported_count": imported_count,
                "errors": errors,
                "message": f"Successfully imported {imported_count} health data entries from Gemini.",
            }
        except Exception as e:
            return {
                "success": False,
                "imported_count": 0,
                "errors": [f"Failed to parse Gemini data: {e}"],
                "message": "Failed to import Gemini health data.",
            }

    def _parse_gemini_health_data(self, data: str) -> List[Dict[str, Any]]:
        """
        Parses health data from various unstructured text formats.

        Args:
            data (str): The unstructured text.

        Returns:
            List[Dict[str, Any]]: A list of structured data entries.
        """
        # First, attempt to parse as JSON
        try:
            json_data = json.loads(data)
            if isinstance(json_data, list):
                return json_data
            if isinstance(json_data, dict) and "health_data" in json_data:
                return json_data["health_data"]
        except json.JSONDecodeError:
            pass  # If not JSON, proceed to text parsing

        parsed_entries = []
        lines = data.split("\n")

        for line in lines:
            line = line.strip()
            if not line:
                continue

            # Regex for weight: e.g., "80.5 kg", "175 lbs"
            weight_match = re.search(r"(\d+(?:\.\d+)?)\s*(lbs?|kg|pounds?)", line, re.IGNORECASE)
            if "weight" in line.lower() and weight_match:
                parsed_entries.append(
                    {
                        "type": "metric",
                        "metric_type": "weight",
                        "value": float(weight_match.group(1)),
                        "unit": "kg" if "kg" in weight_match.group(2).lower() else "lbs",
                        "timestamp": datetime.now().isoformat(),
                        "confidence": 0.8,
                    }
                )

            # Regex for workouts: e.g., "30 min run", "1 hour at the gym"
            duration_match = re.search(r"(\d+)\s*(min|minutes?|hour?s?)", line, re.IGNORECASE)
            if any(w in line.lower() for w in ["workout", "exercise", "run", "gym"]) and duration_match:
                duration = int(duration_match.group(1))
                if "hour" in duration_match.group(2).lower():
                    duration *= 60

                workout_type = "general"
                if "run" in line.lower():
                    workout_type = "running"
                elif "gym" in line.lower():
                    workout_type = "strength training"
                elif "cardio" in line.lower():
                    workout_type = "cardio"

                parsed_entries.append(
                    {
                        "type": "workout",
                        "session_id": f"gemini_{datetime.now().timestamp()}",
                        "date": date.today().isoformat(),
                        "workout_type": workout_type,
                        "duration_minutes": duration,
                        "exercises": [{"name": workout_type, "duration": duration}],
                        "notes": line,
                    }
                )

        return parsed_entries

    def add_health_metric(self, metric: HealthMetric):
        """Adds a new health metric and saves the data."""
        self.metrics.append(metric)
        self._save_data(self.metrics_file, self.metrics)

    def add_fitness_goal(self, goal: FitnessGoal):
        """Adds or updates a fitness goal and saves the data."""
        existing_goal = next((g for g in self.goals if g.goal_id == goal.goal_id), None)
        if existing_goal:
            existing_goal.target_value = goal.target_value
            existing_goal.current_value = goal.current_value
            existing_goal.target_date = goal.target_date
            existing_goal.is_active = goal.is_active
        else:
            self.goals.append(goal)
        self._save_data(self.goals_file, self.goals)

    def add_workout_session(self, workout: WorkoutSession):
        """Adds a new workout session and saves the data."""
        self.workouts.append(workout)
        self._save_data(self.workouts_file, self.workouts)

    def update_user_profile(self, updates: Dict[str, Any]):
        """Updates the user's health profile and saves it."""
        self.user_profile.update(updates)
        self._save_user_profile()

    def get_recent_metrics(self, metric_type: MetricType, days: int = 30) -> List[HealthMetric]:
        """Retrieves recent metrics of a specific type."""
        cutoff_date = datetime.now() - timedelta(days=days)
        return [m for m in self.metrics if m.metric_type == metric_type and m.timestamp >= cutoff_date]

    def get_metric_trend(self, metric_type: MetricType, days: int = 30) -> Dict[str, Any]:
        """Analyzes the trend for a specific metric over a period."""
        recent_metrics = self.get_recent_metrics(metric_type, days)
        values = [float(m.value) for m in recent_metrics if isinstance(m.value, (int, float))]

        if len(values) < 2:
            return {"trend": "insufficient_data", "values": values}

        first_half_avg = statistics.mean(values[: len(values) // 2])
        second_half_avg = statistics.mean(values[len(values) // 2 :])

        trend = "stable"
        if second_half_avg > first_half_avg * 1.05:
            trend = "increasing"
        elif second_half_avg < first_half_avg * 0.95:
            trend = "decreasing"

        change_percent = ((second_half_avg - first_half_avg) / first_half_avg) * 100 if first_half_avg != 0 else 0

        return {
            "trend": trend,
            "current_avg": second_half_avg,
            "previous_avg": first_half_avg,
            "change_percent": change_percent,
            "values": values,
            "recent_value": values[-1],
        }

    def get_goal_progress(self) -> List[Dict[str, Any]]:
        """Calculates and returns the progress for all active goals."""
        return [
            {
                "goal_id": goal.goal_id,
                "title": goal.title,
                "progress_percentage": goal.progress_percentage,
                "days_remaining": goal.days_remaining,
                "category": goal.category,
                "current_value": goal.current_value,
                "target_value": goal.target_value,
                "unit": goal.unit,
            }
            for goal in self.goals
            if goal.is_active
        ]

    def get_health_summary(self) -> Dict[str, Any]:
        """Generates a comprehensive health and fitness summary."""
        recent_workouts = [w for w in self.workouts if (date.today() - w.date).days <= 30]

        summary = {
            "metrics_count": len(self.metrics),
            "active_goals_count": len([g for g in self.goals if g.is_active]),
            "total_workouts_count": len(self.workouts),
            "recent_trends": {},
            "goal_progress": self.get_goal_progress(),
            "last_30_days": {
                "workouts_count": len(recent_workouts),
                "total_workout_minutes": sum(w.duration_minutes for w in recent_workouts),
            },
        }

        for m_type in [MetricType.WEIGHT, MetricType.STEPS, MetricType.HEART_RATE]:
            trend = self.get_metric_trend(m_type)
            if trend["trend"] != "insufficient_data":
                summary["recent_trends"][m_type.value] = trend

        return summary

    def search_health_data(self, query: str) -> Dict[str, List[Dict[str, Any]]]:
        """
        Searches through all health data based on a natural language query.

        Args:
            query (str): The search query.

        Returns:
            A dictionary containing lists of matching metrics, goals, and workouts.
        """
        query_lower = query.lower().split()
        results: Dict[str, List[Dict[str, Any]]] = {"metrics": [], "goals": [], "workouts": []}

        for metric in self.metrics[-100:]:
            if any(term in str(metric).lower() for term in query_lower):
                results["metrics"].append(metric.to_dict())

        for goal in self.goals:
            if any(term in str(goal).lower() for term in query_lower):
                results["goals"].append(goal.to_dict())

        for workout in self.workouts[-50:]:
            if any(term in str(workout).lower() for term in query_lower):
                results["workouts"].append(workout.to_dict())

        return results
