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
frame_length = 2048
top_db = 30
bins_per_octave = 12

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

    f0_yin = librosa.yin(y=y, sr=sr, fmax=fmax, fmin=fmin, hop_length=hop_length, frame_length=frame_length)

    f0_pyin, voiced_flag, voiced_prob = librosa.pyin(y=y, fmax=fmax, fmin=fmin, sr=sr,frame_length=frame_length)

    cqt = librosa.cqt(y=y, sr=sr, hop_length=hop_length,fmin=fmin,n_bins=n_bins, bins_per_octave=bins_per_octave)

    cqt_harm = librosa.cqt(y=y_harm, sr=sr, hop_length=hop_length,fmin=fmin,n_bins=n_bins, bins_per_octave=bins_per_octave)

    cqt_db = librosa.amplitude_to_db(np.abs(cqt_harm), ref=np.max)



    stft = librosa.stft(y=y, hop_length=hop_length, win_length=win_length)

    times = librosa.times_like(f0_pyin, sr=sr, hop_length=hop_length)

    #Partie Percussion
    stft_Perc = librosa.stft(y=y_perc, hop_length=hop_length)
    log_stft_Perc = librosa.amplitude_to_db(np.abs(stft_Perc), ref=np.max)
    diff_stft_Perc = np.diff(log_stft_Perc, axis=-1, prepend=log_stft_Perc[:, :1])
    diff_stft_Perc_thresh = np.maximum(diff_stft_Perc, 0)

    onset_env_Perc = np.mean(diff_stft_Perc_thresh, axis=0)
    times_onset_Perc = librosa.times_like(onset_env_Perc, sr=sr, hop_length=hop_length)
    onset_frames_Perc = librosa.onset.onset_detect(onset_envelope=onset_env_Perc,sr=sr,hop_length=hop_length,backtrack=True)
    onset_times_Perc = librosa.frames_to_time(onset_frames_Perc, sr=sr, hop_length=hop_length)

    cqt_Perc = librosa.cqt(y=y_perc, sr=sr, hop_length=hop_length,fmin=fmin,n_bins=n_bins, bins_per_octave=bins_per_octave)
    
    #Partie Harmoniques
    stft_Harm = librosa.stft(y=y_harm, hop_length=hop_length)
    log_stft_Harm = librosa.amplitude_to_db(np.abs(stft_Harm), ref=np.max)
    diff_stft_Harm = np.diff(log_stft_Harm, axis=-1, prepend=log_stft_Harm[:, :1])
    diff_stft_Harm_thresh = np.maximum(diff_stft_Harm, 0)

    onset_env_Harm = np.mean(diff_stft_Harm_thresh, axis=0)
    times_onset_Harm = librosa.times_like(onset_env_Harm, sr=sr, hop_length=hop_length)
    onset_frames_Harm = librosa.onset.onset_detect(onset_envelope=onset_env_Harm,sr=sr,hop_length=hop_length,backtrack=True)
    onset_times_Harm = librosa.frames_to_time(onset_frames_Harm, sr=sr, hop_length=hop_length)

    f0_pyin_Harm, voiced_flag_Harm, voiced_prob_Harm = librosa.pyin(y=y_harm, fmax=fmax, fmin=fmin, sr=sr,frame_length=frame_length)

    
    cp(music_dir / filename, output_dir / "bg.mp3")