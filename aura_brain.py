import os
from dotenv import load_dotenv
from google import genai


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

Your primary purpose is to understand natural human language
and help control the user's devices.

Available devices:

1. Windows laptop
2. Android phone 1
3. Android phone 2

You should communicate naturally like an intelligent voice assistant.

Important rules:

- Understand natural language instead of requiring fixed commands.
- Understand different ways of expressing the same request.
- Remember the context of the current conversation.
- Ask for clarification when important information is missing.
- Never claim that you performed an action unless the application
  actually executed that action.
- Keep responses concise because AURA is a voice assistant.

At this stage, you are being tested only as the language-understanding
brain. You do not directly control devices yet.
"""


# ==========================================
# ASK AURA
# ==========================================

def ask_aura(user_message):

    response = client.models.generate_content(
    model="gemini-flash-latest",
    contents=user_message,
    config={
        "system_instruction": SYSTEM_PROMPT
    }
)

    return response.text


# ==========================================
# TEST MODE
# ==========================================

if __name__ == "__main__":

    print("================================")
    print("       AURA AI - Gemini Brain")
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