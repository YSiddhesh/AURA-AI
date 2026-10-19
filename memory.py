import json
import os
from pathlib import Path

# Store memory beside this Python file.
MEMORY_FILE = Path(__file__).resolve().parent / "memory.json"

# Prevent unlimited conversation-history growth.
MAX_MEMORY_ENTRIES = 100


def load_memory():
    """Load persistent conversation memory."""
    if not MEMORY_FILE.exists():
        return []

    try:
        with MEMORY_FILE.open("r", encoding="utf-8") as file:
            memory = json.load(file)

        if not isinstance(memory, list):
            return []

        # Keep only entries with the expected structure.
        return [
            entry
            for entry in memory
            if isinstance(entry, dict)
            and isinstance(entry.get("role"), str)
            and isinstance(entry.get("text"), str)
        ][-MAX_MEMORY_ENTRIES:]

    except (json.JSONDecodeError, OSError):
        return []


def save_memory(memory):
    """Save the most recent conversation entries."""
    if not isinstance(memory, list):
        raise TypeError("Memory must be a list.")

    memory = memory[-MAX_MEMORY_ENTRIES:]

    with MEMORY_FILE.open("w", encoding="utf-8") as file:
        json.dump(memory, file, indent=4, ensure_ascii=False)


def add_memory(role, text):
    """Append a conversation entry to persistent memory."""
    if not isinstance(role, str) or not isinstance(text, str):
        raise TypeError("Role and text must be strings.")

    memory = load_memory()

    memory.append({
        "role": role,
        "text": text
    })

    save_memory(memory)


def get_recent_memory(limit=10):
    """Return recent conversation entries for context restoration."""
    if not isinstance(limit, int) or isinstance(limit, bool) or limit < 1:
        raise ValueError("Limit must be a positive integer.")

    return load_memory()[-limit:]


def clear_memory():
    """Clear all persistent conversation entries."""
    save_memory([])
    print("AURA: Persistent memory cleared.")
