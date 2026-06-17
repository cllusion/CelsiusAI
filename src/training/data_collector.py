"""
CelsiusAI Data Collector
=========================
Logs every conversation as training data so CelsiusAI learns from real use.

Three data tiers:
  live_conversations.jsonl  - auto-logged from every interaction
  curated_qa.jsonl          - manually written, high-quality pairs
  merged_training_data.jsonl - combined file used for training (curated x2)

Usage:
  from src.training.data_collector import log_conversation, add_curated_qa

  # Auto-called after every response
  log_conversation("How do I add a seller?", "Go to /admin/sellers...")

  # Manually add verified knowledge
  add_curated_qa("What is MAO?", "MAO = (ARV x 0.70) - Repairs", category="real_estate")
"""

import json
from datetime import datetime
from pathlib import Path
from typing import Optional

PROJECT_ROOT = Path(__file__).resolve().parents[2]
TRAINING_DIR = PROJECT_ROOT / 'data' / 'training'
LIVE_FILE = TRAINING_DIR / 'live_conversations.jsonl'
CURATED_FILE = TRAINING_DIR / 'curated_qa.jsonl'


def log_conversation(prompt: str, response: str, source: str = 'live') -> None:
    """Append a Q&A pair to live_conversations.jsonl after every interaction."""
    TRAINING_DIR.mkdir(parents=True, exist_ok=True)
    entry = {
        'prompt': prompt.strip(),
        'response': response.strip(),
        'source': source,
        'timestamp': datetime.now().isoformat(),
    }
    with open(LIVE_FILE, 'a', encoding='utf-8') as f:
        f.write(json.dumps(entry) + '\n')


def add_curated_qa(prompt: str, response: str, category: str = 'general') -> None:
    """Add a manually verified Q&A pair to the curated dataset."""
    TRAINING_DIR.mkdir(parents=True, exist_ok=True)
    entry = {
        'prompt': prompt.strip(),
        'response': response.strip(),
        'category': category,
        'curated': True,
        'timestamp': datetime.now().isoformat(),
    }
    with open(CURATED_FILE, 'a', encoding='utf-8') as f:
        f.write(json.dumps(entry) + '\n')


def merge_training_data(output_path: Optional[Path] = None) -> Path:
    """
    Combine all sources into one JSONL file for training.
    Curated pairs are included twice (double weight).
    """
    output_path = output_path or (TRAINING_DIR / 'merged_training_data.jsonl')
    TRAINING_DIR.mkdir(parents=True, exist_ok=True)

    all_entries = []
    for src in [LIVE_FILE, CURATED_FILE]:
        if src.exists():
            with open(src, encoding='utf-8') as f:
                for line in f:
                    line = line.strip()
                    if line:
                        obj = json.loads(line)
                        all_entries.append(obj)
                        if obj.get('curated'):
                            all_entries.append(obj)  # double-weight curated

    # Also include seed data if present
    seed = TRAINING_DIR / 'seed_qa.jsonl'
    if seed.exists():
        with open(seed, encoding='utf-8') as f:
            for line in f:
                line = line.strip()
                if line:
                    obj = json.loads(line)
                    all_entries.append(obj)
                    all_entries.append(obj)  # seed data gets double weight too

    with open(output_path, 'w', encoding='utf-8') as f:
        for entry in all_entries:
            f.write(json.dumps({'prompt': entry['prompt'], 'response': entry['response']}) + '\n')

    print(f"Merged {len(all_entries)} training examples → {output_path}")
    return output_path
