import subprocess
import re

ANDROID_DEVICES = {
    "phone1": "EA4989MFDEI7Y9Z5",  # realme RMX3201
    "phone2": "CQLRYPWGNZBMHEW8",  # Xiaomi 23128PC33I
}

ANDROID_APPS = {
    "youtube": "com.google.android.youtube",
    "chrome": "com.android.chrome",
    "whatsapp": "com.whatsapp",
    "settings": "com.android.settings",
}


def run_adb(device, command):
    result = subprocess.run(
        ["adb", "-s", ANDROID_DEVICES[device], *command],
        capture_output=True,
        text=True
    )

    if result.returncode != 0:
        return f"ADB Error: {result.stderr.strip()}"

    return result.stdout.strip()


def open_android_app(app_name, device="phone1"):
    app_name = app_name.lower().strip()
    package_name = ANDROID_APPS.get(app_name)

    if device not in ANDROID_DEVICES:
        return "Sorry, that phone is not configured."

    if not package_name:
        return f"Sorry, {app_name} is not in the approved Android app list."

    run_adb(device, ["shell", "monkey", "-p", package_name, "1"])
    return f"Sent command to open {app_name} on {device}."

def get_battery_level(device="phone1"):
    output = run_adb(
        device,
        ["shell", "dumpsys", "battery"]
    )

    match = re.search(r"level:\s*(\d+)", output)

    if match:
        return f"Phone {device[-1]} battery is {match.group(1)} percent."

    return "Sorry, I could not read the battery level."

def get_battery_level(device="phone1"):
    output = run_adb(device, ["shell", "dumpsys", "battery"])

    if output.startswith("ADB Error:"):
        return f"{device} is not available."

    match = re.search(r"level:\s*(\d+)", output)

    if match:
        return f"{device} battery is {match.group(1)} percent."

    return f"Could not read the battery level for {device}."


def get_device_info(device="phone1"):
    manufacturer = run_adb(
        device,
        ["shell", "getprop", "ro.product.manufacturer"]
    )
    model = run_adb(
        device,
        ["shell", "getprop", "ro.product.model"]
    )

    if manufacturer.startswith("ADB Error:") or model.startswith("ADB Error:"):
        return f"{device} is not available."

    return f"{device} is {manufacturer} {model}."

def get_device_info(device="phone1"):
    model = run_adb(
        device,
        ["shell", "getprop", "ro.product.model"]
    )

    manufacturer = run_adb(
        device,
        ["shell", "getprop", "ro.product.manufacturer"]
    )

    return f"Phone {device[-1]} is {manufacturer} {model}."

def android_home(device="phone1"):
    run_adb(device, ["shell", "input", "keyevent", "KEYCODE_HOME"])
    return f"Returned {device} to the home screen."


def android_back(device="phone1"):
    run_adb(device, ["shell", "input", "keyevent", "KEYCODE_BACK"])
    return f"Pressed back on {device}."


def android_lock(device="phone1"):
    run_adb(device, ["shell", "input", "keyevent", "KEYCODE_POWER"])
    return f"Locked {device}."

if __name__ == "__main__":
    print(open_android_app("youtube", "phone1"))
    print(open_android_app("youtube", "phone2"))