import wave

from functools import lru_cache
from pathlib import Path

import numpy as np
import torch
import torch.nn as nn
import torchaudio
import torchaudio.transforms as T

NUM_CLASSES = 2
SAMPLE_RATE = 8000
TARGET_LENGTH = SAMPLE_RATE
MODEL_PATH = (
    Path(__file__).resolve().parent.parent / "model" / "Malaria_detector_Net_V6.pth"
)


class SpecAugmentPipeline(nn.Module):
    """Applies frequency and time masking to prevent overfitting to background noise."""
    def __init__(self, freq_mask_param=15, time_mask_param=35):
        super().__init__()
        self.freq_mask = T.FrequencyMasking(freq_mask_param=freq_mask_param)
        self.time_mask = T.TimeMasking(time_mask_param=time_mask_param)

    def forward(self, x):
        if self.training:
            x = self.freq_mask(x)
            x = self.time_mask(x)
        return x


class AttentionPooling(nn.Module):
    """Dynamically weights important time steps containing mosquito flight tones."""
    def __init__(self, hidden_dim):
        super().__init__()
        self.attention = nn.Sequential(
            nn.Linear(hidden_dim, 64),
            nn.Tanh(),
            nn.Linear(64, 1)
        )

    def forward(self, lstm_output):
        # lstm_output shape: (batch, seq_len, hidden_dim)
        weights = torch.softmax(self.attention(lstm_output), dim=1) # (batch, seq_len, 1)
        context = torch.sum(weights * lstm_output, dim=1)            # (batch, hidden_dim)
        return context


class MosquitoAttnNet(nn.Module):
    def __init__(self, num_classes=2, sample_rate=8000, n_mfcc=40):
        super(MosquitoAttnNet, self).__init__()
        
        # 1. MFCC Feature Extractor
        self.mfcc = torchaudio.transforms.MFCC(
            sample_rate=sample_rate,
            n_mfcc=n_mfcc,
            melkwargs={'n_fft': 256, 'hop_length': 80, 'n_mels': 64}
        )
        
        # 2. SpecAugment regularization (only active during model.train())
        self.spec_augment = SpecAugmentPipeline()
        
        # 3. 2D Convolutional Backbone (Treats MFCC like a 1-channel image: [batch, 1, n_mfcc, time])
        self.conv1 = nn.Conv2d(in_channels=1, out_channels=32, kernel_size=3, padding=1)
        self.bn1 = nn.BatchNorm2d(32)
        self.pool1 = nn.MaxPool2d((2, 2))
        
        self.conv2 = nn.Conv2d(in_channels=32, out_channels=64, kernel_size=3, padding=1)
        self.bn2 = nn.BatchNorm2d(64)
        self.pool2 = nn.MaxPool2d((2, 2))
        
        self.relu = nn.LeakyReLU(0.2)
        self.dropout = nn.Dropout(0.4)
        
        # 4. Bi-directional LSTM for temporal pattern capture
        # After two max pooling layers on n_mfcc=40, feature dimension becomes: (40 / 4) * 64 = 640
        self.lstm = nn.LSTM(input_size=640, hidden_size=128, num_layers=2, 
                            batch_first=True, bidirectional=True, dropout=0.3)
        
        # 5. Self-Attention Pooling (hidden_size * 2 due to bidirectional LSTM = 256)
        self.attention_pool = AttentionPooling(hidden_dim=256)
        
        # 6. Final Classification Head
        self.fc = nn.Sequential(
            nn.Linear(256, 64),
            nn.ReLU(),
            nn.Dropout(0.3),
            nn.Linear(64, num_classes)
        )

    def forward(self, x):
        if x.dim() == 3:
            x = x.squeeze(1)
            
        # Extract MFCC -> Shape: (batch, n_mfcc, time_frames)
        x = self.mfcc(x)
        
        # Add channel dimension for 2D Conv -> Shape: (batch, 1, n_mfcc, time_frames)
        x = x.unsqueeze(1)
        x = self.spec_augment(x)
        
        # Pass through 2D CNN layers
        x = self.pool1(self.bn1(self.relu(self.conv1(x))))
        x = self.pool2(self.bn2(self.relu(self.conv2(x))))
        
        # Reshape for LSTM: collapse frequency and channel dimensions into features
        # Shape becomes: (batch, time_frames, channels * remaining_mels)
        b, c, m, t = x.shape
        x = x.permute(0, 3, 1, 2).contiguous().view(b, t, c * m)
        
        # LSTM sequence processing
        lstm_out, _ = self.lstm(x)
        
        # Attention Pooling over all time steps
        x = self.attention_pool(lstm_out)
        x = self.dropout(x)
        
        return self.fc(x)


def _select_device() -> torch.device:
    if torch.cuda.is_available():
        return torch.device("cuda")
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
    model = MosquitoAttnNet(num_classes=NUM_CLASSES).to(device)
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
