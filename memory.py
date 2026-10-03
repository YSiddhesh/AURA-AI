import json
import os

MEMORY_FILE = "memory.json"


def load_memory():

    if not os.path.exists(MEMORY_FILE):
        return []

    try:
        with open(MEMORY_FILE, "r", encoding="utf-8") as file:
            return json.load(file)

    except (json.JSONDecodeError, OSError):
        return []


def save_memory(memory):

    with open(MEMORY_FILE, "w", encoding="utf-8") as file:
        json.dump(
            memory,
            file,
            indent=4,
            ensure_ascii=False
        )


def add_memory(role, text):

    memory = load_memory()

    memory.append({
        "role": role,
        "text": text
    })

    save_memory(memory)


def clear_memory():

    save_memory([])

    print("AURA: Persistent memory cleared.")