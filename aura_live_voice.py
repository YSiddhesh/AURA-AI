
import asyncio

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
                "description": "The application name spoken by the user."
            },
            "device": {
                "type": "STRING",
                "enum": ["windows", "phone1", "phone2"],
                "description": (
                    "The exact target: windows for laptop, "
                    "phone1 for phone 1, phone2 for phone 2."
                )
            }
        },
        "required": ["app_name", "device"]
    }
}

    ]
}]


SYSTEM_INSTRUCTION = """
You are AURA, a natural conversational voice assistant.

Listen continuously and respond naturally without requiring a wake phrase.
Use the available tools when the user requests device actions or information.
Use only phone1 and phone2 as internal device identifiers.
Interpret "phone 1", "phone one", "phone 2", and "phone two" correctly.
Never invent a tool result or claim an action succeeded when it failed.
Explain tool failures clearly and concisely.
For multi-step requests, perform the requested actions in order.
Only use the applications and functions exposed by the tools.
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


async def receive_responses(session):
    print("AURA is listening continuously. Press Ctrl+C to stop.")

    with sd.RawOutputStream(
        samplerate=OUTPUT_RATE,
        channels=1,
        dtype="int16",
    ) as speakers:

        while True:
            input_chunks = []
            output_chunks = []

            async for message in session.receive():

                # Handle requested tool calls.
                if message.tool_call:
                    function_responses = []

                    for call in message.tool_call.function_calls:
                        tool_name = call.name
                        arguments = dict(call.args or {})

                        print(f"\nAURA TOOL -> {tool_name}")
                        print(f"Arguments -> {arguments}")

                        try:
                            result = await asyncio.to_thread(
                                execute_tool,
                                tool_name,
                                arguments,
                            )
                        except Exception as error:
                            result = {
                                "status": "failure",
                                "message": str(error),
                            }

                        print(f"Tool Result -> {result}")

                        function_responses.append(
                            types.FunctionResponse(
                                id=call.id,
                                name=tool_name,
                                response={"result": str(result)},
                            )
                        )

                    await session.send_tool_response(
                        function_responses=function_responses
                    )

                content = message.server_content

                if content is None:
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
                            await asyncio.to_thread(
                                speakers.write,
                                part.inline_data.data,
                            )

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




