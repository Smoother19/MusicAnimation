from pathlib import Path
from shutil import copy as cp

import presets
from transcription import analyze, write_midi

MUSIC_DIR = Path("sounds")
OUTPUT_DIR = Path("output")


def decode(filename: str, use_preset: bool = True, strict: bool = True) -> bool:
    OUTPUT_DIR.mkdir(exist_ok=True)

    if use_preset and Path(filename).suffix.lower() != ".mid":
        if presets.load(filename, strict=strict):
            return False

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