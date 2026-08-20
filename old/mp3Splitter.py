import librosa as lr
import numpy as np
from pathlib import Path
import soundfile as sf

# Charge le fichier audio
music_dir = Path("sounds")
output_dir = Path("output")
audio, sample_rate = lr.load(str(music_dir / "Ecossaise_Both.mp3"), sr=None)

# Paramètres STFT
n_fft = 2048
hop_length = 512

stft = lr.stft(audio, n_fft=n_fft, hop_length=hop_length)
freqs = lr.fft_frequencies(sr=sample_rate, n_fft=n_fft)

# Plages de Hz
bands = [
    (20, 60, 'sub-low'),
    (60, 250, 'low'),
    (250, 500, 'bas-mid'),
    (500, 2000, 'mid'),
    (2000, 4000, 'high-mid'),
    (4000, 8000, 'high'),
    (8000, 20000, 'xhigh')
]

# Extraction
for low, high, name in bands:
    # Masque binaire : 1 si fréquence dans la bande, 0 sinon
    mask = [False] * len(freqs)
    for i, f in enumerate(freqs):
        if low <= f < high:
            mask[i] = True
    
    # Application du masque (broadcast sur les colonnes)
    stft_masked = stft.copy()

    for i in range(stft.shape[1]):
        for j in range(stft.shape[0]):
            if not mask[j]:
                stft_masked[j, i] = 0.0 + 0.0j
    
    # Reconstruction audio
    audio_band = lr.istft(stft_masked, hop_length=hop_length)
    
    # Sauvegarde
    sf.write(f"{output_dir / name}.wav", audio_band, sample_rate)
    print(f"{name}.wav généré")
