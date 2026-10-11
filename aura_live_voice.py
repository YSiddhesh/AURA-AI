
import asyncio

import sounddevice as sd
from dotenv import load_dotenv
from google import genai
from google.genai import types

load_dotenv()

MODEL = "gemini-3.8-live"
INPUT_RATE = 16000
OUTPUT_RATE = 24000
BLOCK_SIZE = 1024

client = genai.Client()


async def send_microphone(session):
    """Continuously stream microphone audio to Gemini."""
    print("Microphone active. Speak naturally.")

    with sd.RawInputStream(
        samplerate=INPUT_RATE,
        blocksize=BLOCK_SIZE,
        channels=1,
        dtype="int16",
    ) as microphone:

        while True:
            audio_chunk, overflowed = await asyncio.to_thread(
                microphone.read, BLOCK_SIZE
            )

            await session.send_realtime_input(
                audio=types.Blob(
                    data=bytes(audio_chunk),
                    mime_type=f"audio/pcm;rate={INPUT_RATE}",
                )
            )


async def receive_audio(session):
    """Play Gemini's spoken responses and print transcriptions."""
    print("AURA is listening. Press Ctrl+C to stop.")

    with sd.RawOutputStream(
        samplerate=OUTPUT_RATE,
        channels=1,
        dtype="int16",
    ) as speakers:

        async for message in session.receive():
            content = message.server_content

            if content is None:
                continue

            if content.input_transcription:
                text = content.input_transcription.text
                if text:
                    print(f"\nYou: {text}")

            if content.output_transcription:
                text = content.output_transcription.text
                if text:
                    print(f"AURA: {text}", end="", flush=True)

            if content.model_turn:
                for part in content.model_turn.parts:
                    if part.inline_data and part.inline_data.data:
                        speakers.write(part.inline_data.data)

            if content.turn_complete:
                print("\n")


async def main():
    config = {
        "response_modalities": ["AUDIO"],
        "input_audio_transcription": {},
        "output_audio_transcription": {},
        "system_instruction": (
            "You are AURA, a helpful voice assistant. "
            "Listen carefully, respond naturally and concisely, "
            "and speak as if having a live conversation."
        ),
    }

    print("Connecting to Gemini Live...")

    async with client.aio.live.connect(
        model=MODEL,
        config=config,
    ) as session:
        print("Connected successfully.")

        tasks = [
            asyncio.create_task(send_microphone(session)),
            asyncio.create_task(receive_audio(session)),
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
