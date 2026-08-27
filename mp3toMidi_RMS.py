from pathlib import Path
from shutil import copy as cp
import numpy as np
import librosa as lr
import pretty_midi as pm
from scipy.ndimage import uniform_filter1d, median_filter
import matplotlib.pyplot as plt

music_dir = Path("sounds")
output_dir = Path("output")

sampling_rate = 44100
hop_length = 256
frame_length = 2048

def handle_midi_passthrough(filename: str, music_dir, output_dir) -> bool:
    filetype = Path(filename).suffix
    if ".mid" in filetype:
        cp(music_dir / filename, output_dir / "transcription.mid")
        print("The input file is already a Midi file !")
        return True
    return False

def load_audio(filename: str, music_dir):
    y, sr = lr.load(music_dir / filename, sr=sampling_rate)
    duration = len(y) / sampling_rate
    print(f"MP3 Duration : {duration}s - Sampling Rate : {sr}")
    return y,sr,duration

def stft_calculation(y, sr):
    S_stft = lr.stft(y, hop_length=hop_length)

    fig, ax = plt.subplots(nrows=2, sharex=True)
    img = lr.display.specshow(S_stft, vscale="dBFS",
                                sr=sr, hop_length=hop_length, x_axis="time", y_axis="hz", ax=ax[0])
    lr.display.colorbar_db(img, label="dBFS")
    ax[0].set(title="Spectrogram")
    ax[0].label_outer()
    lr.display.waveshow(y, sr=sr, ax=ax[1])
    ax[1].set(title="Time-domain")

    plt.savefig(output_dir / "STFT")
    plt.close()

    return S_stft

def rms_calculation(y,sr,S_stft):
    rms = lr.feature.rms(y=y, frame_length=frame_length, hop_length=hop_length)[0]
    times = lr.frames_to_time(np.arange(len(rms)), sr=sr, hop_length=hop_length)

    fig, ax = plt.subplots(nrows=2, sharex=True)
    times = lr.times_like(rms)
    ax[0].semilogy(times, rms, label='RMS Energy')
    ax[0].set(xticks=[])
    ax[0].legend()
    ax[0].label_outer()
    lr.display.specshow(S_stft, vscale='dBFS',
                            y_axis='log', x_axis='time', ax=ax[1])
    ax[1].set(title='log Power spectrogram')

    plt.savefig(output_dir / "RMS")
    plt.close()

    return rms, times

def onsetDetection(y,rms,times,sr,S_stft):
    onset_frames = lr.onset.onset_detect(
        onset_envelope=rms,
        sr=sr,
        hop_length=hop_length,
        backtrack=True
    )
    
    onset_times = lr.frames_to_time(onset_frames, sr=sr, hop_length=hop_length)

    logS = lr.amplitude_to_db(np.abs(S_stft), ref=np.max)
    onset_env = np.mean(np.maximum(np.diff(logS,axis=-1,prepend=logS[:,:1]),0),axis=0)

    onset_peaks = lr.util.localmax(onset_env)

    onset_detect = lr.onset.onset_detect(onset_envelope=onset_env)

    peak_pick = lr.util.peak_pick(x=onset_env,pre_max=12, post_max=12, pre_avg=12, post_avg=15, delta=2, wait=10, method="dp_value")

    decay_times = []
    for peak in peak_pick:
        decay_time = (find_decay_time(rms, peak, sr, hop_length, ratio=0.6))
        decay_times.append(decay_time)

    fig, ax = plt.subplots(nrows=2, sharex=True, height_ratios=(3, 1))

    lr.display.waveshow(y=y, sr=sr, ax=ax[1], label="Waveform")
    ax[1].legend()
    ax[0].plot(times, onset_env, label="Onset envelope", color="C1")
    ax[0].scatter(times[onset_peaks], onset_env[onset_peaks], marker="^", color="k", label="Localmax Peaks")
    ax[0].scatter(times[peak_pick], onset_env[peak_pick], marker="x", color="blue", label="peak_pick")
    ax[0].scatter(times[onset_detect], onset_env[onset_detect], marker="o",
                edgecolor="C2", facecolor="none", label="onset_detect")
    ax[0].legend()
    ax[0].label_outer()

    plt.savefig(output_dir / "OnSet_detect")
    plt.close()



    fig, ax = plt.subplots(nrows=2, sharex=True, height_ratios=(3, 1))
    times = lr.times_like(rms, sr=sr, hop_length=hop_length)
    ax[0].semilogy(times, rms, label='RMS Energy', color='C0')
    ax[0].set(xticks=[])
    ax[0].legend(loc='upper right')
    ax[0].label_outer()

    peak_times = lr.frames_to_time(peak_pick, sr=sr, hop_length=hop_length)
    ax[0].scatter(peak_times, rms[peak_pick], marker='x', color='red',
                  s=50, label='peak_pick', zorder=5)
    ax[0].legend(loc='upper right')

    
    lr.display.specshow(S_stft, vscale='dBFS', sr=sr,
                        y_axis='log', x_axis='time', ax=ax[1])
    ax[1].set(title='log Power spectrogram')

    plt.tight_layout()
    plt.savefig(output_dir / "RMS_peak")
    plt.close()

    return onset_frames, onset_times, onset_detect, peak_pick, decay_times

def find_decay_time(rms, peak_idx, sr, hop_length, ratio=0.6):
    threshold = ratio * rms[peak_idx]
    nbre_frames_rms = len(rms)

    for i in range(peak_idx + 1, nbre_frames_rms):
        if rms[i] < threshold:
            return i * hop_length / sr

    return (nbre_frames_rms - 1) * hop_length / sr


def create_segments(peak_pick,rms,y,sr,hop_length,S_stft,decay_times):
    segments = []
    nbre_frames_rms = len(rms)
    nbre_peaks = len(peak_pick)

    for i in range(nbre_peaks):
        start_frame = peak_pick[i]
        end_frame = peak_pick[i+1] if (i+1 < nbre_peaks) else nbre_frames_rms

        if end_frame <= start_frame:
            continue

        rms_segment = rms[start_frame:end_frame]

        instrument = find_instrument(rms_segment)
        
        start_sample = start_frame * hop_length
        end_sample = end_frame * hop_length
        y_segment = y[start_sample:end_sample]

        start_time = start_frame * hop_length / sr
        end_time = decay_times[i]

        midi_note = get_midi_note(y_segment=y_segment,sr=sr, stft=S_stft)

        if midi_note is None:
            english_note = None
        else:
            english_note = lr.midi_to_note(midi_note)

        segments.append({
            "start_frame": start_frame,
            "end_frame": end_frame,
            "start_time": start_time,
            "end_time": end_time,
            "y_segment": y_segment,
            "rms_segment": rms_segment,
            "instrument": instrument,
            "midi_note": midi_note,
            "english_note" : english_note
        })

    return segments

def find_instrument(rms_segment):
    # Segment trop court pour être analysé fiablement. Difficile d'avoir une note courte à la trompette, donc probablement du piano
    if len(rms_segment) < 10:
        return "piano"

    peak_idx = np.argmax(rms_segment)
    decay_idx = min(peak_idx + 10, len(rms_segment) - 1)
    decay = rms_segment[decay_idx]

    diff = rms_segment[peak_idx] - decay
    diff_int = int(diff * 1000)

    #print(diff_int)

    if diff_int < 40:
        return "trompette"
    else:
        return "piano"
        
def get_midi_note(y_segment, sr, stft):
    f0, voiced_flag, voiced_prob = lr.pyin(
        y=y_segment,
        fmin=lr.note_to_hz('C2'),
        fmax=22050,
        sr=sr,
        frame_length=frame_length,
        hop_length=hop_length
    )

    ''' 
    times = lr.times_like(f0)

    fig, ax = plt.subplots()
    lr.display.specshow(stft, vscale="dBFS",
                            x_axis="time", y_axis="log", ax=ax)
    hl = lr.display.highlight(ax=ax, alpha=0.8, linewidth=4)
    ax.plot(times, f0, label="pyin f0 estimate", path_effects=hl)
    ax.legend(loc="upper right")

    plt.show()
    plt.close()
    '''

    pitch = np.nanmedian(f0)
    #print(pitch)
    midi_note = hz_to_midi_note(pitch)
    return midi_note

def hz_to_midi_note(pitch_hz):
    mn = lr.hz_to_midi(pitch_hz)
    if np.isnan(mn):
        return None
    else:
        midi_note = int(round(mn))
        return midi_note

def generate_midi(segments):
    midi = pm.PrettyMIDI(resolution=600)

    piano_track = pm.Instrument(program=0, name="Piano")
    trumpet_track = pm.Instrument(program=56, name="Trompette")

    for seg in segments: 
        if seg["midi_note"] is None:
            continue

        note = pm.Note(
            velocity=100,
            pitch=seg["midi_note"],
            start=seg["start_time"],
            end=seg["end_time"]
        )

        match seg["instrument"]:
            case "piano":
                piano_track.notes.append(note)
            case "trompette":
                trumpet_track.notes.append(note)
            case _:
                continue

    midi.instruments.append(piano_track)
    midi.instruments.append(trumpet_track)

    midi.write(output_dir / "transcription.mid")
    print("Fichier MIDI généré")

def generateBgMusic(fn):
    cp(music_dir / fn, output_dir / "bg.mp3")


def decode(filename: str):
    if handle_midi_passthrough(filename, music_dir, output_dir):
        return True

    y, sr, duration = load_audio(filename, music_dir)
    S_stft = stft_calculation(y,sr)
    rms, times = rms_calculation(y,sr,S_stft)
    onset_frames, onset_times, onset_detect, peak_pick, decay_times = onsetDetection(y,rms,times,sr,S_stft)
    segments = create_segments(peak_pick,rms,y,sr,hop_length,S_stft,decay_times)
    '''
    for segment in segments:
    print(segment["instrument"])
    print(segment["midi_note"])
    print(segment["english_note"])
    '''
    generate_midi(segments=segments)
    generateBgMusic(filename)
    return False