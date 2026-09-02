import json
import shutil
from datetime import datetime
from pathlib import Path

ROOT = Path(__file__).resolve().parent
PRESETS = ROOT / "presets"
OUTPUT = ROOT / "output"
SOUNDS = ROOT / "sounds"


def stem(filename):
    return Path(filename).stem


def folder(filename):
    return PRESETS / stem(filename)


def describe(filename):
    meta = folder(filename) / "preset.json"
    if not meta.exists():
        return None
    data = json.loads(meta.read_text())
    data["complete"] = (folder(filename) / "transcription.mid").exists()
    return data


def save(filename, notes, counts=None, seconds=None):

    from transcription import write_midi

    target = folder(filename)
    target.mkdir(parents=True, exist_ok=True)
    written = write_midi(notes, str(target / "transcription.mid"))

    meta = {
        "source": Path(filename).name,
        "notes": len(notes),
        "by_instrument": counts or written,
        "seconds": round(seconds, 1) if seconds else None,
        "generated": datetime.now().isoformat(timespec="seconds"),
    }
    (target / "preset.json").write_text(json.dumps(meta, indent=1))
    return meta


def load(filename, verbose=True):
    """Installe le preset dans output/ s'il existe.

    Rend True si l'animation peut demarrer sans transcrire.
    """
    meta = describe(filename)
    if meta is None or not meta["complete"]:
        return False

    OUTPUT.mkdir(exist_ok=True)
    shutil.copy(folder(filename) / "transcription.mid",
                OUTPUT / "transcription.mid")
    shutil.copy(SOUNDS / Path(filename).name, OUTPUT / "bg.mp3")
    if verbose:
        print(f"preset {stem(filename)} : {meta['notes']} notes, "
              f"genere le {meta['generated'][:10]}")
    return True


def status():
    "Une ligne par preset present sur le disque."
    rows = []
    if PRESETS.exists():
        for target in sorted(PRESETS.iterdir()):
            meta = target / "preset.json"
            if not meta.is_dir() and meta.exists():
                rows.append((target.name, json.loads(meta.read_text())))
    return rows


if __name__ == "__main__":
    rows = status()
    if not rows:
        print("aucun preset. `python pregenerate.py` pour les creer.")
    for name, data in rows:
        parts = ", ".join(f"{k} {v}" for k, v in
                          (data.get("by_instrument") or {}).items())
        print(f"{name:16s} {data['notes']:5d} notes  "
              f"{data['generated'][:16].replace('T', ' ')}  {parts}")
