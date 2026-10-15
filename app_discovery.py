
import difflib
import json
import os
import re
import shutil
import subprocess
from pathlib import Path

from android_control import ANDROID_DEVICES


# --------------------------------------------------
# ADB CONFIGURATION
# --------------------------------------------------

PROJECT_DIR = Path(__file__).resolve().parent

LOCAL_ADB = (
    PROJECT_DIR
    / "android_voice_control"
    / "platform-tools"
    / "adb.exe"
)

ADB = str(LOCAL_ADB) if LOCAL_ADB.exists() else (
    shutil.which("adb") or "adb"
)


def normalize_name(name):
    """Normalize application names for matching."""
    return re.sub(r"[^a-z0-9]+", "", name.lower())


def best_match(app_name, candidates):
    """
    Match the requested name against discovered applications.
    Returns the best candidate or None.
    """
    wanted = normalize_name(app_name)

    if not wanted:
        return None

    # Exact match
    for candidate in candidates:
        if normalize_name(candidate) == wanted:
            return candidate

    # Partial or fuzzy match
    scored = []

    for candidate in candidates:
        name = normalize_name(candidate)

        if wanted in name or name in wanted:
            score = 0.90
        else:
            score = difflib.SequenceMatcher(
                None, wanted, name
            ).ratio()

        scored.append((score, candidate))

    if not scored:
        return None

    score, candidate = max(scored, key=lambda item: item[0])

    # Avoid launching a completely unrelated application.
    return candidate if score >= 0.78 else None


# --------------------------------------------------
# WINDOWS APPLICATION DISCOVERY
# --------------------------------------------------

def get_windows_apps():
    """Discover apps registered in the Windows Start menu."""
    script = (
        "Get-StartApps | "
        "Select-Object Name, AppID | "
        "ConvertTo-Json -Compress"
    )

    result = subprocess.run(
        [
            "powershell",
            "-NoProfile",
            "-Command",
            script,
        ],
        capture_output=True,
        text=True,
        timeout=20,
    )

    if result.returncode != 0:
        return []

    try:
        data = json.loads(result.stdout or "[]")

        if isinstance(data, dict):
            data = [data]

        return [
            item for item in data
            if item.get("Name") and item.get("AppID")
        ]

    except (json.JSONDecodeError, TypeError):
        return []


def open_windows_app_dynamic(app_name):
    """Find and launch an installed Windows Start-menu app."""
    apps = get_windows_apps()

    names = [item["Name"] for item in apps]
    match = best_match(app_name, names)

    if not match:
        return {
            "success": False,
            "message": (
                f"{app_name} was not found in "
                "the Windows Start-menu applications."
            ),
        }

    app = next(item for item in apps if item["Name"] == match)

    try:
        subprocess.Popen(
            [
                "explorer.exe",
                f"shell:AppsFolder\\{app['AppID']}",
            ]
        )

        return {
            "success": True,
            "message": f"Launch request sent for {match} on Windows.",
        }

    except OSError as error:
        return {
            "success": False,
            "message": f"Could not launch {match}: {error}",
        }


# --------------------------------------------------
# ANDROID APPLICATION DISCOVERY
# --------------------------------------------------

def run_adb_for_device(device, *args):
    """Run an ADB command on exactly one selected phone."""
    if device not in ANDROID_DEVICES:
        raise ValueError(f"Unknown Android device: {device}")

    serial = ANDROID_DEVICES[device]

    return subprocess.run(
        [ADB, "-s", serial, *args],
        capture_output=True,
        text=True,
        timeout=20,
    )


def get_android_packages(device):
    """Discover installed Android package IDs on one phone."""
    result = run_adb_for_device(
        device, "shell", "pm", "list", "packages"
    )

    if result.returncode != 0:
        raise RuntimeError(
            result.stderr.strip() or "Could not list Android packages."
        )

    packages = []

    for line in result.stdout.splitlines():
        line = line.strip()

        if line.startswith("package:"):
            packages.append(line.split(":", 1)[1].strip())

    return packages


def open_android_app_dynamic(app_name, device):
    """
    Search only the selected phone.
    Do not silently switch to the other phone if the app is missing.
    """
    try:
        packages = get_android_packages(device)
    except (RuntimeError, OSError, subprocess.SubprocessError) as error:
        return {
            "success": False,
            "message": f"Cannot inspect {device}: {error}",
        }

    # Android package IDs are discovered dynamically.
    # For example, com.spotify.music contains 'spotify'.
    package = best_match(app_name, packages)

    if not package:
        return {
            "success": False,
            "message": (
                f"{app_name} was not matched to an installed "
                f"package on {device}. No other device was searched."
            ),
        }

    # Confirm that the package has a launchable main activity.
    try:
        activity = run_adb_for_device(
            device,
            "shell",
            "cmd",
            "package",
            "resolve-activity",
            "--brief",
            "-a",
            "android.intent.action.MAIN",
            "-c",
            "android.intent.category.LAUNCHER",
            package,
        )

        if (
            activity.returncode != 0
            or "No activity found" in activity.stdout
            or not activity.stdout.strip()
        ):
            return {
                "success": False,
                "message": (
                    f"{app_name} was matched to {package}, "
                    "but no launchable activity was found."
                ),
            }

        launch = run_adb_for_device(
            device, "shell", "monkey", "-p", package, "1"
        )

        if launch.returncode != 0:
            return {
                "success": False,
                "message": (
                    f"Android could not launch {app_name} "
                    f"on {device}: {launch.stderr.strip()}"
                ),
            }

        return {
            "success": True,
            "message": (
                f"Launch request sent for {app_name} "
                f"({package}) on {device}."
            ),
        }

    except (OSError, subprocess.SubprocessError) as error:
        return {
            "success": False,
            "message": f"Could not launch the app: {error}",
        }


# --------------------------------------------------
# MAIN DEVICE ROUTER
# --------------------------------------------------

def open_app_on_device(app_name, device):
    """Search and launch an app on the requested device only."""
    if not app_name or not app_name.strip():
        return {
            "success": False,
            "message": "No application name was provided.",
        }

    app_name = app_name.strip()
    device = device.lower().strip()

    if device in ("windows", "laptop", "computer"):
        return open_windows_app_dynamic(app_name)

    if device in ANDROID_DEVICES:
        return open_android_app_dynamic(app_name, device)

    return {
        "success": False,
        "message": (
            "Unknown target device. Use windows, phone1, or phone2."
        ),
    }


# --------------------------------------------------
# DIRECT TEST
# --------------------------------------------------

if __name__ == "__main__":
    app = input("Application name: ").strip()
    target = input("Device (windows/phone1/phone2): ").strip()

    print(open_app_on_device(app, target))


