"""Le corpus de mesure : quels morceaux, et quelle verite de terrain.

Chaque entree relie un melange audio a la partition dont il a ete rendu.
C'est cette partition qui sert de reference : elle est exacte par
construction, contrairement a une annotation faite a l'oreille.

`melody` est le NOM de la piste du MIDI de reference que la trompette joue
dans le melange. Il faut le declarer explicitement : la separation par
registre ne marche pas. Sur l'Ecossaise la trompette tient 48-63 et le
piano 34-82 -- le piano y joue donc en moyenne plus aigu que la melodie, et
la regle << aigu = trompette >> y tombe a 27 % de justesse equilibree quand
les pistes en donnent 76 %.

Les fichiers separes (`piano`, `trumpet`) sont facultatifs : ils servent a
calibrer les seuils de timbre sur un instrument seul, jamais a mesurer la
detection, qui doit toujours se faire sur le melange.
"""

from pathlib import Path

SOUNDS = Path("sounds")


def _entry(name, mix, reference, melody, piano=None, trumpet=None, note=""):
    return {
        "name": name,
        "mix": str(SOUNDS / mix),
        "reference": str(SOUNDS / reference),
        "melody": melody,
        "piano": str(SOUNDS / piano) if piano else None,
        "trumpet": str(SOUNDS / trumpet) if trumpet else None,
        "note": note,
    }


CORPUS = {e["name"]: e for e in [
    _entry("Gamme", "Gamme.mp3", "Gamme.mid", "Trumpet",
           "Gamme_Piano.mp3", "Gamme_Trumpet.mp3",
           "52 notes, deux gammes croisees -- le cas d'ecole"),
    _entry("SuperMario", "SuperMario.mp3", "SuperMario.mid", "Trumpet",
           "SuperMarion_Piano.mp3", "SuperMarion_Trumpet.mp3",
           "189 notes tres courtes (mediane 0.10 s) -- teste la resolution"),
    _entry("Ecossaise", "Ecossaise_Both.mp3", "Ecossaise_Beethoven.midi",
           "Flute", "Ecossaise_Piano.mp3", "Ecossaise_Trumpet.mp3",
           "747 notes, 6 voix de piano -- le morceau de calibration"),
    _entry("PinkPanther", "PinkPanther_Both.mp3", "PinkPanther.midi",
           "1./2.fl ", "PinkPanther_Piano_Only.mp3",
           "PinkPanther_Trumpet_Only.mp3",
           "451 notes, 2 min 20 -- le plus long"),
    # Piege : dans SSB.mid la piste nommee "Piano" est celle que la
    # trompette joue, et la piste sans nom est l'accompagnement. Le banc
    # l'a trouve tout seul -- avec l'autre affectation, la justesse
    # equilibree tombait a 31 %, donc sous le hasard. Un classifieur
    # systematiquement anti-correle n'est pas un classifieur casse, c'est
    # une verite de terrain a l'envers.
    _entry("SSB", "SSB.mp3", "SSB.mid", "Piano",
           "SSB_Piano.mp3", "SSB_Trumpet.mp3",
           "109 notes ; l'etiquetage des pistes du MIDI est trompeur"),
]}

# Les deux morceaux de la presentation, dans l'ordre ou ils sont montres.
DEMO = ("SuperMario", "Gamme")


def get(name):
    if name not in CORPUS:
        raise KeyError(f"morceau inconnu : {name}. Connus : "
                       + ", ".join(CORPUS))
    return CORPUS[name]


def available():
    "Les morceaux dont tous les fichiers sont presents sur le disque."
    out = []
    for name, entry in CORPUS.items():
        if Path(entry["mix"]).exists() and Path(entry["reference"]).exists():
            out.append(name)
    return out


if __name__ == "__main__":
    for name, entry in CORPUS.items():
        ok = "  " if name in available() else "!!"
        print(f"{ok} {name:14s} {Path(entry['mix']).name:24s} "
              f"ref {Path(entry['reference']).name:26s} "
              f"melodie {entry['melody']!r}")
        print(f"     {entry['note']}")
