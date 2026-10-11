
import asyncio
import os
import wave

from dotenv import load_dotenv
from google import genai

load_dotenv()

client = genai.Client()
MODEL = "gemini-3.8-live"


async def main():
    print("Connecting to Gemini Live...")

    async with client.aio.live.connect(
        model=MODEL,
        config={
            "response_modalities": ["AUDIO"],
            "output_audio_transcription": {},
        },
    ) as session:

        print("Connected. Requesting a spoken response...")

        await session.send_client_content(
            turns={
                "role": "user",
                "parts": [
                    {"text": "Hello AURA. Introduce yourself in one short sentence."}
                ],
            },
            turn_complete=True,
        )

        with wave.open("aura_live_test.wav", "wb") as audio_file:
            audio_file.setnchannels(1)
            audio_file.setsampwidth(2)
            audio_file.setframerate(24000)

            async for response in session.receive():
                if response.data is not None:
                    audio_file.writeframes(response.data)

                content = response.server_content
                if content:
                    if content.output_transcription:
                        print(
                            "AURA:",
                            content.output_transcription.text,
                        )

                    if content.turn_complete:
                        break

    print("Audio saved to aura_live_test.wav")


if __name__ == "__main__":
    asyncio.run(main())

