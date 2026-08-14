import os

from pydub import AudioSegment


def convert_to_mono_wav(input_path: str, output_path: str, target_sample_rate=16000):
    """
    Converts incoming webm/mp4/ogg audio to standardized mono .wav
    for the ML model pipeline.
    """
    if not os.path.exists(input_path):
        raise FileNotFoundError(f"Audio file not found: {input_path}")

    try:
        audio = AudioSegment.from_file(input_path)
    except Exception as exc:
        raise RuntimeError(
            "Audio conversion failed. Please install ffmpeg/avconv and ensure it is available on PATH."
        ) from exc

    audio = audio.set_channels(1)
    audio = audio.set_frame_rate(target_sample_rate)
    audio.export(output_path, format="wav")
    return output_path
