import re


WINDOWS_APPS = {
    "notepad": ["notepad", "text editor"],
    "calculator": ["calculator", "calc"],
    "paint": ["paint", "ms paint"],
}

ANDROID_APPS = {
    "youtube": ["youtube", "you tube"],
    "chrome": ["chrome", "google chrome"],
    "whatsapp": ["whatsapp", "what's app", "whats app"],
    "settings": ["settings", "phone settings"],
}

DEVICE_ALIASES = {
    "phone1": [
        "phone 1",
        "phone one",
        "first phone",
        "android 1",
        "android one",
        "Siddhesh phone",
        "realme",
    ],
    "phone2": [
        "phone 2",
        "phone two",
        "second phone",
        "android 2",
        "android two",
        "Kirti phone",
        "Redmi",
    ],
}


def clean_command(command):
    command = command.lower().strip()
    command = re.sub(r"\b(hey|okay|ok)?\s*aura\b", "", command)
    command = re.sub(r"[.,!?]", "", command)
    return command.strip()


def find_app(command, app_list):
    for app_name, aliases in app_list.items():
        for alias in aliases:
            if re.search(rf"\b{re.escape(alias)}\b", command):
                return app_name

    return None


def find_device(command):
    for device, aliases in DEVICE_ALIASES.items():
        for alias in aliases:
            if re.search(rf"\b{re.escape(alias)}\b", command):
                return device

    return None


def mentions_android_device(command):
    return bool(
        re.search(
            r"\b(phone|android|mobile|realme|xiaomi)\b",
            command,
        )
        or re.search(r"\b(first|second)\s+(phone|android)\b", command)
    )


def parse_command(command):
    command = clean_command(command)

    if not command:
        return {"intent": "unknown", "target": None}

    device = find_device(command) or "phone1"
    has_device = mentions_android_device(command)

    # Phone lock is recognized, but this feature is currently skipped.
    if re.search(r"\block\b", command) and has_device:
        return {
            "intent": "android_lock",
            "target": None,
            "device": device,
        }

    # Laptop lock
    if re.search(r"\block\b", command):
        return {
            "intent": "lock_device",
            "target": "laptop",
        }

    # Android Home and Back controls
    if has_device:
        if re.search(r"\b(home|go home)\b", command):
            return {
                "intent": "android_home",
                "target": None,
                "device": device,
            }

        if re.search(r"\b(back|go back)\b", command):
            return {
                "intent": "android_back",
                "target": None,
                "device": device,
            }

    # Android battery information
    if re.search(r"\bbattery\b", command) and has_device:
        return {
            "intent": "android_battery",
            "target": None,
            "device": device,
        }

    # Android device information
    if re.search(
        r"\b(model|manufacturer|device info|which phone|what phone)\b",
        command,
    ):
        if has_device or re.search(
            r"\b(this phone|my phone|my device)\b",
            command,
        ):
            return {
                "intent": "android_device_info",
                "target": None,
                "device": device,
            }

    # App-opening commands
    action_pattern = (
        r"^(?:please\s+|can you\s+|could you\s+|would you\s+)?"
        r"(?:open|launch|start|run)\s+"
    )

    match = re.match(action_pattern, command)

    if not match:
        return {"intent": "unknown", "target": None}

    target = command[match.end():].strip()

    is_android_command = mentions_android_device(target)
    device = find_device(target) or "phone1"

    # Remove destination wording from the app name.
    target = re.sub(
        r"\b(?:on|in)\s+(?:my|the)?\s*"
        r"(?:phone\s*(?:1|2|one|two)?|"
        r"android\s*(?:1|2|one|two)?|"
        r"mobile\s*(?:1|2|one|two)?|"
        r"first\s+(?:phone|android)|"
        r"second\s+(?:phone|android)|"
        r"realme|xiaomi)\b",
        "",
        target,
    ).strip()

    target = re.sub(
        r"^(?:the|my|a|an|file|application|app)\s+",
        "",
        target,
    ).strip()

    if is_android_command:
        app_name = find_app(target, ANDROID_APPS)

        if app_name:
            return {
                "intent": "open_android_app",
                "target": app_name,
                "device": device,
            }

        return {"intent": "unknown", "target": None}

    app_name = find_app(target, WINDOWS_APPS)

    if app_name:
        return {
            "intent": "open_application",
            "target": app_name,
        }

    if target:
        return {
            "intent": "open_file",
            "target": target,
        }

    return {"intent": "unknown", "target": None}


if __name__ == "__main__":
    tests = [
        "Hey AURA, open YouTube on my phone",
        "Hey AURA, open YouTube on phone 1",
        "Hey AURA, open YouTube on phone 2",
        "Open YouTube on Android 2",
        "Hey AURA, open Notepad",
        "Lock my laptop",
        "Hey AURA, open Chrome on phone 1",
        "Hey AURA, open WhatsApp on phone 2",
        "Hey AURA, open Settings on phone 1",
        "Hey AURA, go home on phone 1",
        "Hey AURA, go back on phone 1",
        "Hey AURA, go home on phone 2",
        "Hey AURA, go back on phone 2",
        "Check phone 1 battery",
        "Check phone 2 battery",
        "What is my phone model?",
        "What phone is this?",
        "Can you launch YouTube on my first phone?",
        "Start YouTube on my realme",
        "Open Chrome on the second phone",
        "Open WhatsApp on Kirti phone",
        "Open WhatsApps on Siddhesh phone",
    ]

    for test in tests:
        print(test, "->", parse_command(test))