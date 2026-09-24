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


# ==========================================
# ANDROID DEVICE NAMES
# ==========================================

DEVICE_ALIASES = {
    "phone1": [
        "siddhesh phone",
        "phone 1",
        "phone one",
        "mobile 1",
        "mobile one",
    ],

    "phone2": [
        "aai phone",
        "phone 2",
        "phone two",
        "mobile 2",
        "mobile two",
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

    # Remove "Aura" from commands.
    # Examples:
    # Aura, open YouTube
    # Aura open YouTube
    command = re.sub(
        r"\baura\b",
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

            command = re.sub(
                pattern,
                "",
                command
            )

    return command.strip()

def uses_previous_device(command):
    return bool(
        re.search(
            r"\b(its|that phone|this phone|same phone|there)\b",
            command.lower()
        )
    )

def parse_command(command):

    command = clean_command(command)

    if not command:
        return build_result("unknown")

    # ==========================================
    # DETECT DEVICE
    # ==========================================

    device = find_device(command)

    has_device = mentions_android_device(command)

    uses_context = uses_previous_device(command)

    if device:
        has_device = True

    if uses_context and not device:
            device = None
            has_device = True

    # ==========================================
    # ANDROID HOME
    # ==========================================

    if has_device and re.search(
        r"\b(go home|home)\b",
        command
    ):
        return build_result(
            "android_home",
            device=device
        )

    # ==========================================
    # ANDROID BACK
    # ==========================================

    if has_device and re.search(
        r"\b(go back|back)\b",
        command
    ):
        return build_result(
            "android_back",
            device=device
        )

    # ==========================================
    # ANDROID BATTERY
    # ==========================================

    if re.search(r"\b(check|show|tell|what is|what's)\b.*\bbattery\b", command):
        return build_result("android_battery", device=device if has_device else None)

    # ==========================================
    # ANDROID DEVICE INFORMATION
    # ==========================================

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

    # ==========================================
    # LAPTOP LOCK
    # ==========================================

    if (
        re.search(r"\block\b", command)
        and not has_device
    ):
        return build_result(
            "lock_device",
            target="laptop"
        )

    # ==========================================
    # ANDROID LOCK
    # SKIPPED FEATURE
    # ==========================================

    if (
        re.search(r"\block\b", command)
        and has_device
    ):
        return build_result(
            "android_lock",
            device=device
        )

    # ==========================================
    # OPEN / LAUNCH / START / RUN
    # ==========================================

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

    # ==========================================
    # ANDROID COMMAND
    # ==========================================

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

    # ==========================================
    # WINDOWS APPLICATION
    # ==========================================

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

    # ==========================================
    # WINDOWS FILE
    # ==========================================

    if target:
        return build_result(
            "open_file",
            target=target
        )

    return build_result("unknown")


# ==========================================
# TESTING
# ==========================================

if __name__ == "__main__":

    tests = [

        # Wake/command style
        "Aura, open YouTube on Siddhesh phone",
        "Aura, open YouTube on Aai phone",

        # Android applications
        "Aura, open Chrome on Siddhesh phone",
        "Aura, open WhatsApp on Aai phone",
        "Aura, open Settings on Siddhesh phone",

        # Android controls
        "Aura, go home on Siddhesh phone",
        "Aura, go back on Siddhesh phone",
        "Aura, go home on Aai phone",
        "Aura, go back on Aai phone",

        # Battery
        "Aura, check Siddhesh phone battery",
        "Aura, check Aai phone battery",

        # Device information
        "Aura, what is Siddhesh phone model",
        "Aura, what is Aai phone model",

        # Windows
        "Aura, open Notepad",
        "Aura, open Calculator",
        "Aura, open Paint",
        "Aura, lock my laptop",
    ]

    for test in tests:
        print(
            test,
            "->",
            parse_command(test)
        )

print(parse_command("check battery"))
print(parse_command("check battery on phone 1"))
print(parse_command("check battery on phone 2"))