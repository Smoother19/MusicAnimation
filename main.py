import librosa

from pathlib import Path
from sound_to_midi.monophonic import wave_to_midi

music_dir = Path("sounds")

# Charge le fichier audio
audio, sample_rate = librosa.load(str(music_dir / "Ecossaise_Piano.mp3"), sr=None)

print(f"Sample rate: {sample_rate} Hz")
print(f"Nombre d'échantillons: {len(audio)}")
print(f"Durée: {len(audio) / sample_rate:.2f} s")

print("Hello World !")