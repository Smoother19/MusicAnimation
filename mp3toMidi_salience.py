from pathlib import Path
from shutil import copy as cp

from transcription import analyze, write_midi

MUSIC_DIR = Path("sounds")
OUTPUT_DIR = Path("output")


def decode(filename: str) -> bool:
    """Transcribe an audio file to output/transcription.mid.

    Returns True when the input was already a MIDI file.
    """
    OUTPUT_DIR.mkdir(exist_ok=True)

    if Path(filename).suffix.lower() == ".mid":
        cp(MUSIC_DIR / filename, OUTPUT_DIR / "transcription.mid")
        print("The input file is already a Midi file!")
        return True

    notes = analyze(str(MUSIC_DIR / filename))
    counts = write_midi(notes, str(OUTPUT_DIR / "transcription.mid"))
    print(f"{len(notes)} notes: " +
          ", ".join(f"{n} {c}" for n, c in counts.items()))

    cp(MUSIC_DIR / filename, OUTPUT_DIR / "bg.mp3")
    return False