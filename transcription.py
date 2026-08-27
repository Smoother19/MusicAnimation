import pretty_midi

from config import MAX_NOTES, MIDI_PROGRAMS
from notes import transcribe
from instruments import measure, label, enforce_monophony


def analyze(path, max_notes=MAX_NOTES, classify=True):
    """Transcribe a file and return its notes, labelled by instrument."""
    y, notes = transcribe(path, max_notes)

    if classify:
        measure(y, notes)
        label(notes)
        enforce_monophony(notes)

    return notes


def write_midi(notes, path):
    """Write the notes to a MIDI file, one track per instrument.

    Returns the note count per track.
    """
    out = pretty_midi.PrettyMIDI()
    tracks = {}

    for note in notes:
        name = note.instrument or "piano"
        if name not in tracks:
            tracks[name] = pretty_midi.Instrument(
                program=MIDI_PROGRAMS.get(name, 0), name=name)
        start, end = note.seconds()
        tracks[name].notes.append(pretty_midi.Note(
            velocity=90, pitch=note.midi, start=start, end=end))

    out.instruments.extend(tracks.values())
    out.write(path)

    return {name: len(track.notes) for name, track in tracks.items()}


def decode(audio_path, midi_path=None):
    """Transcribe an audio file to MIDI and return the output path."""
    if midi_path is None:
        midi_path = audio_path.rsplit(".", 1)[0] + ".mid"

    write_midi(analyze(audio_path), midi_path)
    return midi_path


if __name__ == "__main__":
    AUDIO = "./sounds/PinkPanther_Both.mp3"
    OUTPUT = "transcription_2tracks.mid"

    notes = analyze(AUDIO)
    print(f"{len(notes)} notes detected")

    for name, count in write_midi(notes, OUTPUT).items():
        print(f"  {name:8s}: {count} notes")
    print(f"written: {OUTPUT}")