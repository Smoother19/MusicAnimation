"""Les transcriptions pre-calculees.

Transcrire un morceau coute plusieurs fois sa duree : deux minutes et demie
pour l'Ecossaise. C'est acceptable en developpement, pas devant un public.

Un preset est donc une transcription enregistree une fois pour toutes, avec
l'empreinte de la version de l'algorithme qui l'a produite. Au lancement,
si le preset existe ET que l'empreinte correspond au code actuel, on le
recopie au lieu de retranscrire ; sinon on le dit clairement, et on
retranscrit.

L'empreinte est le condensat du contenu des six fichiers du pipeline et des
reglages de transcription de config.py. C'est volontairement strict : une
virgule changee dans salience.py donne une autre empreinte, donc un preset
perime. Mieux vaut une alerte de trop qu'une demonstration qui montre les
resultats d'une version qu'on ne presente plus.

    python presets.py                 l'etat de tous les presets
    python pregenerate.py             (re)genere ceux des morceaux de demo
"""

import hashlib
import json
import shutil
from datetime import datetime
from pathlib import Path

PRESETS = Path("presets")
OUTPUT = Path("output")
SOUNDS = Path("sounds")

# Les fichiers dont le contenu definit la transcription. gui.py, shapes.py,
# flowers.py et le reste de l'animation n'y sont pas : ils ne changent pas
# une seule note du MIDI produit.
PIPELINE = ("salience.py", "notes.py", "timing.py", "harmonics.py",
            "instruments.py", "transcription.py")

# Les constantes de config.py qui pilotent la transcription. Le reste du
# fichier (couleurs, ciel, prairie, train) est ignore : une fleur plus
# grande ne perime pas un MIDI.
SETTINGS = (
    "SR", "N_FFT", "HOP", "N_ENV", "HOP_ENV",
    "N_PARTIALS", "ALPHA", "BETA", "MAX_NOTES", "SALIENCE_THRESHOLD",
    "CANCEL_FACTOR", "SILENCE_THRESHOLD", "MIN_FRAMES", "GAP_TOLERANCE",
    "MIDI_MIN", "MIDI_MAX", "ONSET_HOP", "ONSET_DELTA", "ONSET_WAIT",
    "ONSET_LAG", "SPLIT_RATIO", "SPLIT_GUARD", "SPLIT_WINDOW",
    "MIN_DURATION", "MERGE_GAP", "SNAP_TOLERANCE",
    "HARM_N_FFT", "HARM_HOP", "HARM_FMAX", "HARM_PARTIALS", "HARM_LOBE",
    "MIN_RELATIVE_ENERGY", "MAX_POLYPHONY", "POLYPHONY_MIN_FRACTION",
    "SUSTAIN_DELAY", "SUSTAIN_THRESHOLD", "FLATNESS_THRESHOLD",
    "ROLLOFF_THRESHOLD", "TEST_WEIGHTS", "TEST_SPREAD", "FUSION_THRESHOLD",
)


def fingerprint():
    "Empreinte courte de la version de l'algorithme, huit caracteres."
    digest = hashlib.sha256()
    for name in PIPELINE:
        path = Path(name)
        digest.update(path.read_bytes() if path.exists() else b"absent")
    import config
    for key in SETTINGS:
        digest.update(f"{key}={getattr(config, key, None)!r}".encode())
    return digest.hexdigest()[:8]


def stem(filename):
    "Le nom du preset d'un fichier audio : SuperMario.mp3 -> SuperMario."
    return Path(filename).stem


def folder(filename):
    return PRESETS / stem(filename)


def describe(filename):
    "Le contenu de preset.json, ou None si le preset n'existe pas."
    meta = folder(filename) / "preset.json"
    if not meta.exists():
        return None
    data = json.loads(meta.read_text())
    data["up_to_date"] = data.get("algo") == fingerprint()
    data["complete"] = (folder(filename) / "transcription.mid").exists()
    return data


def save(filename, notes, counts=None, seconds=None):
    """Enregistre la transcription d'un morceau comme preset.

    `notes` est la liste rendue par transcription.analyze ; le MIDI est
    reecrit ici plutot que copie depuis output/, pour que le preset ne
    depende pas d'un fichier de travail.
    """
    from transcription import write_midi

    target = folder(filename)
    target.mkdir(parents=True, exist_ok=True)
    written = write_midi(notes, str(target / "transcription.mid"))

    meta = {
        "source": Path(filename).name,
        "algo": fingerprint(),
        "notes": len(notes),
        "by_instrument": counts or written,
        "seconds": round(seconds, 1) if seconds else None,
        "generated": datetime.now().isoformat(timespec="seconds"),
    }
    (target / "preset.json").write_text(json.dumps(meta, indent=1))
    return meta


def load(filename, strict=True, verbose=True):
    """Installe le preset dans output/ s'il est utilisable.

    Rend True si l'animation peut demarrer sans transcrire. Avec
    strict=False, un preset perime est quand meme utilise -- utile en
    demonstration si le code a bouge pour une raison sans rapport avec la
    transcription.
    """
    meta = describe(filename)
    if meta is None or not meta["complete"]:
        return False

    if not meta["up_to_date"]:
        if verbose:
            print(f"preset {stem(filename)} : genere par la version "
                  f"{meta['algo']}, le code est en {fingerprint()}")
        if strict:
            if verbose:
                print("  -> ignore, on retranscrit "
                      "(python pregenerate.py pour le refaire)")
            return False
        if verbose:
            print("  -> utilise quand meme (strict=False)")

    OUTPUT.mkdir(exist_ok=True)
    shutil.copy(folder(filename) / "transcription.mid",
                OUTPUT / "transcription.mid")
    shutil.copy(SOUNDS / Path(filename).name, OUTPUT / "bg.mp3")
    if verbose:
        print(f"preset {stem(filename)} : {meta['notes']} notes, "
              f"version {meta['algo']}, genere le {meta['generated'][:10]}")
    return True


def status():
    "Une ligne par preset present sur le disque."
    current = fingerprint()
    rows = []
    if PRESETS.exists():
        for target in sorted(PRESETS.iterdir()):
            meta = target / "preset.json"
            if not meta.is_dir() and meta.exists():
                data = json.loads(meta.read_text())
                rows.append((target.name, data, data.get("algo") == current))
    return current, rows


if __name__ == "__main__":
    current, rows = status()
    print(f"version de l'algorithme : {current}\n")
    if not rows:
        print("aucun preset. `python pregenerate.py` pour les creer.")
    for name, data, ok in rows:
        print(f"{'OK ' if ok else '!! '}{name:16s} {data['notes']:5d} notes  "
              f"version {data['algo']}  "
              f"{data['generated'][:16].replace('T', ' ')}  "
              f"{'' if ok else '(perime)'}")
