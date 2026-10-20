import re
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
    """Save recent conversation entries with a safer file-replacement strategy."""
    if not isinstance(memory, list):
        raise TypeError("Memory must be a list.")

    memory = memory[-MAX_MEMORY_ENTRIES:]

    # Validate entries before saving.
    memory = [
        entry
        for entry in memory
        if isinstance(entry, dict)
        and isinstance(entry.get("role"), str)
        and isinstance(entry.get("text"), str)
    ]

    temporary_file = MEMORY_FILE.with_suffix(".tmp")

    try:
        with temporary_file.open("w", encoding="utf-8") as file:
            json.dump(memory, file, indent=4, ensure_ascii=False)
            file.flush()
            os.fsync(file.fileno())

        # Replace the original only after the temporary file is complete.
        os.replace(temporary_file, MEMORY_FILE)

    finally:
        # Remove a leftover temporary file if one remains.
        try:
            temporary_file.unlink(missing_ok=True)
        except OSError:
            pass



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


def search_memory(query, limit=5):
    """Find stored conversation entries that match important query keywords."""
    if not isinstance(query, str):
        raise TypeError("Query must be a string.")

    if not isinstance(limit, int) or isinstance(limit, bool) or limit < 1:
        raise ValueError("Limit must be a positive integer.")

    stop_words = {
        "a", "an", "and", "are", "did", "do", "does", "for",
        "i", "in", "is", "it", "me", "my", "of", "on", "or",
        "the", "to", "was", "were", "what", "when", "where",
        "which", "who", "why", "with", "you", "your", "previously"
    }

    def keywords(text):
        words = set(re.findall(r"[a-z]+", text.lower()))
        return words - stop_words

    query_words = keywords(query)

    if not query_words:
        return []

    memory = load_memory()
    matches = []

    for index, entry in enumerate(memory):
        entry_words = keywords(entry["text"])
        overlap = query_words & entry_words

        if overlap:
            # Prefer entries matching more query keywords.
            score = len(overlap)
            matches.append((score, index, entry))

    # Higher scores first; newer entries win ties.
    matches.sort(key=lambda item: (item[0], item[1]), reverse=True)

    return [entry for _, _, entry in matches[:limit]]


def clear_memory():
    """Clear all persistent conversation entries."""
    save_memory([])
    print("AURA: Persistent memory cleared.")
