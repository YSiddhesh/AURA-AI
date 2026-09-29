import os
from dotenv import load_dotenv
from openai import OpenAI

# Load API key from .env
load_dotenv()

api_key = os.getenv("OPENAI_API_KEY")

if not api_key:
    raise ValueError(
        "OPENAI_API_KEY not found. Please check your .env file."
    )

client = OpenAI(api_key=api_key)


SYSTEM_PROMPT = """
You are AURA, an intelligent personal AI assistant.

Your job is to understand the user's natural-language commands and respond
naturally and helpfully.

AURA can eventually control:
- Windows laptop
- Android phone 1
- Android phone 2

For now, this module is only testing AURA's language understanding.
Do NOT pretend that you actually performed an action.

If the user asks something:
- Understand the intent.
- Consider the context of the conversation.
- Ask for clarification when important information is missing.
- Respond naturally like a voice assistant.
"""


def ask_aura(user_message):
    response = client.responses.create(
        model="gpt-5.6-luna",
        instructions=SYSTEM_PROMPT,
        input=user_message
    )

    return response.output_text


if __name__ == "__main__":
    print("================================")
    print("       AURA AI - LLM Brain")
    print("================================")
    print("Type 'exit' to stop.\n")

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