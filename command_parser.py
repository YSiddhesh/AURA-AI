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

    command = command.lower()

    for device, aliases in DEVICE_ALIASES.items():
        for alias in aliases:
            pattern = (
                rf"\b(?:on|in)\s+"
                rf"(?:my|the)?\s*"
                rf"{re.escape(alias.lower())}\b"
            )

            command = re.sub(pattern, "", command)

    return command.strip()


def parse_command(command):

    command = clean_command(command)

    if not command:
        return build_result("unknown")

    # --------------------------------
    # Detect device
    # --------------------------------
    device = find_device(command) or "phone1"

    has_device = mentions_android_device(command)

    # --------------------------------
    # Android Home
    # --------------------------------
    if has_device and re.search(
        r"\b(go home|home)\b",
        command
    ):
        return build_result(
            "android_home",
            device=device
        )

    # --------------------------------
    # Android Back
    # --------------------------------
    if has_device and re.search(
        r"\b(go back|back)\b",
        command
    ):
        return build_result(
            "android_back",
            device=device
        )

    # --------------------------------
    # Android Battery
    # --------------------------------
    if has_device and re.search(
        r"\bbattery\b",
        command
    ):
        return build_result(
            "android_battery",
            device=device
        )

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
            return build_result(
                "android_device_info",
                device=device
            )

    # --------------------------------
    # Laptop Lock
    # --------------------------------
    if (
        re.search(r"\block\b", command)
        and not has_device
    ):
        return build_result(
            "lock_device",
            target="laptop"
        )

    # --------------------------------
    # Android Lock
    # Feature currently skipped
    # --------------------------------
    if (
        re.search(r"\block\b", command)
        and has_device
    ):
        return build_result(
            "android_lock",
            device=device
        )

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
        return build_result("unknown")

    target = command[match.end():].strip()

    # --------------------------------
    # Determine Android command
    # --------------------------------
    is_android_command = mentions_android_device(target)

    if is_android_command:

        device = find_device(target) or "phone1"

        target = remove_device_from_command(target)

        target = re.sub(
            r"^(?:the|my|a|an|file|application|app)\s+",
            "",
            target
        ).strip()

        app_name = find_app(
            target,
            ANDROID_APPS
        )

        if app_name:
            return build_result(
                "open_android_app",
                target=app_name,
                device=device
            )

        return build_result("unknown")

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
        return build_result(
            "open_application",
            target=app_name
        )

    # --------------------------------
    # Windows file
    # --------------------------------
    if target:
        return build_result(
            "open_file",
            target=target
        )

    return build_result("unknown")


# --------------------------------
# TESTING
# --------------------------------

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