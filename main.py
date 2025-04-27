import asyncio
import edge_tts
import whisper
import subprocess
import os
import glob
from google import genai
from tqdm import tqdm

GEMINI_API_KEY = "Your API key"


async def translate_text(client, text, target_language):
    prompt = f"Translate this text to {target_language} and reply only translated text: {text}"
    response = client.models.generate_content(model="gemini-2.0-flash", contents=prompt)
    return response.text.strip()

async def generate_tts(text, voice_name, output_filename):
    communicate = edge_tts.Communicate(text=text, voice=voice_name)
    await communicate.save(output_filename)

async def process_segment(segment, target_language, voice_name, idx, client):
    original_text = segment['text']
    start = segment['start']
    end = segment['end']

    translated_text = await translate_text(client, original_text, target_language)

    output_filename = f"segment_{idx}.mp3"
    await generate_tts(translated_text, voice_name, output_filename)

    return (output_filename, start, end)

def cleanup_segments():
    print("\nCleaning up temporary segment files...")
    for file in glob.glob("segment_*.mp3"):
        os.remove(file)
    if os.path.exists("segments_list.txt"):
        os.remove("segments_list.txt")

async def process_audio(audio_file, is_youtube=False, original_video=None):
    model_size = input("Choose Whisper model (tiny, base, small, medium, large): ").strip()
    print("\nLoading model...")
    model = whisper.load_model(model_size)

    print("\nTranscribing audio...")
    result = model.transcribe(audio_file)
    segments = result['segments']

    target_language = input("\nEnter target language (e.g., th, ja, en, es, fr, etc.): ").strip()

    voice_name = input("\nEnter Edge-TTS voice name (e.g., ja-JP-NanamiNeural, th-TH-NiwatNeural): ").strip()

    client = genai.Client(api_key=GEMINI_API_KEY)

    print("\nProcessing segments...")

    results = []
    for idx, segment in enumerate(tqdm(segments, desc="Processing segments")):
        result = await process_segment(segment, target_language, voice_name, idx, client)
        results.append(result)
        await asyncio.sleep(5)  # Delay 5 วิ ต่อ 1 segment

    # รวมไฟล์เสียง
    print("\nCombining segments with ffmpeg...")

    with open("segments_list.txt", "w") as f:
        for idx, (filename, start, end) in enumerate(results):
            f.write(f"file '{os.path.abspath(filename)}'\n")

    subprocess.run([
        "ffmpeg", "-f", "concat", "-safe", "0", "-i", "segments_list.txt",
        "-c", "copy", "final_audio.mp3", "-y"
    ], check=True)

    print(f"\nSaved final audio: final_audio.mp3")

    # delete segments
    cleanup_segments()

    if is_youtube and original_video:
        final_video = "output_final_video.mp4"
        subprocess.run([
            "ffmpeg", "-i", original_video, "-i", "final_audio.mp3",
            "-c:v", "copy", "-map", "0:v:0", "-map", "1:a:0",
            "-shortest", final_video, "-y"
        ], check=True)
        print(f"\n✅ Created final video: {final_video}")
    else:
        try:
            # change mp3 to wav before playing
            print("\nConverting MP3 to WAV for playback...")
            subprocess.run(["ffmpeg", "-y", "-i", "final_audio.mp3", "final_audio.wav"], check=True)

            import simpleaudio as sa
            print("\nPlaying the generated audio...")
            wave_obj = sa.WaveObject.from_wave_file("final_audio.wav")
            play_obj = wave_obj.play()
            play_obj.wait_done()

        except Exception as e:
            print(f"Cannot play audio: {e}")

async def main():
    choice = input("Choose mode (1=YouTube, 2=Local File): ").strip()

    if choice == "1":
        url = input("Enter YouTube URL: ").strip()
        print("\nDownloading YouTube video...")
        subprocess.run(["yt-dlp", "-f", "best", "-o", "downloaded_video.mp4", url], check=True)

        print("\nExtracting audio...")
        subprocess.run(["ffmpeg", "-i", "downloaded_video.mp4", "-q:a", "0", "-map", "a", "extracted_audio.mp3", "-y"], check=True)

        await process_audio("extracted_audio.mp3", is_youtube=True, original_video="downloaded_video.mp4")

    elif choice == "2":
        audio_file = input("Enter local audio filename (e.g., File.mp3): ").strip()
        await process_audio(audio_file, is_youtube=False)

    else:
        print("Invalid choice!")

if __name__ == "__main__":
    asyncio.run(main())
