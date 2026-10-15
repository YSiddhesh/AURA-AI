import json
import os
import time
from dotenv import load_dotenv
from google import genai
from google.genai import types
from memory import load_memory, add_memory, clear_memory as clear_persistent_memory
from tool_router import execute_tool

load_dotenv()

MODEL = "gemini-3.8-flash"
MAX_MODEL_RETRIES = 3
MAX_TOOL_ROUNDS = 12

api_key = os.getenv("GEMINI_API_KEY")
if not api_key:
    raise RuntimeError("GEMINI_API_KEY is missing. Add it to your .env file.")

client = genai.Client(api_key=api_key)

SYSTEM_PROMPT = """
You are AURA, a practical AI assistant that can answer questions and control the
user's Windows laptop and two Android phones through the available tools.

Planning and execution rules:
1. Break multi-action requests into a clear ordered plan internally.
2. Use tools for real device actions and device information; never claim an action
   succeeded unless its returned result supports that conclusion.
3. A tool response is authoritative. Inspect its status and message before deciding
   what to do next.
4. AURA's Python runtime executes at most one real tool action per model response.
   If other calls were deferred, reconsider them after receiving the tool results.
5. If an action fails, do not repeat it automatically and do not execute an action
   that depends on the failed action. Independent actions may still be performed
   when safe and relevant.
6. Preserve explicit targets: Windows uses target "windows"; Android devices use
   "phone1" and "phone2". Never silently redirect an action to another device.
7. Use open_app_on_device for applications that are not covered by the predefined
   app tools. It must target the requested device.
8. Keep tool arguments accurate and do not invent filenames, app availability,
   battery levels, device details, or execution results.
9. Once the requested work is complete, give a concise summary of successes and
   failures. If a target device is ambiguous, ask a clarifying question instead
   of guessing.
10. Do not expose hidden reasoning. Provide only a brief explanation or plan when
    useful.
""".strip()

DEVICE_SCHEMA = {
    "type": "STRING",
    "enum": ["phone1", "phone2"],
}

FUNCTION_DECLARATIONS = [
    {
        "name": "open_windows_app",
        "description": "Open an approved application on the Windows laptop.",
        "parameters": {
            "type": "OBJECT",
            "properties": {
                "app_name": {
                    "type": "STRING",
                    "enum": ["notepad", "calculator", "paint"],
                }
            },
            "required": ["app_name"],
        },
    },
    {
        "name": "open_file",
        "description": "Open a file by its exact filename on Windows.",
        "parameters": {
            "type": "OBJECT",
            "properties": {"file_name": {"type": "STRING"}},
            "required": ["file_name"],
        },
    },
    {
        "name": "lock_laptop",
        "description": "Lock the Windows laptop.",
        "parameters": {"type": "OBJECT", "properties": {}},
    },
    {
        "name": "open_android_app",
        "description": "Open a predefined Android app on the specified phone.",
        "parameters": {
            "type": "OBJECT",
            "properties": {
                "app_name": {
                    "type": "STRING",
                    "enum": ["youtube", "chrome", "whatsapp", "settings"],
                },
                "device": DEVICE_SCHEMA,
            },
            "required": ["app_name", "device"],
        },
    },
    {
        "name": "open_app_on_device",
        "description": (
            "Discover and open an app by name on the exact target. Use device "
            "'windows', 'phone1', or 'phone2'. Never switch targets if not found."
        ),
        "parameters": {
            "type": "OBJECT",
            "properties": {
                "app_name": {"type": "STRING"},
                "device": {
                    "type": "STRING",
                    "enum": ["windows", "phone1", "phone2"],
                },
            },
            "required": ["app_name", "device"],
        },
    },
    {
        "name": "android_home",
        "description": "Return the specified Android phone to its home screen.",
        "parameters": {
            "type": "OBJECT",
            "properties": {"device": DEVICE_SCHEMA},
            "required": ["device"],
        },
    },
    {
        "name": "android_back",
        "description": "Press Back on the specified Android phone.",
        "parameters": {
            "type": "OBJECT",
            "properties": {"device": DEVICE_SCHEMA},
            "required": ["device"],
        },
    },
    {
        "name": "get_battery_level",
        "description": "Check the battery level of the specified Android phone.",
        "parameters": {
            "type": "OBJECT",
            "properties": {"device": DEVICE_SCHEMA},
            "required": ["device"],
        },
    },
    {
        "name": "get_device_info",
        "description": "Get device information for the specified Android phone.",
        "parameters": {
            "type": "OBJECT",
            "properties": {"device": DEVICE_SCHEMA},
            "required": ["device"],
        },
    },
]

aura_tools = types.Tool(function_declarations=FUNCTION_DECLARATIONS)
conversation_history = load_memory() or []
aura_state = {"last_device": None, "last_app": None, "last_action": None}


def _is_success(result):
    """Handle both the router's outer status and nested discovery result."""
    if not isinstance(result, dict):
        return False
    if result.get("status") != "success":
        return False
    nested = result.get("result")
    if isinstance(nested, dict) and nested.get("success") is False:
        return False
    return True


def _record_success(tool_name, arguments):
    aura_state["last_action"] = tool_name
    device = arguments.get("device")
    if tool_name == "open_app_on_device":
        device = arguments.get("device")
        aura_state["last_app"] = arguments.get("app_name")
    elif tool_name == "open_android_app":
        aura_state["last_app"] = arguments.get("app_name")
    elif tool_name == "open_windows_app":
        aura_state["last_device"] = "windows"
        aura_state["last_app"] = arguments.get("app_name")
    elif tool_name == "android_home" or tool_name == "android_back":
        aura_state["last_device"] = device
    if device:
        aura_state["last_device"] = device


def _append_memory(role, text):
    conversation_history.append({"role": role, "text": text})
    # Keep the in-memory history bounded; persistent memory remains managed by memory.py.
    if len(conversation_history) > 40:
        del conversation_history[:-40]
    add_memory(role, text)


def _result_summary(tool_results):
    lines = []
    for name, arguments, result in tool_results:
        lines.append(f"- {name} {json.dumps(arguments, ensure_ascii=False)}: {result}")
    return "\n".join(lines)


def ask_aura(user_message):
    """Answer a message and execute tool calls one real action at a time."""
    user_message = str(user_message).strip()
    if not user_message:
        return "Please tell me what you would like me to do."

    _append_memory("user", user_message)
    recent_history = conversation_history[-12:]
    history_text = "\n".join(
        f"{item.get('role', 'user')}: {item.get('text', '')}"
        for item in recent_history
        if isinstance(item, dict)
    )
    context = (
        f"Current device state: {json.dumps(aura_state)}\n\n"
        f"Recent conversation:\n{history_text}\n\n"
        f"Current request: {user_message}"
    )

    contents = [types.Content(role="user", parts=[types.Part.from_text(text=context)])]
    tool_results = []
    retry_count = 0
    tool_rounds = 0

    while tool_rounds < MAX_TOOL_ROUNDS:
        try:
            response = client.models.generate_content(
                model=MODEL,
                contents=contents,
                config=types.GenerateContentConfig(
                    system_instruction=SYSTEM_PROMPT,
                    tools=[aura_tools],
                    temperature=0.2,
                ),
            )
            retry_count = 0
        except Exception as error:
            message = str(error)
            temporary = any(token in message.upper() for token in (
                "429", "RESOURCE_EXHAUSTED", "503", "UNAVAILABLE", "DEADLINE_EXCEEDED"
            ))
            if temporary and not tool_results and retry_count < MAX_MODEL_RETRIES:
                retry_count += 1
                wait_seconds = min(2 ** retry_count, 8)
                print(f"AURA: Gemini temporarily unavailable. Retry {retry_count}/{MAX_MODEL_RETRIES} in {wait_seconds}s.")
                time.sleep(wait_seconds)
                continue
            if tool_results:
                summary = _result_summary(tool_results)
                answer = (
                    "I completed the actions shown below, but Gemini became unavailable "
                    "before I could safely finish the full request:\n" + summary
                )
                _append_memory("assistant", answer)
                return answer
            return f"AURA could not reach Gemini: {message}"

        if not response.candidates:
            answer = "Gemini returned no response. Please try again."
            _append_memory("assistant", answer)
            return answer

        candidate_content = response.candidates[0].content
        parts = candidate_content.parts or []
        function_calls = [part.function_call for part in parts if getattr(part, "function_call", None)]

        if not function_calls:
            answer = (response.text or "I could not generate a response.").strip()
            if tool_results:
                # Keep actual action results available so a model answer cannot silently
                # contradict what the tools returned.
                answer += "\n\nActions performed:\n" + _result_summary(tool_results)
            _append_memory("assistant", answer)
            return answer

        # Preserve the model's tool-call message in the conversation before responding.
        contents.append(candidate_content)
        response_parts = []

        # Execute only the first requested action. Send a response for every call in the
        # candidate so the function-call turn is fully acknowledged by the API. Deferred
        # actions are explicitly marked and will be reconsidered by the model afterward.
        for index, function_call in enumerate(function_calls):
            tool_name = function_call.name
            arguments = dict(function_call.args or {})
            if index == 0:
                tool_rounds += 1
                print(f"\nAURA TOOL -> {tool_name}")
                print(f"Arguments -> {arguments}")
                try:
                    result = execute_tool(tool_name, arguments)
                except Exception as error:
                    result = {"status": "failure", "tool": tool_name, "message": str(error)}
                tool_results.append((tool_name, arguments, result))
                print(f"Tool Result -> {result}")
                if _is_success(result):
                    _record_success(tool_name, arguments)
                response_data = {
                    "tool": tool_name,
                    "arguments": arguments,
                    "result": result,
                    "status": "success" if _is_success(result) else "failure",
                }
            else:
                response_data = {
                    "tool": tool_name,
                    "arguments": arguments,
                    "status": "not_executed",
                    "message": (
                        "This action was not executed. Inspect the preceding real tool result, "
                        "then decide whether this action is still necessary and safe."
                    ),
                }
                print(f"AURA SAFEGUARD -> Deferred tool action: {tool_name} {arguments}")

            response_parts.append(
                types.Part.from_function_response(
                    name=tool_name,
                    response={"result": json.dumps(response_data, ensure_ascii=False, default=str)},
                )
            )

        contents.append(types.Content(role="user", parts=response_parts))

    answer = "I stopped because the request required too many tool steps. Completed actions:\n"
    answer += _result_summary(tool_results) if tool_results else "No actions were executed."
    _append_memory("assistant", answer)
    return answer


def main():
    print("=" * 48)
    print("AURA AI - Phase 5.3: Advanced Task Planning")
    print("Conversation Memory Enabled")
    print("Commands: clear | exit")
    print("=" * 48)

    while True:
        try:
            user_input = input("\nYou: ").strip()
        except (EOFError, KeyboardInterrupt):
            print("\nAURA: Shutting down.")
            break

        if not user_input:
            continue
        command = user_input.lower()
        if command in {"exit", "quit"}:
            print("AURA: Goodbye.")
            break
        if command == "clear":
            conversation_history.clear()
            clear_persistent_memory()
            aura_state.update({"last_device": None, "last_app": None, "last_action": None})
            print("AURA: Conversation memory cleared.")
            continue

        answer = ask_aura(user_input)
        print(f"\nAURA: {answer}")


if __name__ == "__main__":
    main()