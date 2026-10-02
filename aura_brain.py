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

Understand natural language.

For Android commands:
- phone 1 means phone1
- phone one means phone1
- mobile 1 means phone1
- mobile one means phone1
- phone 2 means phone2
- phone two means phone2
- mobile 2 means phone2
- mobile two means phone2

Do not invent devices.

If a required device is missing, ask the user which phone they mean.

When a tool is available and the user requests that action,
use the tool instead of merely explaining what could be done.

After a tool executes, tell the user the result naturally.
"""


# ==========================================
# GEMINI TOOL DEFINITIONS
# ==========================================

open_android_app_tool = types.FunctionDeclaration(
    name="open_android_app",
    description="Open an approved Android application on phone 1 or phone 2.",
    parameters=types.Schema(
        type=types.Type.OBJECT,
        properties={
            "app_name": types.Schema(
                type=types.Type.STRING,
                description="Android app to open, such as youtube, chrome, whatsapp, or settings."
            ),
            "device": types.Schema(
                type=types.Type.STRING,
                enum=["phone1", "phone2"],
                description="The Android phone on which to open the application."
            )
        },
        required=["app_name", "device"]
    )
)


aura_tools = types.Tool(
    function_declarations=[open_android_app_tool]
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

    # Check whether Gemini requested a tool
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

                # Execute the actual Python function
                result = execute_tool(
                    tool_name,
                    arguments
                )

                return result

    # Normal Gemini response
    return response.text


# ==========================================
# TEST MODE
# ==========================================

if __name__ == "__main__":

    print("================================")
    print("     AURA AI - Tool Brain")
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