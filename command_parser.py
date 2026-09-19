import re


WINDOWS_APPS = {
    "notepad": ["notepad", "text editor"],
    "calculator": ["calculator", "calc"],
    "paint": ["paint", "ms paint"],
}


ANDROID_APPS = {
    "youtube": ["youtube", "you tube"],
    "chrome": ["chrome", "google chrome"],
    "whatsapp": [
        "whatsapp",
        "whats app",
        "what's app",
        "whatsapps",
    ],
    "settings": ["settings", "phone settings"],
}


DEVICE_ALIASES = {
    "phone1": [
        "phone 1",
        "phone one",
        "first phone",
        "android 1",
        "android one",
        "first android",
        "siddhesh phone",
        "realme",
    ],
    "phone2": [
        "phone 2",
        "phone two",
        "second phone",
        "android 2",
        "android two",
        "second android",
        "kirti phone",
        "redmi",
        "xiaomi",
    ],
}


def clean_command(command):
    command = command.lower().strip()

    command = re.sub(
        r"\b(hey|okay|ok)?\s*aura\b",
        "",
        command
    )

    command = re.sub(r"[.,!?]", "", command)

    return command.strip()


def find_app(command, app_list):
    for app_name, aliases in app_list.items():
        for alias in aliases:
            if re.search(
                rf"\b{re.escape(alias.lower())}\b",
                command
            ):
                return app_name

    return None


def find_device(command):
    command = command.lower()

    for device, aliases in DEVICE_ALIASES.items():
        for alias in aliases:
            if re.search(
                rf"\b{re.escape(alias.lower())}\b",
                command
            ):
                return device

    return None


def mentions_android_device(command):
    return bool(
        find_device(command)
        or re.search(
            r"\b(phone|android|mobile)\b",
            command
        )
    )


def remove_device_from_command(command):
    """
    Removes phrases such as:
    on phone 1
    on my first phone
    on the second phone
    on realme
    on siddhesh phone
    on kirti phone
    on redmi
    """

    command = command.lower()

    # Remove "on/in my/the ..."
    for device, aliases in DEVICE_ALIASES.items():
        for alias in aliases:
            pattern = (
                rf"\b(?:on|in)\s+"
                rf"(?:my|the)?\s*"
                rf"{re.escape(alias.lower())}\b"
            )

            command = re.sub(pattern, "", command)

    return command.strip()

def build_result(intent, target=None, device=None):
    result = {
        "intent": intent,
        "entities": {}
    }

    if target is not None:
        result["entities"]["target"] = target

    if device is not None:
        result["entities"]["device"] = device

    return result

def parse_command(command):
    command = clean_command(command)

    if not command:
        return {
            "intent": "unknown",
            "target": None
        }

    # Detect device
    device = find_device(command) or "phone1"

    has_device = mentions_android_device(command)

    # --------------------------------
    # Android Home
    # --------------------------------
    if has_device and re.search(
        r"\b(go home|home)\b",
        command
    ):
        return {
            "intent": "android_home",
            "target": None,
            "device": device
        }

    # --------------------------------
    # Android Back
    # --------------------------------
    if has_device and re.search(
        r"\b(go back|back)\b",
        command
    ):
        return {
            "intent": "android_back",
            "target": None,
            "device": device
        }

    # --------------------------------
    # Android Battery
    # --------------------------------
    if has_device and re.search(
        r"\bbattery\b",
        command
    ):
        return {
            "intent": "android_battery",
            "target": None,
            "device": device
        }

    # --------------------------------
    # Android Device Information
    # --------------------------------
    if re.search(
        r"\b(model|manufacturer|device info|which phone|what phone)\b",
        command
    ):
        if (
            has_device
            or re.search(
                r"\b(this phone|my phone|my device)\b",
                command
            )
        ):
            return {
                "intent": "android_device_info",
                "target": None,
                "device": device
            }

    # --------------------------------
    # Laptop Lock
    # --------------------------------
    if (
        re.search(r"\block\b", command)
        and not has_device
    ):
        return {
            "intent": "lock_device",
            "target": "laptop"
        }

    # --------------------------------
    # Android Lock
    # Feature currently skipped
    # --------------------------------
    if (
        re.search(r"\block\b", command)
        and has_device
    ):
        return {
            "intent": "android_lock",
            "target": None,
            "device": device
        }

    # --------------------------------
    # Open / Launch / Start / Run
    # --------------------------------
    action_pattern = (
        r"^(?:please\s+|can you\s+|could you\s+|would you\s+)?"
        r"(?:open|launch|start|run)\s+"
    )

    match = re.match(
        action_pattern,
        command
    )

    if not match:
        return {
            "intent": "unknown",
            "target": None
        }

    target = command[match.end():].strip()

    # --------------------------------
    # Determine Android command
    # BEFORE removing device wording
    # --------------------------------
    is_android_command = mentions_android_device(target)

    if is_android_command:
        device = find_device(target) or "phone1"

        # Remove phrases such as:
        # "on phone one"
        # "on my first phone"
        # "on realme"
        # "on kirti phone"
        # "on redmi"
        target = remove_device_from_command(target)

        # Remove common filler words
        target = re.sub(
            r"^(?:the|my|a|an|file|application|app)\s+",
            "",
            target
        ).strip()

        # Find Android application
        app_name = find_app(
            target,
            ANDROID_APPS
        )

        if app_name:
            return {
                "intent": "open_android_app",
                "target": app_name,
                "device": device
            }

        return {
            "intent": "unknown",
            "target": None
        }

    # --------------------------------
    # Windows application
    # --------------------------------
    target = re.sub(
        r"^(?:the|my|a|an|file|application|app)\s+",
        "",
        target
    ).strip()

    app_name = find_app(
        target,
        WINDOWS_APPS
    )

    if app_name:
        return {
            "intent": "open_application",
            "target": app_name
        }

    # --------------------------------
    # Windows file
    # --------------------------------
    if target:
        return {
            "intent": "open_file",
            "target": target
        }

    return {
        "intent": "unknown",
        "target": None
    }


if __name__ == "__main__":

    tests = [
        # Existing commands
        "Hey AURA, open YouTube on my phone",
        "Hey AURA, open YouTube on phone 1",
        "Hey AURA, open YouTube on phone 2",
        "Open YouTube on Android 2",
        "Hey AURA, open Notepad",
        "Lock my laptop",

        # Existing Android commands
        "Hey AURA, open Chrome on phone 1",
        "Hey AURA, open WhatsApp on phone 2",
        "Hey AURA, open Settings on phone 1",

        # Android controls
        "Hey AURA, go home on phone 1",
        "Hey AURA, go back on phone 1",
        "Hey AURA, go home on phone 2",
        "Hey AURA, go back on phone 2",

        # Device information
        "Check phone 1 battery",
        "Check phone 2 battery",
        "What is my phone model?",
        "What phone is this?",

        # Phase 3 NLU
        "Can you launch YouTube on my first phone?",
        "Start YouTube on my realme",
        "Open Chrome on the second phone",
        "Open WhatsApp on xiaomi",
        "Open WhatsApp on Kirti phone",
        "Open WhatsApps on Siddhesh phone",
        "Open YouTube on Siddhesh phone",
        "Start Chrome on Kirti phone",
    ]

    for test in tests:
        print(
            test,
            "->",
            parse_command(test)
        )

