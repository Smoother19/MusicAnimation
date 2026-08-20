import pretty_midi as pm
import librosa as lr
from pathlib import Path
import numpy as np

def decode():
    file_dir = Path("output")
    filename = "transcription.mid"
    midi_data = pm.PrettyMIDI(file_dir / filename)

    print("\nStarting to decode midi file...")

    beats = midi_data.get_beats()
    intervals, pitches = midi_data.get_intervals_and_pitches()
    times, tempos = midi_data.get_tempo_changes()

    print(f"BPM : {tempos.max()}")
    print(f"Nbre de notes : {len(intervals)}")

    arr_fusionne = np.column_stack((intervals, pitches))

    return arr_fusionne, tempos.max()

    
