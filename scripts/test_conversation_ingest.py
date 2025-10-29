import sys
from pathlib import Path

sys.path.append(str(Path(__file__).resolve().parents[1]))
from src.learning.conversation_ingest import store_conversation

res = store_conversation(
    "Hello AI partner at test@example.com, call me at 555-123-4567. This is a sample conversation for ingestion.",
    participants="AI1,AI2",
    source="test",
)
print("Ingest result:", res)
