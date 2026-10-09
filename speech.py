from faster_whisper import WhisperModel
import sounddevice as sd
import soundfile as sf


model = WhisperModel(
    "base",
    device="cpu",
    compute_type="int8"
)


def listen(duration=5):

    print("\n🎙️ Listening...")

    sample_rate = 16000

    audio = sd.rec(
        int(duration * sample_rate),
        samplerate=sample_rate,
        channels=1,
        dtype="float32"
    )

    sd.wait()

    sf.write(
        "command.wav",
        audio,
        sample_rate
    )

    print("🔄 Converting speech to text...")

    segments, info = model.transcribe(
    "command.wav",
    language="en",
    beam_size=5,
    initial_prompt="Hey AURA. AURA is the name of the voice assistant."
)
    text = ""

    for segment in segments:
        text += " " + segment.text

    text = text.strip()

    print("Heard:", text)

    return text