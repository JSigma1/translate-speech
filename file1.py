import asyncio
import edge_tts
import whisper
import simpleaudio as sa
import subprocess
import os

async def main():
    mp3_file = input("Enter mp3 filename (e.g., Relax.mp3): ")

    print("\nTranscribing audio...")
    model = whisper.load_model("medium")
    result = model.transcribe(mp3_file)
    original_text = result["text"]
    print("\nOriginal Text:\n")
    print(original_text)

    language_selection = input("\nSelect language to translate (th, ja): ").lower()
    while language_selection not in ["th", "ja"]:
        print("Invalid language, please use only 'th' or 'ja'")
        language_selection = input("Select language (th, ja): ").lower()

    from deep_translator import GoogleTranslator
    print("\nTranslating text...")
    translated_text = GoogleTranslator(source='auto', target=language_selection).translate(original_text)
    print("\nTranslated Text:\n")
    print(translated_text)

    if language_selection == "th":
        voice_name = "th-TH-NiwatNeural"
    elif language_selection == "ja":
        voice_name = "ja-JP-KeitaNeural"

    output_mp3 = "Relax_translated.mp3"
    output_wav = "Relax_translated.wav"

    print("\nGenerating speech...")
    communicate = edge_tts.Communicate(
        text=translated_text,
        voice=voice_name
    )
    await communicate.save(output_mp3)
    print(f"\nSaved: {output_mp3} successfully!")

    # use ffmpeg convertmp3 to wav
    print("\nConverting mp3 to wav...")
    subprocess.run(["ffmpeg", "-y", "-i", output_mp3, output_wav], check=True)
    print(f"Converted to {output_wav} successfully!")

    # play wav with simpleaudio
    print("\nPlaying the generated audio...")
    wave_obj = sa.WaveObject.from_wave_file(output_wav)
    play_obj = wave_obj.play()
    play_obj.wait_done()

if __name__ == "__main__":
    asyncio.run(main())
