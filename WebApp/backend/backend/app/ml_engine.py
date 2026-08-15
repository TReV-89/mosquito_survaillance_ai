import wave

from functools import lru_cache
from pathlib import Path

import numpy as np
import torch
import torch.nn as nn
import torchaudio

NUM_CLASSES = 2
SAMPLE_RATE = 8000
TARGET_LENGTH = SAMPLE_RATE
MODEL_PATH = (
    Path(__file__).resolve().parent.parent / "model" / "Malaria_detector_Net_V4.pth"
)


class MosquitoMelNet(nn.Module):
    def __init__(self, num_classes, sample_rate=8000, n_mels=64):
        super(MosquitoMelNet, self).__init__()

        # 1. Mel Spectrogram Feature Extractor
        # Generates a visual-audio matrix mapping biological frequencies
        self.mel_spec = torchaudio.transforms.MelSpectrogram(
            sample_rate=sample_rate,
            n_fft=256,
            hop_length=80,
            n_mels=n_mels,
        )
        # Convert power to decibels (log scale) to highlight subtle hums
        self.amplitude_to_db = torchaudio.transforms.AmplitudeToDB()

        # 2. First Spatial CNN (n_mels becomes the in_channels)
        self.conv1 = nn.Conv1d(in_channels=n_mels, out_channels=64, kernel_size=5, padding=2)
        self.pool1 = nn.MaxPool1d(2)

        # 3. Second Spatial CNN
        self.conv2 = nn.Conv1d(in_channels=64, out_channels=64, kernel_size=5, padding=2)
        self.pool2 = nn.MaxPool1d(2)

        self.relu = nn.LeakyReLU(0.2)
        self.dropout = nn.Dropout(0.5)

        # 4. LSTM (Receiving the compressed Mel-CNN sequence)
        self.lstm = nn.LSTM(
            input_size=64, hidden_size=128, num_layers=2, batch_first=True, dropout=0.3
        )

        # 5. Final Classification
        self.fc = nn.Linear(128, num_classes)

    def forward(self, x):
        # Ensure input is 2D: (batch, time)
        if x.dim() == 3:
            x = x.squeeze(1)

        # Extract Mel Spectrogram features
        x = self.mel_spec(x)
        x = self.amplitude_to_db(x)  # Output shape: (batch, n_mels, time_frames)

        # Pass through CNNs
        x = self.pool1(self.relu(self.conv1(x)))
        x = self.pool2(self.relu(self.conv2(x)))

        # Reshape for LSTM: from (batch, features, seq_len) to (batch, seq_len, features)
        x = x.transpose(1, 2)

        lstm_out, _ = self.lstm(x)

        # Apply dropout to the final time step prediction
        last_out = self.dropout(lstm_out[:, -1, :])
        return self.fc(last_out)


def _select_device() -> torch.device:
    if torch.cuda.is_available():
        return torch.device("cuda")
    if torch.backends.mps.is_available():
        return torch.device("mps")
    return torch.device("cpu")


def _load_wave_file(wav_file_path: str) -> np.ndarray:
    with wave.open(wav_file_path, "rb") as wav:
        frame_count = wav.getnframes()
        sample_width = wav.getsampwidth()
        channel_count = wav.getnchannels()
        frames = wav.readframes(frame_count)

    if sample_width == 2:
        audio = np.frombuffer(frames, dtype=np.int16).astype(np.float32) / 32768.0
    elif sample_width == 4:
        audio = np.frombuffer(frames, dtype=np.int32).astype(np.float32) / 2147483648.0
    else:
        raise ValueError(f"Unsupported WAV sample width: {sample_width} bytes")

    if channel_count > 1:
        audio = audio.reshape(-1, channel_count).mean(axis=1)

    return audio


def _prepare_input_tensor(wav_file_path: str, device: torch.device) -> torch.Tensor:
    waveform = _load_wave_file(wav_file_path)

    if waveform.size == 0:
        raise ValueError("The provided WAV file has no audio samples.")

    if waveform.shape[0] > TARGET_LENGTH:
        energy = np.power(waveform, 2)
        window = np.ones(TARGET_LENGTH, dtype=np.float32)
        rolling_energy = np.convolve(energy, window, mode="valid")
        start_idx = int(np.argmax(rolling_energy))
        waveform = waveform[start_idx : start_idx + TARGET_LENGTH]
    elif waveform.shape[0] < TARGET_LENGTH:
        waveform = np.pad(
            waveform, (0, TARGET_LENGTH - waveform.shape[0]), mode="constant"
        )

    max_amplitude = float(np.max(np.abs(waveform)))
    if max_amplitude > 0:
        waveform = waveform / max_amplitude

    model_input = (
        torch.from_numpy(waveform.astype(np.float32)).unsqueeze(0).unsqueeze(0)
    )
    return model_input.to(device)


@lru_cache(maxsize=1)
def _load_model() -> tuple[nn.Module, torch.device]:
    if not MODEL_PATH.exists():
        raise FileNotFoundError(f"Model weights not found: {MODEL_PATH}")

    device = _select_device()
    model = MosquitoMelNet(num_classes=NUM_CLASSES).to(device)
    try:
        state_dict = torch.load(MODEL_PATH, map_location=device, weights_only=True)
    except TypeError:
        state_dict = torch.load(MODEL_PATH, map_location=device)
    model.load_state_dict(state_dict)
    model.eval()
    return model, device


def predict_mosquito_species(wav_file_path: str, _metadata: dict) -> dict:
    model, device = _load_model()
    input_tensor = _prepare_input_tensor(wav_file_path, device)

    with torch.inference_mode():
        logits = model(input_tensor)
        probs = torch.softmax(logits, dim=1).squeeze(0).detach().cpu().numpy()

    non_anopheles_prob = float(probs[0]) * 100.0
    anopheles_prob = float(probs[1]) * 100.0

    return {
        "anopheles": round(anopheles_prob, 2),
        "non_anopheles": round(non_anopheles_prob, 2),
        "raw_signal_detected": bool(
            np.max(np.abs(input_tensor.detach().cpu().numpy())) > 1e-5
        ),
    }
