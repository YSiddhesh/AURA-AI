import subprocess
from pathlib import Path


def open_application(app_name):
    applications = {
        "notepad": "notepad.exe",
        "calculator": "calc.exe",
        "paint": "mspaint.exe",
    }

    app_name = app_name.lower().strip()

    if app_name in applications:
        subprocess.Popen(applications[app_name])
        return f"{app_name.title()} opened successfully."

    return f"Application '{app_name}' is not available."


def open_file(file_name):
    search_locations = [
        Path.home() / "Desktop",
        Path.home() / "Documents",
        Path.home() / "Downloads",
    ]

    file_name = file_name.lower().strip()

    for location in search_locations:

        if not location.exists():
            continue

        for file in location.rglob("*"):

            if file.is_file() and file.name.lower() == file_name:
                subprocess.Popen(["explorer", str(file)])
                return f"Opened {file.name}."

    return f"File '{file_name}' was not found."


def lock_laptop():
    subprocess.run(
        ["rundll32.exe", "user32.dll,LockWorkStation"]
    )

    return "Laptop locked."