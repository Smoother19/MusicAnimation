import pretty_midi as pm
import librosa as lr
from pathlib import Path
import numpy as np

def decode():
    file_dir = Path("output")
    filename = "transcription.mid"
    midi_data = pm.PrettyMIDI(file_dir / filename)

    print("\nStarting to decode midi file...")

    times, tempos = midi_data.get_tempo_changes()

    notes = [(n.start, n.end, lr.midi_to_hz(n.pitch), inst.name or "piano")
             for inst in midi_data.instruments for n in inst.notes]
    notes.sort(key=lambda row: row[0])

    print(f"BPM : {tempos.max()}")
    print(f"Nbre de notes : {len(notes)}")
    for inst in midi_data.instruments:
        print(f"  {inst.name or 'piano'} : {len(inst.notes)} notes")

    return notes, tempos.max()

    
