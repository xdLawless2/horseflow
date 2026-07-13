import io

import librosa
import numpy as np
import soundfile as sf


def normalize_to_wav(data: bytes, path: str) -> float:
    """Decode audio to peak-normalized 16 kHz mono WAV and return seconds."""
    audio, _ = librosa.load(io.BytesIO(data), sr=16_000, mono=True)
    peak = float(np.abs(audio).max())
    if peak > 0:
        audio = audio * (0.95 / peak)
    sf.write(path, audio, 16_000)
    return len(audio) / 16_000
