import os
from dotenv import load_dotenv
from google import genai
from google.genai import types

from tool_router import execute_tool


# ==========================================
# LOAD GEMINI API KEY
# ==========================================

load_dotenv()

api_key = os.getenv("GEMINI_API_KEY")

if not api_key:
    raise ValueError(
        "GEMINI_API_KEY not found. Check your .env file."
    )


# ==========================================
# GEMINI CLIENT
# ==========================================

client = genai.Client(api_key=api_key)


# ==========================================
# AURA SYSTEM INSTRUCTIONS
# ==========================================

SYSTEM_PROMPT = """
You are AURA, an intelligent personal AI assistant.

You can control:
- Windows laptop
- Android phone 1
- Android phone 2

Understand natural human language instead of requiring fixed commands.

DEVICE NAMES:
- phone 1, phone one, mobile 1, mobile one = phone1
- phone 2, phone two, mobile 2, mobile two = phone2

ANDROID APPS:
- YouTube = youtube
- Chrome = chrome
- WhatsApp = whatsapp
- Settings = settings

Rules:
- Never invent a device.
- Never invent an app.
- If a required phone is missing, ask which phone.
- Use tools when the user requests an actual action.
- After a tool executes, report the result naturally.
"""


# ==========================================
# TOOL DEFINITIONS
# ==========================================

open_windows_app = types.FunctionDeclaration(
    name="open_windows_app",
    description="Open an approved application on the Windows laptop.",
    parameters=types.Schema(
        type=types.Type.OBJECT,
        properties={
            "app_name": types.Schema(
                type=types.Type.STRING,
                description="Windows application such as notepad, calculator, or paint."
            )
        },
        required=["app_name"]
    )
)


open_file = types.FunctionDeclaration(
    name="open_file",
    description="Open a file on the Windows laptop.",
    parameters=types.Schema(
        type=types.Type.OBJECT,
        properties={
            "file_name": types.Schema(
                type=types.Type.STRING,
                description="Name or path of the file to open."
            )
        },
        required=["file_name"]
    )
)


lock_laptop = types.FunctionDeclaration(
    name="lock_laptop",
    description="Lock the Windows laptop.",
    parameters=types.Schema(
        type=types.Type.OBJECT,
        properties={}
    )
)


open_android_app = types.FunctionDeclaration(
    name="open_android_app",
    description="Open an approved Android application on phone 1 or phone 2.",
    parameters=types.Schema(
        type=types.Type.OBJECT,
        properties={
            "app_name": types.Schema(
                type=types.Type.STRING,
                description="Android app: youtube, chrome, whatsapp, or settings."
            ),
            "device": types.Schema(
                type=types.Type.STRING,
                enum=["phone1", "phone2"],
                description="Android phone to control."
            )
        },
        required=["app_name", "device"]
    )
)


android_home = types.FunctionDeclaration(
    name="android_home",
    description="Return an Android phone to its home screen.",
    parameters=types.Schema(
        type=types.Type.OBJECT,
        properties={
            "device": types.Schema(
                type=types.Type.STRING,
                enum=["phone1", "phone2"]
            )
        },
        required=["device"]
    )
)


android_back = types.FunctionDeclaration(
    name="android_back",
    description="Press the back button on an Android phone.",
    parameters=types.Schema(
        type=types.Type.OBJECT,
        properties={
            "device": types.Schema(
                type=types.Type.STRING,
                enum=["phone1", "phone2"]
            )
        },
        required=["device"]
    )
)


get_battery_level = types.FunctionDeclaration(
    name="get_battery_level",
    description="Check the battery percentage of an Android phone.",
    parameters=types.Schema(
        type=types.Type.OBJECT,
        properties={
            "device": types.Schema(
                type=types.Type.STRING,
                enum=["phone1", "phone2"]
            )
        },
        required=["device"]
    )
)


get_device_info = types.FunctionDeclaration(
    name="get_device_info",
    description="Get the manufacturer and model of an Android phone.",
    parameters=types.Schema(
        type=types.Type.OBJECT,
        properties={
            "device": types.Schema(
                type=types.Type.STRING,
                enum=["phone1", "phone2"]
            )
        },
        required=["device"]
    )
)


# ==========================================
# AURA TOOL COLLECTION
# ==========================================

aura_tools = types.Tool(
    function_declarations=[
        open_windows_app,
        open_file,
        lock_laptop,
        open_android_app,
        android_home,
        android_back,
        get_battery_level,
        get_device_info
    ]
)


# ==========================================
# AURA BRAIN
# ==========================================

def ask_aura(user_message):

    response = client.models.generate_content(
        model="gemini-flash-latest",
        contents=user_message,
        config=types.GenerateContentConfig(
            system_instruction=SYSTEM_PROMPT,
            tools=[aura_tools]
        )
    )

    for candidate in response.candidates:

        for part in candidate.content.parts:

            if part.function_call:

                function_call = part.function_call

                tool_name = function_call.name
                arguments = dict(function_call.args)

                print(f"\nAURA TOOL → {tool_name}")
                print(f"Arguments → {arguments}")

                result = execute_tool(
                    tool_name,
                    arguments
                )

                return result

    return response.text


# ==========================================
# TEST MODE
# ==========================================

if __name__ == "__main__":

    print("================================")
    print("     AURA AI - Full Tool Brain")
    print("================================")
    print("Type 'exit' to stop.")
    print("================================\n")

    while True:

        user_input = input("You: ").strip()

        if user_input.lower() == "exit":
            print("AURA: Goodbye!")
            break

        if not user_input:
            continue

        try:

            answer = ask_aura(user_input)

            print("AURA:", answer)

        except Exception as e:

            print("AURA Error:", e)