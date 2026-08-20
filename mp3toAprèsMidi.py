import librosa
import numpy as np
import pretty_midi as pm
from pathlib import Path
from shutil import copy as cp

fmin = librosa.note_to_hz("C2")
fmax = librosa.note_to_hz("B8")
hop_length = 512
n_bins = 84
win_length = 2048
frame_length = 1351
top_db = 30

SEUIL_DB = -30.0      # seuil d'activation en dB
PRESENCE_MIN = 0.3    # proportion minimale de présence dans un segment
DURATION_MIN = 0.08   # durée minimale d'une note en secondes

music_dir = Path("sounds")
output_dir = Path("output")

def decode(filename:str):
    filetype = Path(filename).suffix
    if ".mid" in filetype :
        cp(music_dir / filename, output_dir / "transcription.mid")
        print("The input file is already a Midi file !")
        return True

    y, sr = librosa.load(music_dir / filename,sr=None)
    y, _ = librosa.effects.trim(y, top_db=top_db)

    y_harm, y_perc = librosa.effects.hpss(y)

    f0_yin = librosa.yin(y=y, sr=sr, fmax=fmax, fmin=fmin)

    f0_pyin, voiced_flag, voiced_prob = librosa.pyin(y=y, fmax=fmax, fmin=fmin, sr=sr,frame_length=frame_length)

    cqt = librosa.cqt(y=y, sr=sr, hop_length=hop_length,fmin=fmin,n_bins=n_bins)

    cqt_harm = librosa.cqt(y=y_harm, sr=sr, hop_length=hop_length,fmin=fmin,n_bins=n_bins)

    cqt_db = librosa.amplitude_to_db(np.abs(cqt_harm), ref=np.max)



    stft = librosa.stft(y=y, hop_length=hop_length, win_length=win_length)

    times = librosa.times_like(f0_pyin, sr=sr, hop_length=hop_length)

    stft_Perc = librosa.stft(y=y_perc, hop_length=hop_length)
    log_stft_Perc = librosa.amplitude_to_db(np.abs(stft_Perc), ref=np.max)
    diff_stft_Perc = np.diff(log_stft_Perc, axis=-1, prepend=log_stft_Perc[:, :1])
    diff_stft_Perc_thresh = np.maximum(diff_stft_Perc, 0)

    onset_env = np.mean(diff_stft_Perc_thresh, axis=0)
    times_onset = librosa.times_like(onset_env, sr=sr, hop_length=hop_length)
    onset_frames = librosa.onset.onset_detect(onset_envelope=onset_env,sr=sr,hop_length=hop_length,backtrack=True)
    onset_times = librosa.frames_to_time(onset_frames, sr=sr, hop_length=hop_length)


    cp(music_dir / filename, output_dir / "bg.mp3")