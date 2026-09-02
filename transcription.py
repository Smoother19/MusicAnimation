import pretty_midi

from config import MAX_NOTES, MIDI_PROGRAMS
from notes import transcribe, merge_fragments
from instruments import measure, label, enforce_monophony
from timing import onset_times, split_on_onsets, snap_starts, decay_ends, clip_to_next
from harmonics import decompose, validate


def analyze(path, max_notes=MAX_NOTES, classify=True, refine_timing=True,
            validate_notes=True, trace=None):
    """Transcribe an audio file into notes.

    Five stages, each answering one failure of the previous version:

    1. the salience engine reports the pitches present in every frame;
    2. the frames are grouped into notes;
    3. the spectrum is decomposed over those notes, and each one is cut
       at the attacks where its own amplitude rises, so a key struck
       three times stops being one held note without a held note being
       shredded every time another instrument plays over it;
    4. the spectrum is decomposed again over the cut notes: the ones the
       model does not need are dropped, the others are measured;
    5. the timing is pulled onto the detected onsets and the three timbre
       tests name the instrument.

    `trace` is an optional callback trace(label, notes) called after every
    stage. It is what benchmark.py reads to measure the pipeline stage by
    stage without holding a second, drifting copy of this function.
    """
    step = trace or (lambda label, notes: None)

    y, notes = transcribe(path, max_notes)
    step("groupement", notes)
    onsets = onset_times(y)

    notes = split_on_onsets(notes, onsets, decompose(y, notes))
    step("decoupe", notes)
    notes = merge_fragments(notes, onsets)
    step("recollage", notes)
    notes = snap_starts(notes, onsets)
    step("calage", notes)

    # Second decomposition: the cut notes, for validation and timbre.
    harmonics = decompose(y, notes)
    if validate_notes:
        notes, harmonics = validate(notes, harmonics)
    step("validation", notes)

    if refine_timing:
        decay_ends(y, notes, ratio=0.15)
        clip_to_next(notes)
        step("durees", notes)

    if classify:
        measure(y, notes, harmonics)
        label(notes)
        enforce_monophony(notes)
        step("classification", notes)

    return notes


def write_midi(notes, path):
    """Write the notes to a MIDI file, one track per instrument.

    Returns the note count per track.
    """
    out = pretty_midi.PrettyMIDI(resolution=600)
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
    AUDIO = "./sounds/Ecossaise_Both.mp3"
    OUTPUT = "transcription_2tracks.mid"

    notes = analyze(AUDIO)
    print(f"{len(notes)} notes detected")

    for name, count in write_midi(notes, OUTPUT).items():
        print(f"  {name:8s}: {count} notes")
    print(f"written: {OUTPUT}")
