from pydub import AudioSegment
import speech_recognition as sr

# 🔥 Force ffmpeg path (change if needed)
AudioSegment.converter = r"C:\ffmpeg\bin\ffmpeg.exe"


def convert_ogg_to_wav(input_path, output_path):
    audio = AudioSegment.from_file(input_path)
    audio.export(output_path, format="wav")


def speech_to_text(wav_path):
    recognizer = sr.Recognizer()

    with sr.AudioFile(wav_path) as source:
        audio_data = recognizer.record(source)

    try:
        return recognizer.recognize_google(audio_data)
    except Exception as e:
        print("Speech error:", e)
        return "Could not understand audio"