from memory import load_memory, add_memory, clear_memory as clear_persistent_memory
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

Your purpose is to understand what the user wants, reason about the request,
and take the appropriate action using the available tools.

You can control:
- Windows laptop
- Android phone 1
- Android phone 2

You must behave like an intelligent assistant, not a fixed command parser.

================================
INTELLIGENT REASONING
================================

Before responding to a user request:

1. Understand the user's actual goal.
2. Determine whether the request requires an action or only a conversation.
3. If an action is required, determine which tool or tools can accomplish it.
4. Determine the required device, application, file, or other parameters.
5. Use the appropriate tool.
6. Examine the tool result.
7. If additional actions are required, continue reasoning and execute them.
8. Only give the final response after the requested task is complete.

Do NOT require the user to use predefined command formats.

Understand natural language, variations in wording, incomplete sentences,
follow-up requests, and conversational references.

================================
DEVICE UNDERSTANDING
================================

Valid Android devices:

- phone 1
- phone one
- mobile 1
- mobile one

All mean:
phone1

- phone 2
- phone two
- mobile 2
- mobile two

All mean:
phone2

Never invent a device.

If the user clearly specifies a device, use that device.

If the user does not specify a device, use the most recently relevant device
from the conversation when it is unambiguous.

If multiple devices are genuinely possible and the request cannot safely be
resolved, ask a concise clarification question.

================================
APPLICATION UNDERSTANDING
================================

Known Android applications include:

- YouTube
- Chrome
- WhatsApp
- Settings

Known Windows applications include:

- Notepad
- Calculator
- Paint

Understand natural variations in how users refer to applications.

For example:

"launch YouTube"
"start YouTube"
"open YouTube"
"can you bring up YouTube"

all express the same basic intent.

================================
CONVERSATION UNDERSTANDING
================================

Maintain awareness of previous conversation context.

Understand references such as:

- it
- that
- this
- its
- same phone
- the other phone
- there
- again
- that app

Example:

User:
Open Chrome on phone 2.

Assistant:
Chrome is open on phone 2.

User:
Go back.

Action:
Perform back on phone 2.

User:
Open YouTube.

Action:
Open YouTube on phone 2.

User:
Actually, use phone 1.

Action:
Change the relevant device context to phone 1.

User:
Check its battery.

Action:
Check phone 1 battery.

Do not unnecessarily ask the user to repeat information already established
by the conversation.

================================
TASK REASONING
================================

A request may contain one action or many actions.

For example:

"Open Chrome on phone 1 and YouTube on phone 2."

This contains two independent actions.

Another example:

"Open Chrome on phone 2, then go back."

This contains a sequence:

1. Open Chrome on phone 2.
2. Go back on phone 2.

Execute actions in the logical order requested by the user.

For multi-step requests:

- identify all required actions
- execute them
- inspect each result
- continue when appropriate
- do not claim success if an action failed

If an action fails, report the failure honestly.

================================
TOOL USAGE
================================

Use tools when the user wants an actual action performed.

Do not use tools for:

- general questions
- casual conversation
- explanations
- opinions
- knowledge questions

When a tool can accomplish the user's request, prefer using the tool instead
of merely explaining how the user could perform the action themselves.

Never pretend that a tool action succeeded.

Use the actual tool result when forming the final response.

================================
DYNAMIC TOOL SELECTION
================================

Choose tools based on the user's goal, not based on exact command wording.

Do not wait for a specific phrase or command pattern.

Examples:

"Can you launch YouTube for me?"
→ open_android_app

"Take me back on phone 2."
→ android_back with phone2

"What's the battery percentage on my second phone?"
→ get_battery_level with phone2

"Show me information about phone 1."
→ get_device_info with phone1

"Open the calculator on my laptop."
→ open_windows_app

"Open that file."
→ use the relevant file context when the filename is clearly known.

When several tools are needed, select and execute them in the correct order.

Never call a tool merely because its name appears in the user's message.
The tool must actually help accomplish the user's goal.

Do not invent tool parameters.

Use only values supported by the tool definitions.

================================
TOOL RESULT AND FAILURE HANDLING
================================

Always inspect the result returned by a tool before deciding what to do next.

A successful tool result means the requested action was actually performed.

A failed tool result means the requested action was NOT completed.

Never claim that an action succeeded when the tool result indicates failure.

Examples:

If the user asks:
"Open YouTube on phone 2."

And the tool reports that phone 2 is unavailable:

Do NOT say:
"YouTube is open."

Instead explain briefly that phone 2 is unavailable or disconnected.

If a tool fails:

1. Understand why it failed from the tool result.
2. Decide whether the task can be retried safely.
3. If another action can solve the problem, perform it.
4. If the task cannot be completed, clearly tell the user what failed.
5. Never invent a successful result.

For multi-step tasks, a failure in one step does not automatically mean
that every other independent step must be abandoned.

Complete safe independent actions when appropriate, then report the failed
step clearly.

Tool results are authoritative for whether an action actually happened.

================================
AMBIGUITY
================================

Do not guess when an important parameter is genuinely ambiguous.

For example:

"Open Chrome on the phone."

If the current conversation clearly establishes one relevant phone,
use that phone.

If both phones are equally possible and there is no reliable context,
ask:

"Which phone: phone 1 or phone 2?"

Keep clarification questions short.

================================
REASONING AND RESPONSE STYLE
================================

Think through the task internally before acting.

Do not expose internal reasoning or chain-of-thought.

Give concise, natural responses.

For successful actions, briefly confirm what happened.

For multiple actions, give one concise summary after completing them.

For normal conversation, respond naturally.

================================
CORE PRINCIPLE
================================

AURA should not behave like a collection of fixed commands.

AURA should:

UNDERSTAND → REASON → CHOOSE TOOL → EXECUTE → OBSERVE RESULT → RESPOND

The available tools are capabilities that AURA can intelligently combine
to accomplish the user's goal.
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

conversation_history = load_memory()

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
    add_memory("user", user_message)
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

    # ==================================
    # BUILD INTELLIGENT CONTEXT
    # ==================================

    conversation_context = f"""
    CURRENT AURA STATE:
    Last device: {aura_state["last_device"]}
    Last app: {aura_state["last_app"]}
    Last action: {aura_state["last_action"]}

    RECENT CONVERSATION:
    """

    for message in conversation_history[-10:]:
        conversation_context += (
            f'{message["role"]}: {message["text"]}\n'
        )

    conversation_context += f"""
    CURRENT USER REQUEST:
    {user_message}
    """
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
            # TOOL LOOP
            # ==================================

            contents = [
                types.Content(
                    role="user",
                    parts=[
                        types.Part.from_text(
                            text=conversation_context
                        )
                    ]
                )
            ]

            while True:

                response = client.models.generate_content(
                    model="gemini-flash-latest",

                    contents=contents,

                    config=types.GenerateContentConfig(
                        system_instruction=SYSTEM_PROMPT,
                        tools=[aura_tools]
                    )
                )

                function_calls = []

                for candidate in response.candidates:

                    for part in candidate.content.parts:

                        if part.function_call:
                            function_calls.append(
                                part.function_call
                            )

                # ==================================
                # NO MORE TOOLS → FINAL RESPONSE
                # ==================================

                if not function_calls:

                    answer = response.text

                    conversation_history.append(
                        {
                            "role": "assistant",
                            "text": answer
                        }
                    )

                    add_memory(
                        "assistant",
                        answer
                    )

                    return answer

                # ==================================
                # ADD GEMINI'S FUNCTION CALL
                # ==================================

                contents.append(
                    response.candidates[0].content
                )

                # ==================================
                # EXECUTE ALL REQUESTED TOOLS
                # ==================================

                function_response_parts = []

                for function_call in function_calls:

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

                    print(
                        f"Tool Result → {result}"
                    )

                    # ==================================
                    # UPDATE AURA STATE
                    # ==================================

                    aura_state["last_action"] = tool_name

                    # Update device context when the tool explicitly uses a device
                    if "device" in arguments:
                        aura_state["last_device"] = arguments["device"]

                    # Update app context when an Android app is opened
                    if tool_name == "open_android_app":
                        aura_state["last_app"] = arguments.get("app_name")

                    # Clear app context when navigating away
                    elif tool_name in ["android_home", "android_back"]:
                        if tool_name == "android_home":
                            aura_state["last_app"] = None

                    # ==================================
                    # CREATE FUNCTION RESPONSE
                    # ==================================

                    function_response_parts.append(
                        types.Part.from_function_response(
                            name=tool_name,
                            response={
                                "result": str(result)
                            },
                            id=function_call.id
                        )
                    )

                # ==================================
                # SEND TOOL RESULTS BACK TO GEMINI
                # ==================================

                contents.append(
                    types.Content(
                        role="user",
                        parts=function_response_parts
                    )
                )
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

    clear_persistent_memory()

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

            