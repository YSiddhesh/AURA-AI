import os
import time
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

CONVERSATION CONTEXT:
- Remember relevant information from previous messages.
- If the user gives a device in a previous message, remember that device
  for natural follow-up commands when the context clearly refers to it.
- Understand references such as "that phone", "the same phone", "go back",
  "go home", or "check its battery" when the previous conversation makes
  the meaning clear.
- Do not guess when the referenced device is genuinely ambiguous.
- Ask for clarification when necessary.

RULES:
- Never invent a device.
- Never invent an app.
- If a required phone is missing or ambiguous, ask which phone.
- Use tools when the user requests an actual action.
- Do not use tools for normal conversation or general questions.
- Give concise and natural responses.
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
# CONVERSATION MEMORY
# ==========================================

conversation_history = []

# ==========================================
# AURA DEVICE STATE
# ==========================================

aura_state = {
    "last_device": None,
    "last_app": None,
    "last_action": None
}

# ==========================================
# AURA BRAIN
# ==========================================

def ask_aura(user_message):

    global conversation_history
    global aura_state

    # Add the new user message
    conversation_history.append(
        {
            "role": "user",
            "text": user_message
        }
    )

    # Build context for Gemini
    context_parts = []

    for message in conversation_history:

        context_parts.append(
            f"{message['role'].upper()}: {message['text']}"
        )

    conversation_context = "\n".join(context_parts)

    state_context = f"""
    CURRENT AURA STATE:
    Last device: {aura_state["last_device"]}
    Last Android app: {aura_state["last_app"]}
    Last action: {aura_state["last_action"]}
    """

    conversation_context = (
        state_context
        + "\n\nCONVERSATION HISTORY:\n"
        + conversation_context
    )

    max_retries = 3

    for attempt in range(max_retries):

        try:

            response = client.models.generate_content(
                model="gemini-flash-latest",

                contents=conversation_context,

                config=types.GenerateContentConfig(
                    system_instruction=SYSTEM_PROMPT,
                    tools=[aura_tools]
                )
            )

            # ==================================
            # CHECK FOR TOOL CALL
            # ==================================

            for candidate in response.candidates:

                for part in candidate.content.parts:

                    if part.function_call:

                        function_call = part.function_call

                        tool_name = function_call.name
                        arguments = dict(function_call.args)

                        print(
                            f"\nAURA TOOL → {tool_name}"
                        )

                        print(
                            f"Arguments → {arguments}"
                        )

                        # Execute actual Python tool
                        result = execute_tool(
                        tool_name,
                        arguments
                    )


                    # ==================================
                    # UPDATE AURA DEVICE STATE
                    # ==================================

                    aura_state["last_action"] = tool_name

                    if "device" in arguments:
                        aura_state["last_device"] = arguments["device"]

                    if tool_name == "open_android_app":
                        aura_state["last_app"] = arguments.get("app_name")

                        # Store the tool action in memory
                        conversation_history.append(
                            {
                                "role": "assistant",
                                "text": (
                                    f"Used tool {tool_name} "
                                    f"with arguments {arguments}."
                                )
                            }
                        )

                        # Store the tool result in memory
                        conversation_history.append(
                            {
                                "role": "tool",
                                "text": str(result)
                            }
                        )

                        return result

            # ==================================
            # NORMAL GEMINI RESPONSE
            # ==================================

            answer = response.text

            conversation_history.append(
                {
                    "role": "assistant",
                    "text": answer
                }
            )

            return answer

        except Exception as e:

            error_text = str(e)

            # Retry temporary Gemini/server errors
            if "503" in error_text or "UNAVAILABLE" in error_text:

                if attempt < max_retries - 1:

                    wait_time = 2 ** attempt

                    print(
                        f"AURA: Gemini temporarily unavailable. "
                        f"Retrying in {wait_time} seconds..."
                    )

                    time.sleep(wait_time)

                else:

                    return (
                        "Gemini is temporarily unavailable. "
                        "Please try again."
                    )

            else:
                raise


# ==========================================
# CLEAR MEMORY
# ==========================================

def clear_memory():

    global conversation_history

    conversation_history = []

    print("AURA: Conversation memory cleared.")


# ==========================================
# TEST MODE
# ==========================================

if __name__ == "__main__":

    print("================================")
    print("     AURA AI - Phase 4.1")
    print("================================")
    print("Conversation Memory Enabled")
    print("Type 'clear' to clear memory.")
    print("Type 'exit' to stop.")
    print("================================\n")

    while True:

        user_input = input("You: ").strip()

        if user_input.lower() == "exit":

            print("AURA: Goodbye!")
            break

        if user_input.lower() == "clear":

            clear_memory()
            continue

        if not user_input:
            continue

        try:

            answer = ask_aura(user_input)

            print("AURA:", answer)

        except Exception as e:

            print("AURA Error:", e)

            