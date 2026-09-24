
from speech import listen
from command_parser import parse_command
from windows_control import (
    open_application,
    open_file,
    lock_laptop
)
from android_control import (
    open_android_app,
    android_home,
    android_back,
    android_lock,
    get_battery_level,
    get_device_info
)


WAKE_WORD = "hey aura"
# Stores the context of the previous command
CONTEXT = {
    "device": None,
    "target": None,
    "intent": None,
    "pending_intent": None
}

def detect_wake_word(text):
    text = text.lower().strip()
    return "hey aura" in text


def execute_command(command):
    result = parse_command(command)

    intent = result["intent"]
    entities = result.get("entities", {})

    target = entities.get("target")
    device = entities.get("device")

    # ==========================================
    # PENDING CLARIFICATION
    # ==========================================

    if CONTEXT["pending_intent"]:
        pending_intent = CONTEXT["pending_intent"]

        # User provided a phone/device as the answer
        if device:
            if pending_intent == "android_battery":
                CONTEXT["pending_intent"] = None
                return get_battery_level(device)

            if pending_intent == "android_device_info":
                CONTEXT["pending_intent"] = None
                return get_device_info(device)

            if pending_intent == "open_android_app":
                pending_target = CONTEXT["target"]
                CONTEXT["pending_intent"] = None
                return open_android_app(pending_target, device)

        # If the answer wasn't understood
        return "Please specify which phone you mean."

    # ==========================================
    # CLARIFICATION HANDLING
    # ==========================================

    # Android app command without a specific phone
    if intent == "open_android_app" and not entities.get("device"):
        CONTEXT["pending_intent"] = "open_android_app"
        CONTEXT["target"] = target
        return "Which phone should I open it on?"

    # Battery command without a specific phone
    if intent == "android_battery" and not entities.get("device"):
        CONTEXT["pending_intent"] = "android_battery"
        return "Which phone's battery should I check?"

    # Device information without a specific phone
    if intent == "android_device_info" and not entities.get("device"):
        CONTEXT["pending_intent"] = "android_device_info"
        return "Which phone should I check?"

    # ==========================================
    # CONTEXT AWARENESS
    # ==========================================


    # Remember explicitly mentioned device
    if device:
        CONTEXT["device"] = device

    # Remember target
    if target:
        CONTEXT["target"] = target

    # Remember the latest valid intent
    if intent != "unknown":
        CONTEXT["intent"] = intent

    # If no device was mentioned, use previous device
    if (
        not device
        and intent in [
            "android_home",
            "android_back"
        ]
    ):
        device = CONTEXT["device"] or "phone1"

    # ==========================================
    # WINDOWS
    # ==========================================

    if intent == "open_application":
        return open_application(target)

    if intent == "open_file":
        return open_file(target)

    if intent == "lock_device":
        return lock_laptop()

    # ==========================================
    # ANDROID
    # ==========================================

    if intent == "open_android_app":
        return open_android_app(target, device)

    if intent == "android_home":
        return android_home(device)

    if intent == "android_back":
        return android_back(device)

    if intent == "android_battery":
        return get_battery_level(device)

    if intent == "android_device_info":
        return get_device_info(device)

    if intent == "unknown":
        return (
            "I don't understand that command yet. "
            "Please try another command."
        )

    return "Sorry, something went wrong while processing the command."

print("================================")
print("        AURA AI - Phase 2")
print("================================")
print("AURA is waiting for the wake word...")
print("Say: Hey Aura")
print("================================")



while True:
    try:
        # ==========================================
        # NORMAL MODE / CLARIFICATION MODE
        # ==========================================

        if CONTEXT["pending_intent"]:
            # AURA is waiting for the user's clarification answer
            text = listen(duration=5)

            if not text:
                print("AURA: I didn't hear your answer.")
                continue

            print("Heard:", text)

            response = execute_command(text)
            print("AURA:", response)

        else:
            # Normal mode: wait for wake word
            text = listen(duration=3)

            if detect_wake_word(text):
                print("\nAURA: Yes? How can I help?")

                command = listen(duration=5)

                if not command:
                    print("AURA: I didn't hear a command.")
                    continue

                response = execute_command(command)
                print("AURA:", response)

            else:
                print("AURA: Wake word not detected.")

    except KeyboardInterrupt:
        print("\nAURA: Goodbye!")
        break

    except Exception as e:
        print("AURA Error:", e)




        