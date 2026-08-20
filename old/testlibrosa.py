import librosa
import numpy as np
import matplotlib.pyplot as plt
from scipy.ndimage import *

HOP = 256   # temps entre 2 frames
BPO = 36    # bins/octave => 3 bins/demi-tons
K = 8       # nbr harmonique
N_BINS = 228    # hauteur totale
GEOMETRIC = True    # False → somme arithmétique, pour comparer
SEUIL = 0.2


# chargement + stft/cqt
y, sr = librosa.load(".\\sounds\\Ecossaise_Trumpet.mp3")
tuning = librosa.estimate_tuning(y=y, sr=sr)
fmin = librosa.note_to_hz("G2")

S_stft = librosa.stft(y, hop_length=HOP)
C_cqt = librosa.cqt(y, sr=sr, hop_length=HOP, fmin=fmin, bins_per_octave=BPO, n_bins=N_BINS, tuning=tuning)

logS = librosa.amplitude_to_db(np.abs(S_stft), ref=np.max)
C_lin = np.abs(C_cqt)

# rythme
diffS = np.maximum(np.diff(logS, axis=-1, prepend=logS[:, :1]), 0)
onset_env = np.mean(diffS, axis=0)  # agregation

onset_frames = librosa.onset.onset_detect(onset_envelope=onset_env,
                                          sr=sr, hop_length=HOP)    # detection de pic
onset_times = librosa.frames_to_time(onset_frames, sr=sr, hop_length=HOP)

tempo, beats = librosa.beat.beat_track(onset_envelope=onset_env,
                                       sr=sr, hop_length=HOP)   # tempo
tempo = float(np.atleast_1d(tempo)[0])
beat_times = librosa.frames_to_time(beats, sr=sr, hop_length=HOP)


# lissage
def whiten(C, size=48, floor_ratio=0.01):
    p = uniform_filter1d(C.astype(np.float64) ** 2, size=size,
                         axis=0, mode="nearest")
    local = np.sqrt(np.maximum(p, 0.0))
    return C / np.maximum(local, floor_ratio * local.max())

C_white = whiten(C_lin)


# saillances => quelle note jouer à instant T
offsets = BPO * np.log2(np.arange(1, K + 1))    # offsets en bins
weights = 1.0 / np.arange(1, K + 1)     # poids harmoniques => patch erreurs octave

cands = np.arange(0, N_BINS - int(np.ceil(offsets[-1])), 3)     # positions demi-tons

def salience(C):
    scores = []
    for b in cands:
        total = 0
        for k in range(1, K + 1):
            p = b + BPO * np.log2(k)
            total += (1/k) * C[int(round(p))]
        scores.append(total / weights.sum())
    return np.array(scores)

t_ref = librosa.time_to_frames(20.0, sr=sr, hop_length=HOP)
print("contrôle:", cands[np.argmax(salience(C_white[:, t_ref]))])

S_sal = salience(C_white)

# plt.plot(cands, salience(C_white[:, t_ref]), label="arrondi")
# plt.plot(cands, salience(C_white[:, t_ref]), label="interpolé")
# plt.legend()
# plt.show()

# hauteur
pitch_bins = cands[np.argmax(S_sal, axis=0)]
pitch_bins = median_filter(pitch_bins, size=5, mode="nearest")
pitch_hz = fmin * 2.0 ** (pitch_bins / BPO)
times = librosa.times_like(pitch_hz, sr=sr, hop_length=HOP)

print(f"{len(onset_times)} onsets, tempo {tempo:.1f} BPM")


# sonification
# f_ech = np.repeat(pitch_hz, HOP)
# f_ech = (f_ech[:len(y)] if len(f_ech) >= len(y)
#          else np.pad(f_ech, (0, len(y) - len(f_ech)), mode="edge"))

# sinus = 0.3 * np.sin(2 * np.pi * np.cumsum(f_ech) / sr)
# sf.write("pitch_check.wav", y * 0.5 + sinus, sr)

frames = np.append(onset_frames, len(pitch_bins))

notes = []
for i in range(len(frames) - 1):
    a, b = frames[i], frames[i + 1]
    if b - a < 3:                       # trop court pour être une note
        continue
    seg = pitch_bins[a:b]
    bin_note = int(np.median(seg))
    force = S_sal[:, a:b].max(axis=0).mean()
    notes.append((a, b, bin_note, force))

forces = np.array([n[3] for n in notes])

midi_note = librosa.hz_to_midi(fmin * 2.0 ** (bin_note / BPO))
midi_note = int(np.round(midi_note))


notes = [n for n in notes if n[3] >= SEUIL]
print(len(notes), "notes retenues")

import pretty_midi

# quantification sur la grille de temps
sub = 60.0 / tempo / 4          # durée d'une double-croche
t0 = beat_times[0]              # ancre la grille sur le 1er temps détecté

def snap(t):
    return t0 + round((t - t0) / sub) * sub

# écriture
pm = pretty_midi.PrettyMIDI(initial_tempo=tempo)
inst = pretty_midi.Instrument(program=56)      # 56 = Trumpet

f_max = forces.max()
for a, b, bin_note, force in notes:
    pitch = int(round(librosa.hz_to_midi(fmin * 2.0 ** (bin_note / BPO))))
    velocity = int(np.clip(40 + 87 * (force / f_max) ** 3, 1, 127))

    start = snap(a * HOP / sr)
    end = max(snap(b * HOP / sr), start + sub)

    inst.notes.append(pretty_midi.Note(velocity=velocity, pitch=pitch,
                                       start=start, end=end))

pm.instruments.append(inst)
pm.write("transcription.mid")
print("MIDI écrit :", len(inst.notes), "notes")