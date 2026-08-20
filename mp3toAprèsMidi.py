import librosa
import pretty_midi as pm

fmin = librosa.note_to_hz("C2")
fmax = librosa.note_to_hz("B8")
hop_length = 512
n_bins = 84
win_length = 2048

y, sr = librosa.load(music_dir / filename,sr=None)

f0 = librosa.yin(y=y, sr=sr, fmax=fmax, fmin=fmin)

cqt = librosa.cqt(y=y, sr=sr, hop_length=hop_length,fmin=fmin,fmax=fmax,n_bins=n_bins)

stft_mag, stft_phase = librosa.stft(y=y, sr=sr, hop_length=hop_length, win_length=win_length)

times = librosa.times_like(f0, sr=sr, hop_length=hop_length)

