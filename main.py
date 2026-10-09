from speech import listen
from aura_brain import ask_aura


# ==========================================
# WAKE WORD
# ==========================================

def detect_wake_word(text):
    text = text.lower().strip()
    return "hey aura" in text


# ==========================================
# AURA STARTUP
# ==========================================

print("================================")
print("        AURA AI - Phase 3.6")
print("================================")
print("AURA is waiting for the wake word...")
print("Say: Hey Aura")
print("================================")


# ==========================================
# MAIN LOOP
# ==========================================

while True:

    try:

        # ----------------------------------
        # WAIT FOR WAKE WORD
        # ----------------------------------

        text = listen(duration=3)

        if detect_wake_word(text):

            print("\nAURA: Yes? How can I help?")

            # ----------------------------------
            # LISTEN FOR COMMAND
            # ----------------------------------

            command = listen(duration=5)

            if not command:

                print("AURA: I didn't hear a command.")
                continue

            print("Command:", command)

            # ----------------------------------
            # SEND TO GEMINI
            # ----------------------------------

            response = ask_aura(command)

            print("AURA:", response)

        else:

            print("AURA: Wake word not detected.")


    except KeyboardInterrupt:

        print("\nAURA: Goodbye!")
        break


    except Exception as e:

        print("AURA Error:", e)