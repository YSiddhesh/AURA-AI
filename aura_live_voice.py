import asyncio
import threading
from collections import deque

import numpy as np
import sounddevice as sd
from dotenv import load_dotenv
from google import genai
from google.genai import types

from tool_router import execute_tool

load_dotenv()

MODEL = "gemini-3.8-live"
INPUT_RATE = 16000
OUTPUT_RATE = 24000
BLOCK_SIZE = 1024

client = genai.Client()

DEVICE_SCHEMA = {
    "type": "STRING",
    "enum": ["phone1", "phone2"],
}

AURA_TOOLS = [{
    "function_declarations": [
        {
            "name": "open_windows_app",
            "description": "Open an approved application on Windows.",
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
            "description": "Open a file by its exact filename.",
            "parameters": {
                "type": "OBJECT",
                "properties": {
                    "file_name": {"type": "STRING"},
                },
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
            "description": "Open an approved Android app on a specified phone.",
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
            "description": "Check the battery percentage of an Android phone.",
            "parameters": {
                "type": "OBJECT",
                "properties": {"device": DEVICE_SCHEMA},
                "required": ["device"],
            },
        },
        {
            "name": "get_device_info",
            "description": "Get the manufacturer and model of an Android phone.",
            "parameters": {
                "type": "OBJECT",
                "properties": {"device": DEVICE_SCHEMA},
                "required": ["device"],
            },
        },
        {
            "name": "open_app_on_device",
            "description": (
                "Search for an application on the specifically requested "
                "device and open it if found. Use this for application names "
                "that are not covered by the existing predefined app tools. "
                "Never switch to another device if the app is missing."
            ),
            "parameters": {
                "type": "OBJECT",
                "properties": {
                    "app_name": {
                        "type": "STRING",
                        "description": "The application name spoken by the user.",
                    },
                    "device": {
                        "type": "STRING",
                        "enum": ["windows", "phone1", "phone2"],
                        "description": (
                            "The exact target: windows for laptop, "
                            "phone1 for phone 1, phone2 for phone 2."
                        ),
                    },
                },
                "required": ["app_name", "device"],
            },
        },
    ]
}]


SYSTEM_INSTRUCTION = """
You are AURA, a natural conversational voice assistant.

CONVERSATION CONTEXT:
- Maintain continuity with the recent conversation throughout this live session.
- Use previous user requests, your responses, and tool results to understand follow-up commands.
- Resolve references such as "it", "that app", "the same phone", "the other phone", and "do that again" from recent context.
- For "its battery", identify the device referred to in recent conversation.
- If the user changes the device or application, follow the new request.
- Do not ask the user to repeat information that is already clear.
- If a reference is genuinely ambiguous, ask one short clarifying question rather than guessing.
- Treat tool results as authoritative. Never claim an action succeeded unless its result supports that conclusion.

DEVICE CONTROL:
- Listen continuously and respond naturally without requiring a wake phrase.
- Use available tools for device actions and information.
- Use only phone1 and phone2 as internal Android identifiers.
- Interpret "phone 1", "phone one", "phone 2", and "phone two" correctly.
- Use predefined application tools for supported applications.
- For other application names, use open_app_on_device and specify the exact target: windows, phone1, or phone2.
- Never silently switch devices if an app is missing or a device is unavailable.
- For multi-step requests, perform actions in the requested order.
- Only use applications and functions exposed by the tools.
- If a tool fails or its result is unclear, explain that accurately; do not invent success.
"""


async def send_microphone(session):
    print("Microphone active. Speak naturally.")

    with sd.RawInputStream(
        samplerate=INPUT_RATE,
        blocksize=BLOCK_SIZE,
        channels=1,
        dtype="int16",
    ) as microphone:

        while True:
            audio_chunk, _ = await asyncio.to_thread(
                microphone.read, BLOCK_SIZE
            )

            await session.send_realtime_input(
                audio=types.Blob(
                    data=bytes(audio_chunk),
                    mime_type=f"audio/pcm;rate={INPUT_RATE}",
                )
            )


def _tool_result_status(result):
    """Return True/False when the result clearly indicates success/failure, else None."""
    if isinstance(result, dict):
        status = str(result.get("status", "")).strip().lower()
        if status in {"failure", "failed", "error", "unavailable", "not_found"}:
            return False
        if status in {"success", "succeeded", "ok", "completed"}:
            return True
        if result.get("success") is False or result.get("ok") is False:
            return False
        if result.get("success") is True or result.get("ok") is True:
            return True
        return None

    if isinstance(result, str):
        message = result.strip().lower()
        failure_markers = (
            "error:", "failed", "failure", "could not", "couldn't",
            "unable to", "not found", "not connected", "unknown target",
            "device not found", "unavailable",
        )
        if any(marker in message for marker in failure_markers):
            return False
        success_markers = (
            "success", "opened", "opening", "battery level", "battery:",
            "device info", "returned to home", "pressed back", "locked",
        )
        if any(marker in message for marker in success_markers):
            return True
    return None


def _context_snapshot(context):
    """Create a compact, JSON-safe summary of the latest tool activity."""
    return {
        "last_target_device": context["last_target_device"],
        "last_application": context["last_application"],
        "last_action": context["last_action"],
        "last_tool": context["last_tool"],
        "last_result_status": context["last_result_status"],
        "last_result": context["last_result"],
    }


def _update_tool_context(context, tool_name, arguments, result):
    """Update context only from the tool call and its actual returned result."""
    device = arguments.get("device") or arguments.get("target_device")
    if device:
        context["last_target_device"] = str(device)
    elif tool_name in {"open_windows_app", "open_file", "lock_laptop"}:
        context["last_target_device"] = "windows"

    app_name = arguments.get("app_name") or arguments.get("file_name")
    if app_name:
        context["last_application"] = str(app_name)

    context["last_action"] = tool_name
    context["last_tool"] = tool_name
    context["last_result_status"] = _tool_result_status(result)
    context["last_result"] = str(result)[:500]


async def receive_responses(session):
    print("AURA is listening continuously. Press Ctrl+C to stop.")

    # Keep the output stream running. The callback plays queued PCM audio,
    # allowing an interruption to discard pending speech without aborting
    # PortAudio's stream.
    audio_buffer = deque()
    audio_lock = threading.Lock()
    current_chunk = None
    current_offset = 0

    # Session-only context: resets when AURA is restarted.
    context = {
        "last_target_device": None,
        "last_application": None,
        "last_action": None,
        "last_tool": None,
        "last_result_status": None,
        "last_result": None,
    }

    def audio_callback(outdata, frames, time_info, status):
        nonlocal current_chunk, current_offset
        outdata.fill(0)

        with audio_lock:
            written = 0
            while written < frames:
                if current_chunk is None or current_offset >= current_chunk.size:
                    if not audio_buffer:
                        break
                    current_chunk = audio_buffer.popleft()
                    current_offset = 0

                count = min(frames - written, current_chunk.size - current_offset)
                outdata[written:written + count, 0] = current_chunk[
                    current_offset:current_offset + count
                ]
                written += count
                current_offset += count

                if current_offset >= current_chunk.size:
                    current_chunk = None
                    current_offset = 0

    with sd.OutputStream(
        samplerate=OUTPUT_RATE,
        channels=1,
        dtype="int16",
        blocksize=BLOCK_SIZE,
        callback=audio_callback,
    ):
        while True:
            input_chunks = []
            output_chunks = []

            async for message in session.receive():
                # Handle requested tool calls and track their real results.
                if message.tool_call:
                    function_responses = []
                    for call in message.tool_call.function_calls:
                        tool_name = call.name
                        arguments = dict(call.args or {})
                        print(f"\nAURA TOOL -> {tool_name}")
                        print(f"Arguments -> {arguments}")

                        try:
                            result = await asyncio.to_thread(
                                execute_tool, tool_name, arguments
                            )
                        except Exception as error:
                            result = {
                                "status": "failure",
                                "message": str(error),
                            }

                        _update_tool_context(context, tool_name, arguments, result)
                        status = context["last_result_status"]
                        if status is True:
                            print("Tool Status -> SUCCESS (confirmed by result)")
                        elif status is False:
                            print("Tool Status -> FAILURE (reported by result)")
                        else:
                            print("Tool Status -> UNKNOWN (result needs interpretation)")
                        print(f"Tool Result -> {result}")

                        # Include the latest context in the tool response so the
                        # model can use it when interpreting follow-up requests.
                        response_payload = {
                            "result": str(result),
                            "result_status": (
                                "success" if status is True else
                                "failure" if status is False else "unknown"
                            ),
                            "conversation_context": _context_snapshot(context),
                        }
                        function_responses.append(
                            types.FunctionResponse(
                                id=call.id,
                                name=tool_name,
                                response=response_payload,
                            )
                        )

                    await session.send_tool_response(
                        function_responses=function_responses
                    )

                content = message.server_content
                if content is None:
                    continue

                # Clear queued audio on interruption. Do not stop the stream,
                # because subsequent responses must still be played.
                if getattr(content, "interrupted", False):
                    with audio_lock:
                        audio_buffer.clear()
                        current_chunk = None
                        current_offset = 0
                    print("\nAURA: Speech interrupted.")
                    continue

                if content.input_transcription:
                    text = content.input_transcription.text
                    if text:
                        input_chunks.append(text)

                if content.output_transcription:
                    text = content.output_transcription.text
                    if text:
                        output_chunks.append(text)

                if content.model_turn:
                    for part in content.model_turn.parts:
                        if part.inline_data and part.inline_data.data:
                            audio_bytes = part.inline_data.data
                            # Avoid a malformed final sample if the byte count is odd.
                            if len(audio_bytes) % 2:
                                audio_bytes = audio_bytes[:-1]
                            if audio_bytes:
                                pcm = np.frombuffer(audio_bytes, dtype=np.int16).copy()
                                with audio_lock:
                                    audio_buffer.append(pcm)

                if content.turn_complete:
                    if input_chunks:
                        print("\nYou:", "".join(input_chunks))
                    if output_chunks:
                        print("AURA:", "".join(output_chunks))
                    print()
                    break


async def main():
    config = {
        "response_modalities": ["AUDIO"],
        "input_audio_transcription": {},
        "output_audio_transcription": {},
        "system_instruction": SYSTEM_INSTRUCTION,
        "tools": AURA_TOOLS,
    }

    print("Connecting to Gemini Live...")

    async with client.aio.live.connect(
        model=MODEL,
        config=config,
    ) as session:
        print("Connected successfully.")

        tasks = [
            asyncio.create_task(send_microphone(session)),
            asyncio.create_task(receive_responses(session)),
        ]

        try:
            done, pending = await asyncio.wait(
                tasks,
                return_when=asyncio.FIRST_COMPLETED,
            )

            for task in done:
                if not task.cancelled() and task.exception():
                    raise task.exception()

        finally:
            for task in tasks:
                task.cancel()

            await asyncio.gather(*tasks, return_exceptions=True)


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("\nAURA voice session stopped.")
    except Exception as error:
        print(f"\nAURA error: {error}")
