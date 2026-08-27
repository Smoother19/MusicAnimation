import librosa
import pretty_midi
import numpy as np
import matplotlib.pyplot as plt
from scipy.ndimage import *
from pathlib import Path
from shutil import copy as cp
import numpy as np
import librosa
import pretty_midi
from scipy.ndimage import uniform_filter1d, median_filter
import matplotlib.pyplot as plt


HOP = 256   # temps entre 2 frames
BPO = 36    # bins/octave => 3 bins/demi-tons
K = 8       # nbr harmonique
N_BINS = 228    # hauteur totale
GEOMETRIC = True    # False → somme arithmétique, pour comparer
SEUIL = 0.2
DB_SEUIL = -30
fmin = librosa.note_to_hz("C2")
music_dir = Path("sounds")
output_dir = Path("output")

def decode(filename:str):
    filetype = Path(filename).suffix
    if ".mid" in filetype :
        cp(music_dir / filename, output_dir / "transcription.mid")
        print("The input file is already a Midi file !")
        return True

    # chargement + stft/cqt
    y, sr = librosa.load(music_dir / filename,sr=None)

    tuning = librosa.estimate_tuning(y=y, sr=sr)
    if tuning == None :
        tuning = 0.0

    fmin = librosa.note_to_hz("C2")

    S_stft = librosa.stft(y, hop_length=HOP)

    # STFT SPECTRE GENERATION
    fig, ax = plt.subplots(nrows=2, sharex=True)
    img = librosa.display.specshow(S_stft, vscale="dBFS",
                                sr=sr, hop_length=512, x_axis="time", y_axis="hz", ax=ax[0])
    librosa.display.colorbar_db(img, label="dBFS")
    ax[0].set(title="Spectrogram")
    ax[0].label_outer()
    librosa.display.waveshow(y, sr=sr, ax=ax[1])
    ax[1].set(title="Time-domain")

    plt.savefig(output_dir / "STFT")


    C_cqt = librosa.cqt(y, sr=sr, hop_length=HOP, fmin=fmin, bins_per_octave=BPO, n_bins=N_BINS, tuning=tuning)

    #CQT SPECTRE GENERATION
    fig, ax = plt.subplots()
    img = librosa.display.specshow(C_cqt, vscale="dBFS",
                               x_axis="time", y_axis="cqt_hz",
                               ax=ax)
    librosa.display.colorbar_db(img, label="dBFS")

    plt.savefig(output_dir / "CQT")

    logS = librosa.amplitude_to_db(np.abs(S_stft), ref=np.max)
    C_lin = np.abs(C_cqt)

    rms = librosa.feature.rms(y=y, hop_length=HOP)[0]
    rms_db = librosa.amplitude_to_db(rms, ref=np.max)

    fig, ax = plt.subplots(nrows=2, sharex=True)
    times = librosa.times_like(rms)
    ax[0].semilogy(times, rms, label='RMS Energy')
    ax[0].set(xticks=[])
    ax[0].legend()
    ax[0].label_outer()
    librosa.display.specshow(S_stft, vscale='dBFS',
                            y_axis='log', x_axis='time', ax=ax[1])
    ax[1].set(title='log Power spectrogram')

    plt.savefig(output_dir / "RMS")

    return y, sr, fmin, logS, C_lin, S_stft, rms, rms_db


def analyze_rhythm(logS, sr, HOP, S_stft):
    diffS = np.maximum(np.diff(logS, axis=-1, prepend=logS[:, :1]), 0)
    onset_env = np.mean(diffS, axis=0)  # agregation

    onset_frames = librosa.onset.onset_detect(onset_envelope=onset_env,
                                                sr=sr, hop_length=HOP)  # detection de pic

    # MAG SPECTRE GENERATION
    diffS_thresh = np.maximum(diffS, 0)

    # Visualize the results
    fig, ax = plt.subplots(nrows=3, sharex=True, sharey=True)
    i1 = librosa.display.specshow(S_stft, vscale="dBFS", x_axis="time", y_axis="log", ax=ax[0], sr=sr)
    i2 = librosa.display.specshow(diffS, x_axis="time", y_axis="log", ax=ax[1], sr=sr)
    i3 = librosa.display.specshow(diffS_thresh, x_axis="time", y_axis="log", ax=ax[2], sr=sr, norm=i2.norm, cmap=i2.cmap)

    librosa.display.colorbar_db(i1, label="dBFS")
    librosa.display.colorbar_db(i2, label="Δ dB")
    librosa.display.colorbar_db(i3, label="Δ dB")
    ax[0].label_outer()
    ax[1].label_outer()
    ax[0].set(ylabel="STFT")
    ax[1].set(ylabel="Difference")
    ax[2].set(ylabel="Thresholded diff")

    plt.savefig(output_dir / "diffS")

    if len(onset_frames) == 0:
        onset_frames = np.array([0])

    onset_times = librosa.frames_to_time(onset_frames, sr=sr, hop_length=HOP)

    tempo, beats = librosa.beat.beat_track(onset_envelope=onset_env,
                                        sr=sr, hop_length=HOP)   # tempo
    tempo = float(np.atleast_1d(tempo)[0])

    beats = np.atleast_1d(beats)
    if len(beats) == 0:
        beats = np.array([0])

    beat_times = librosa.frames_to_time(beats, sr=sr, hop_length=HOP)


    # lissage
    def whiten(C, size=48, floor_ratio=0.01):
        p = uniform_filter1d(C.astype(np.float64) ** 2, size=size,
                            axis=0, mode="nearest")
        local = np.sqrt(np.maximum(p, 0.0))
        return C / np.maximum(local, floor_ratio * local.max() + 1e-10)

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
    t_ref = min(t_ref, C_white.shape[1] - 1)
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


def build_notes(onset_frames, pitch_bins, S_sal, SEUIL, rms, rms_db, DB_SEUIL):
    active = rms_db > DB_SEUIL
    frames = np.append(onset_frames, len(pitch_bins))

    segments = []
    start = None
    for i, a in enumerate(active):
        if a and start is None:
            start = i
        elif not a and start is not None:
            segments.append((start, i))
            start = None
    if start is not None:
        segments.append((start, len(active)))

    notes = []
    for seg_start, seg_end in segments:
        onset_in_seg = onset_frames[(onset_frames >= seg_start) & (onset_frames <= seg_end)]
        if len(onset_in_seg) > 0:
            note_start = onset_in_seg[0]
        else:
            note_start = seg_start
        
        note_end = seg_end
        
        if note_end - note_start < 3:
            continue

        seg = pitch_bins[note_start:note_end]
        bin_note = int(np.median(seg))
        force = S_sal[:, note_start:note_end].max(axis=0).mean()
        notes.append((note_start, note_end, bin_note, force))

    midi_note = librosa.hz_to_midi(fmin * 2.0 ** (bin_note / BPO))
    midi_note = int(np.round(midi_note))


    notes = [n for n in notes if n[3] >= SEUIL]
    print(len(notes), "notes retenues")


    # quantification sur la grille de temps
    sub = 60.0 / tempo / 4          # durée d'une double-croche
    t0 = beat_times[0]              # ancre la grille sur le 1er temps détecté

    def snap(t):
        return t0 + round((t - t0) / sub) * sub

    # écriture
    pm = pretty_midi.PrettyMIDI(initial_tempo=tempo)
    inst = pretty_midi.Instrument(program=56)      # 56 = Trumpet

    forces = np.array([n[3] for n in notes])
    f_max = forces.max()

    for a, b, bin_note, force in notes:
        pitch = int(round(librosa.hz_to_midi(fmin * 2.0 ** (bin_note / BPO))))
        velocity = int(np.clip(40 + 87 * (force / f_max) ** 3, 1, 127))

        start = snap(a * HOP / sr)
        end = max(snap(b * HOP / sr), start + sub)

        inst.notes.append(pretty_midi.Note(velocity=velocity, pitch=pitch,
                                        start=start, end=end))

    pm.instruments.append(inst)
    pm.write(output_dir / "transcription.mid")
    cp(music_dir / filename, output_dir / "bg.mp3")
    print("MIDI écrit :", len(inst.notes), "notes")


def decode(filename: str):
    if handle_midi_passthrough(filename, music_dir, output_dir):
        return True

    y, sr, fmin, logS, C_lin, S_stft, rms, rms_db = load_audio_and_transforms(filename, music_dir, HOP, BPO, N_BINS)

    onset_frames, onset_times, tempo, beats, beat_times = analyze_rhythm(logS, sr, HOP, S_stft)

    C_white, cands, weights, salience = compute_salience(C_lin, N_BINS, BPO, K)

    S_sal, pitch_bins, pitch_hz, times = extract_pitch(C_white, cands, salience, sr, HOP, fmin, BPO)

    print(f"{len(onset_times)} onsets, tempo {tempo:.1f} BPM")

    sonification_debug(pitch_hz, y, sr, HOP)

    notes = build_notes(onset_frames, pitch_bins, S_sal, SEUIL, rms, rms_db, DB_SEUIL)

    write_midi(notes, tempo, beat_times, fmin, BPO, HOP, sr, filename, music_dir, output_dir)
