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
    Execute an AURA tool and classify execution failures.
    """

    try:
        if tool_name == "open_windows_app":
            result = open_application(arguments["app_name"])

        elif tool_name == "open_file":
            result = open_file(arguments["file_name"])

        elif tool_name == "lock_laptop":
            result = lock_laptop()

        elif tool_name == "open_android_app":
            result = open_android_app(
                arguments["app_name"],
                arguments["device"]
            )

        elif tool_name == "android_home":
            result = android_home(arguments["device"])

        elif tool_name == "android_back":
            result = android_back(arguments["device"])

        elif tool_name == "get_battery_level":
            result = get_battery_level(arguments["device"])

        elif tool_name == "get_device_info":
            result = get_device_info(arguments["device"])

        else:
            return {
                "status": "failure",
                "error_type": "unknown_tool",
                "message": f"Unknown AURA tool: {tool_name}"
            }

            
        # Detect empty results.
        if result is None:
            return {
                "status": "failure",
                "error_type": "empty_result",
                "message": f"{tool_name} returned no result."
            }

        # Detect failures reported as text by control functions.
        if isinstance(result, str):
            
            failure_phrases = [
                "not available",
                "not found",
                "failed",
                "failure",
                "error",
                "unable to",
                "could not",
                "adb error",
                "not configured",
                "not in the approved"
            ]


            if any(phrase in result.lower() for phrase in failure_phrases):
                return {
                    "status": "failure",
                    "error_type": "tool_failure",
                    "tool": tool_name,
                    "message": result
                }

        # Return successful results.
        return {
            "status": "success",
            "tool": tool_name,
            "result": result
        }


    except KeyError as error:
        return {
            "status": "failure",
            "error_type": "missing_argument",
            "message": f"Missing required argument: {error}"
        }

    except Exception as error:
        return {
            "status": "failure",
            "error_type": "execution_error",
            "message": str(error),
            "tool": tool_name
        }
