from windows_control import (
    open_application,
    open_file,
    lock_laptop
)

from android_control import (
    open_android_app,
    android_home,
    android_back,
    get_battery_level,
    get_device_info
)


def execute_tool(tool_name, arguments):
    """
    Execute an AURA tool using the existing Python functions.
    """

    if tool_name == "open_windows_app":
        return open_application(arguments["app_name"])

    if tool_name == "open_file":
        return open_file(arguments["file_name"])

    if tool_name == "lock_laptop":
        return lock_laptop()

    if tool_name == "open_android_app":
        return open_android_app(
            arguments["app_name"],
            arguments["device"]
        )

    if tool_name == "android_home":
        return android_home(arguments["device"])

    if tool_name == "android_back":
        return android_back(arguments["device"])

    if tool_name == "get_battery_level":
        return get_battery_level(arguments["device"])

    if tool_name == "get_device_info":
        return get_device_info(arguments["device"])

    return "Unknown AURA tool."