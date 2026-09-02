from pathlib import Path
from shutil import copy as cp

import presets

# `transcription` n'est PAS importe ici : il tire librosa, scipy et tout le
# moteur d'analyse. Quand un preset existe -- le cas en demonstration -- on
# n'en a aucun besoin, et l'import seul coute plusieurs secondes sur une
# installation ou librosa n'est pas paresseux. Il est donc importe dans la
# branche qui transcrit, et nulle part ailleurs.

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

    from transcription import analyze, write_midi

    print("aucun preset utilisable : transcription en cours, "
          "cela prend a peu pres la duree du morceau...")
    notes = analyze(str(MUSIC_DIR / filename))
    counts = write_midi(notes, str(OUTPUT_DIR / "transcription.mid"))
    print(f"{len(notes)} notes: " +
          ", ".join(f"{n} {c}" for n, c in counts.items()))

    cp(MUSIC_DIR / filename, OUTPUT_DIR / "bg.mp3")
    return False