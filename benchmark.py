"""Banc de mesure : toutes les statistiques de l'algorithme, sur tous les
morceaux du corpus.

    python benchmark.py run                 mesure tout, ecrit bench/results.json
    python benchmark.py run SuperMario      un seul morceau
    python benchmark.py report              les tableaux, depuis le JSON
    python benchmark.py charts              les graphiques, depuis le JSON
    python benchmark.py calibrate           les seuils de timbre, morceau par morceau
    python benchmark.py html                bench/rapport.html, tout au meme endroit
    python benchmark.py all                 la chaine complete

La mesure est longue (elle transcrit chaque morceau), les tableaux et les
graphiques ne le sont pas : ils relisent bench/results.json. C'est la
raison de la separation -- on mesure une fois, on refait les figures
autant de fois qu'on veut.

Ce que le banc mesure, par morceau :

  detection     rappel, precision, F1, rapport de comptage
  entonnoir     le nombre de notes en sortie de chaque etape du pipeline
  timing        erreur d'attaque, mediane / moyenne / 90e centile
  fantomes      la relation harmonique de chaque fausse note a une note reelle
  instruments   justesse par classe et justesse equilibree
  cout          duree de chaque etape, et facteur temps reel
"""

import json
import statistics as st
import sys
import time
from collections import Counter
from pathlib import Path

import numpy as np
import pretty_midi

import corpus

BENCH = Path("bench")
RESULTS = BENCH / "results.json"

TOLERANCE = 0.15        # secondes : au-dela, l'attaque ne compte pas comme trouvee
MIN_PITCH = 21          # en dessous de la0, la note du MIDI est un artefact
MIN_DURATION = 0.02

# Les relations harmoniques cherchees entre une fausse note et une note qui
# sonne au meme instant, en demi-tons. L'ordre compte : on retient la
# premiere qui colle, donc les octaves avant les quintes.
RELATIONS = ((12, "octave +12"), (-12, "octave -12"),
             (19, "douzieme +19"), (-19, "douzieme -19"),
             (7, "quinte +7"), (-7, "quinte -7"),
             (24, "double octave +24"), (-24, "double octave -24"))


# --- verite de terrain --------------------------------------------------

def reference_notes(entry):
    """(instrument, hauteur, debut, fin) de chaque note de la partition.

    Les notes de moins de 20 ms et celles sous la0 sont ecartees : les
    exports MIDI en trainent (l'Ecossaise porte des notes de hauteur 0)
    et elles gonfleraient artificiellement le denominateur du rappel.
    """
    midi = pretty_midi.PrettyMIDI(entry["reference"])
    melody = entry["melody"]
    unnamed_is_melody = melody is None

    out = []
    for track in midi.instruments:
        name = track.name or ""
        is_melody = (name == melody) if not unnamed_is_melody else not name
        kind = "trumpet" if is_melody else "piano"
        for note in track.notes:
            if note.end - note.start > MIN_DURATION and note.pitch >= MIN_PITCH:
                out.append((kind, note.pitch, note.start, note.end))
    out.sort(key=lambda row: row[2])
    return out


# --- mesures ------------------------------------------------------------

def detection(notes, reference):
    "Rappel, precision, F1 et rapport de comptage."
    expected = [(pitch, start) for _, pitch, start, _ in reference]
    obtained = [(n.midi, n.seconds()[0]) for n in notes]

    def close(a, b):
        return a[0] == b[0] and abs(a[1] - b[1]) < TOLERANCE

    found = sum(1 for e in expected if any(close(e, o) for o in obtained))
    correct = sum(1 for o in obtained if any(close(e, o) for e in expected))

    recall = found / max(1, len(expected))
    precision = correct / max(1, len(obtained))
    return {
        "reference": len(expected),
        "detected": len(obtained),
        "ratio": len(obtained) / max(1, len(expected)),
        "recall": recall,
        "precision": precision,
        "f1": 2 * recall * precision / (recall + precision + 1e-9),
    }


def timing(notes, reference):
    """Erreur d'attaque des notes retrouvees.

    Mesuree sur les seules notes appariees : une fausse note n'a pas
    d'attaque de reference a laquelle se comparer, et une note manquee
    n'a pas d'attaque du tout.
    """
    errors = []
    for note in notes:
        start = note.seconds()[0]
        best = min((abs(start - s) for _, pitch, s, _ in reference
                    if pitch == note.midi), default=None)
        if best is not None and best < TOLERANCE:
            errors.append(1000 * best)
    if not errors:
        return {"n": 0, "median": None, "mean": None, "p90": None}
    ordered = sorted(errors)
    return {
        "n": len(errors),
        "median": st.median(ordered),
        "mean": st.mean(ordered),
        "p90": ordered[min(len(ordered) - 1, int(0.90 * len(ordered)))],
    }


def ghosts(notes, reference):
    """La relation harmonique de chaque fausse note a ce qui sonnait.

    C'est la mesure qui dit si les erreurs sont du bruit ou une propriete
    de la methode : un fantome d'octave n'est pas une erreur de reglage,
    c'est la consequence du fait que les partiels de l'octave sont un
    sous-ensemble exact de ceux de sa fondamentale.
    """
    def matched(pitch, start):
        return any(p == pitch and abs(s - start) < TOLERANCE
                   for _, p, s, _ in reference)

    counts = Counter()
    total = 0
    for note in notes:
        pitch, start = note.midi, note.seconds()[0]
        if matched(pitch, start):
            continue
        total += 1
        sounding = {pitch - p for _, p, s, e in reference
                    if abs(s - start) < TOLERANCE or s - TOLERANCE <= start <= e}
        for delta, label in RELATIONS:
            if delta in sounding:
                counts[label] += 1
                break
        else:
            counts["sans relation"] += 1

    harmonic = total - counts["sans relation"]
    return {
        "total": total,
        "harmonic": harmonic,
        "share": harmonic / total if total else 0.0,
        "by_relation": dict(counts),
    }


def instruments(notes, reference):
    "Justesse par classe et justesse equilibree, sur les notes appariees."
    hits = {"piano": [0, 0], "trumpet": [0, 0]}
    for kind, pitch, start, _ in reference:
        for note in notes:
            if note.midi == pitch and abs(note.seconds()[0] - start) < TOLERANCE:
                hits[kind][1] += 1
                hits[kind][0] += int(note.instrument == kind)
                break

    rates = {k: (ok / total if total else 0.0) for k, (ok, total) in hits.items()}
    return {
        "piano": rates["piano"], "trumpet": rates["trumpet"],
        "balanced": (rates["piano"] + rates["trumpet"]) / 2,
        "counts": {k: list(v) for k, v in hits.items()},
    }


def polyphony(notes):
    "Polyphonie maximale et moyenne de ce qui a ete detecte."
    events = []
    for note in notes:
        s, e = note.seconds()
        events += [(s, 1), (e, -1)]
    events.sort()
    current = peak = 0
    weighted, last = 0.0, None
    for t, delta in events:
        if last is not None and current:
            weighted += current * (t - last)
        current += delta
        peak = max(peak, current)
        last = t
    span = (events[-1][0] - events[0][0]) if events else 0.0
    return {"peak": peak, "mean": weighted / span if span else 0.0}


# --- un morceau ---------------------------------------------------------

def measure(name):
    "Toutes les statistiques d'un morceau. Transcrit, donc c'est lent."
    import librosa                    # 3 s a l'import : seul `run` en a besoin
    from transcription import analyze

    entry = corpus.get(name)
    reference = reference_notes(entry)
    duration = librosa.get_duration(path=entry["mix"])

    stages, marks = [], [time.perf_counter()]

    def trace(label, notes):
        now = time.perf_counter()
        stages.append({"stage": label, "notes": len(notes),
                       "seconds": now - marks[-1]})
        marks.append(now)

    started = time.perf_counter()
    notes = analyze(entry["mix"], trace=trace)
    elapsed = time.perf_counter() - started

    # L'entonnoir : le rappel et la precision a chaque etape demanderaient
    # de reevaluer sur les notes intermediaires, ce que trace ne conserve
    # pas. On garde le comptage, qui est ce qui pilote l'animation.
    result = {
        "name": name,
        "note": entry["note"],
        "audio_seconds": duration,
        "compute_seconds": elapsed,
        "realtime": elapsed / duration if duration else 0.0,
        "stages": stages,
        "detection": detection(notes, reference),
        "timing": timing(notes, reference),
        "ghosts": ghosts(notes, reference),
        "instruments": instruments(notes, reference),
        "polyphony": polyphony(notes),
        # Les trois descripteurs de chaque note, avec la classe que la
        # partition lui donne (None si la note est fausse). C'est ce qui
        # permet de recalibrer les seuils sans retranscrire : on mesure une
        # fois, on rejoue l'analyse autant de fois qu'on veut.
        "descriptors": [
            [next((k for k, p, st_, _ in reference
                   if p == n.midi and abs(st_ - n.seconds()[0]) < TOLERANCE),
                  None),
             n.sustain, n.flatness, n.rolloff, round(n.score, 4), n.midi]
            for n in notes],
        "reference_by_instrument": dict(Counter(k for k, *_ in reference)),
        "detected_by_instrument": dict(Counter(n.instrument or "piano"
                                               for n in notes)),
    }
    return result


def run(names=None):
    names = list(names) if names else corpus.available()
    BENCH.mkdir(exist_ok=True)

    results = {}
    if RESULTS.exists():
        results = json.loads(RESULTS.read_text())

    for name in names:
        print(f"\n=== {name} " + "=" * (60 - len(name)))
        started = time.perf_counter()
        results[name] = measure(name)
        d = results[name]["detection"]
        print(f"  {d['detected']} notes ({d['ratio']:.2f}x)  "
              f"rappel {100 * d['recall']:.0f} %  "
              f"precision {100 * d['precision']:.0f} %  "
              f"en {time.perf_counter() - started:.0f} s")

    results = {k: results[k] for k in corpus.CORPUS if k in results}
    RESULTS.write_text(json.dumps(results, indent=1))
    print(f"\necrit : {RESULTS}")
    return results


# --- tableaux -----------------------------------------------------------

def load():
    if not RESULTS.exists():
        sys.exit(f"{RESULTS} absent : lance d'abord `python benchmark.py run`")
    return json.loads(RESULTS.read_text())


def report(results=None):
    results = results or load()
    rows = list(results.values())

    print("\nDETECTION")
    print(f"{'morceau':14s} {'ref':>5s} {'trouve':>7s} {'rapport':>8s} "
          f"{'rappel':>7s} {'precis.':>8s} {'F1':>6s}")
    for r in rows:
        d = r["detection"]
        print(f"{r['name']:14s} {d['reference']:5d} {d['detected']:7d} "
              f"{d['ratio']:7.2f}x {100 * d['recall']:6.0f}% "
              f"{100 * d['precision']:7.0f}% {100 * d['f1']:5.1f}")

    print("\nTIMING DES ATTAQUES  (ms)")
    print(f"{'morceau':14s} {'appariees':>10s} {'mediane':>8s} "
          f"{'moyenne':>8s} {'90e c.':>8s}")
    for r in rows:
        t = r["timing"]
        if not t["n"]:
            print(f"{r['name']:14s} {'aucune':>10s}")
            continue
        print(f"{r['name']:14s} {t['n']:10d} {t['median']:7.1f} "
              f"{t['mean']:7.1f} {t['p90']:7.1f}")

    print("\nFAUSSES NOTES")
    print(f"{'morceau':14s} {'total':>6s} {'harmoniques':>12s} {'part':>6s}   "
          f"principales relations")
    for r in rows:
        g = r["ghosts"]
        top = sorted(g["by_relation"].items(), key=lambda kv: -kv[1])[:3]
        print(f"{r['name']:14s} {g['total']:6d} {g['harmonic']:12d} "
              f"{100 * g['share']:5.0f}%   "
              + ", ".join(f"{k} : {v}" for k, v in top))

    print("\nINSTRUMENTS  (justesse sur les notes appariees)")
    print(f"{'morceau':14s} {'piano':>8s} {'trompette':>11s} {'equilibree':>11s}")
    for r in rows:
        i = r["instruments"]
        print(f"{r['name']:14s} {100 * i['piano']:7.0f}% "
              f"{100 * i['trumpet']:10.0f}% {100 * i['balanced']:10.0f}%")

    print("\nCOUT")
    print(f"{'morceau':14s} {'audio':>8s} {'calcul':>8s} {'x temps reel':>13s}   "
          f"etape la plus chere")
    for r in rows:
        worst = max(r["stages"], key=lambda s: s["seconds"])
        print(f"{r['name']:14s} {r['audio_seconds']:7.0f}s "
              f"{r['compute_seconds']:7.0f}s {r['realtime']:12.2f}x   "
              f"{worst['stage']} ({worst['seconds']:.0f} s)")

    print("\nENTONNOIR  (notes en sortie de chaque etape)")
    labels = [s["stage"] for s in rows[0]["stages"]]
    print(f"{'morceau':14s} " + " ".join(f"{l[:9]:>10s}" for l in labels))
    for r in rows:
        print(f"{r['name']:14s} "
              + " ".join(f"{s['notes']:10d}" for s in r["stages"]))
    print()


# --- graphiques ---------------------------------------------------------

# Palette validee pour la vision des couleurs (ecart CVD >= 8 en OKLab) :
# laiton, bleu, vert, rouge, sur un fond creme.
LAITON, BLEU, VERT, ROUGE = "#B07D14", "#1F6F9E", "#4C7A2E", "#B03A3A"
ACIER, ENCRE, MUET, FOND = "#787E8A", "#1C1E24", "#5F6470", "#FCFCFB"


def _style():
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    plt.rcParams.update({
        "figure.facecolor": FOND, "axes.facecolor": FOND,
        "font.family": "DejaVu Sans", "font.size": 11,
        "axes.edgecolor": "#CFD4DC", "axes.labelcolor": ENCRE,
        "text.color": ENCRE, "xtick.color": MUET, "ytick.color": MUET,
        "axes.titlecolor": ENCRE, "grid.color": "#E2E6EB", "grid.linewidth": .8,
        "axes.spines.top": False, "axes.spines.right": False,
        "axes.titlesize": 12.5, "axes.titleweight": "bold", "axes.titlepad": 12,
    })
    return plt


def charts(results=None):
    results = results or load()
    rows = list(results.values())
    names = [r["name"] for r in rows]
    plt = _style()
    BENCH.mkdir(exist_ok=True)
    written = []

    def save(fig, filename):
        path = BENCH / filename
        fig.savefig(path, dpi=170, bbox_inches="tight")
        plt.close(fig)
        written.append(path)

    x = np.arange(len(names))

    # 1. detection : rappel et precision, une seule echelle
    fig, (a, b) = plt.subplots(1, 2, figsize=(2.0 * len(rows) + 6.5, 4.6),
                               gridspec_kw={"width_ratios": [1.5, 1]})
    w = 0.38
    a.bar(x - w / 2, [100 * r["detection"]["recall"] for r in rows], w,
          color=BLEU, label="rappel", zorder=3)
    a.bar(x + w / 2, [100 * r["detection"]["precision"] for r in rows], w,
          color=VERT, label="precision", zorder=3)
    for i, r in enumerate(rows):
        a.text(i - w / 2, 100 * r["detection"]["recall"] + 1.5,
               f"{100 * r['detection']['recall']:.0f}", ha="center",
               color=BLEU, fontweight="bold", fontsize=10)
        a.text(i + w / 2, 100 * r["detection"]["precision"] + 1.5,
               f"{100 * r['detection']['precision']:.0f}", ha="center",
               color=VERT, fontweight="bold", fontsize=10)
    a.set_xticks(x); a.set_xticklabels(names)
    a.set_ylabel("pourcentage"); a.set_ylim(0, 122)
    a.set_title("Ce qui est retrouve, ce qui est juste")
    a.legend(frameon=False, loc="upper center", ncol=2,
             bbox_to_anchor=(0.5, 1.02))
    a.grid(axis="y", alpha=.7, zorder=0); a.set_axisbelow(True)

    ratios = [r["detection"]["ratio"] for r in rows]
    b.barh(x, ratios, .5, color=[LAITON if abs(v - 1) < .15 else ROUGE
                                 for v in ratios], zorder=3)
    b.set_ylim(-.6, len(names) - .1)
    b.axvline(1.0, color=ENCRE, ls="--", lw=1.6, zorder=4)
    b.text(1.03, len(names) - .2, "la partition", color=ENCRE,
           fontweight="bold", fontsize=10, va="top")
    for i, v in enumerate(ratios):
        b.text(v - .03, i, f"{v:.2f}x", va="center", ha="right", fontsize=10.5,
               fontweight="bold", color="white")
    b.set_yticks(x); b.set_yticklabels(names)
    b.set_xlim(0, max(1.35, max(ratios) * 1.25))
    b.set_xlabel("notes detectees / notes de la partition")
    b.set_title("Le bon nombre de notes")
    b.grid(axis="x", alpha=.7, zorder=0); b.set_axisbelow(True)
    fig.tight_layout()
    save(fig, "1_detection.png")

    # 2. timing
    fig, ax = plt.subplots(figsize=(9.5, 1.0 * len(rows) + 2.2))
    med = [r["timing"]["median"] or 0 for r in rows]
    p90 = [r["timing"]["p90"] or 0 for r in rows]
    for i, (m, p) in enumerate(zip(med, p90)):
        ax.plot([m, p], [i, i], color="#D6DAE1", lw=3, solid_capstyle="round",
                zorder=2)
    ax.plot(med, x, "o", ms=12, color=VERT, markeredgecolor=FOND, mew=2,
            zorder=3, label="mediane")
    ax.plot(p90, x, "o", ms=12, color=LAITON, markeredgecolor=FOND, mew=2,
            zorder=3, label="90e centile")
    for i, (m, p) in enumerate(zip(med, p90)):
        ax.text(m, i + .28, f"{m:.0f}", ha="center", color=VERT,
                fontweight="bold", fontsize=10)
        ax.text(p, i + .28, f"{p:.0f}", ha="center", color=LAITON,
                fontweight="bold", fontsize=10)
    ax.axvline(46, color=ACIER, ls=":", lw=1.5)
    ax.text(47, -.62, "un saut de STFT (46 ms)", color=MUET, fontsize=9.5)
    ax.set_yticks(x); ax.set_yticklabels(names)
    ax.set_xlabel("erreur d'attaque (ms)"); ax.set_xlim(left=0)
    ax.set_ylim(-.8, len(names) - .3)
    ax.set_title("A quel point les attaques tombent juste")
    ax.legend(frameon=False, loc="lower right")
    ax.grid(axis="x", alpha=.7, zorder=0); ax.set_axisbelow(True)
    fig.tight_layout()
    save(fig, "2_timing.png")

    # 3. fausses notes par relation harmonique
    #
    # En PARTS et non en effectifs : l'Ecossaise en compte dix fois plus que
    # la Gamme, et un empilement en valeur absolue ecraserait les petits
    # morceaux jusqu'a l'illisible. Le total est annote au-dessus.
    fig, ax = plt.subplots(figsize=(2.1 * len(rows) + 4.5, 4.6))
    groups = [("octave", ("octave +12", "octave -12",
                          "double octave +24", "double octave -24"), LAITON),
              ("quinte / douzieme", ("douzieme +19", "douzieme -19",
                                     "quinte +7", "quinte -7"), BLEU),
              ("sans relation", ("sans relation",), ACIER)]
    bottom = np.zeros(len(rows))
    totals = np.array([max(1, r["ghosts"]["total"]) for r in rows], dtype=float)
    for label, keys, color in groups:
        values = np.array([sum(r["ghosts"]["by_relation"].get(k, 0)
                               for k in keys) for r in rows], dtype=float)
        share = 100 * values / totals
        ax.bar(x, share, .5, bottom=bottom, color=color, label=label,
               zorder=3, edgecolor=FOND, linewidth=2)
        for i, (v, sh) in enumerate(zip(values, share)):
            if sh > 7:
                ax.text(i, bottom[i] + sh / 2, f"{sh:.0f} %", ha="center",
                        va="center", color="white", fontweight="bold",
                        fontsize=10.5)
        bottom += share
    for i, r in enumerate(rows):
        ax.text(i, 102, f"{r['ghosts']['total']} fausses notes", ha="center",
                color=ENCRE, fontweight="bold", fontsize=10)
    ax.set_xticks(x); ax.set_xticklabels(names)
    ax.set_ylabel("part des fausses notes (%)"); ax.set_ylim(0, 118)
    ax.set_title("D'ou viennent les fausses notes")
    ax.legend(frameon=False, loc="upper center", ncol=3,
              bbox_to_anchor=(0.5, -0.08))
    ax.grid(axis="y", alpha=.7, zorder=0); ax.set_axisbelow(True)
    fig.tight_layout()
    save(fig, "3_fantomes.png")

    # 4. instruments
    fig, ax = plt.subplots(figsize=(1.9 * len(rows) + 4.5, 4.6))
    w = 0.26
    ax.bar(x - w, [100 * r["instruments"]["piano"] for r in rows], w,
           color=LAITON, label="piano", zorder=3)
    ax.bar(x, [100 * r["instruments"]["trumpet"] for r in rows], w,
           color=BLEU, label="trompette", zorder=3)
    ax.bar(x + w, [100 * r["instruments"]["balanced"] for r in rows], w,
           color=VERT, label="equilibree", zorder=3)
    ax.axhline(50, color=ROUGE, ls="--", lw=1.5, zorder=4)
    ax.text(-.45, 52, "pile ou face", color=ROUGE,
            fontweight="bold", fontsize=10, ha="left")
    ax.set_xticks(x); ax.set_xticklabels(names)
    ax.set_ylabel("justesse (%)"); ax.set_ylim(0, 125)
    ax.set_title("Piano ou trompette : justesse des trois tests de timbre")
    ax.legend(frameon=False, loc="upper center", ncol=3,
              bbox_to_anchor=(0.5, 1.02))
    ax.grid(axis="y", alpha=.7, zorder=0); ax.set_axisbelow(True)
    fig.tight_layout()
    save(fig, "4_instruments.png")

    # 5. entonnoir, un petit multiple par morceau
    n = len(rows)
    fig, axes = plt.subplots(1, n, figsize=(3.0 * n, 4.0), sharey=False)
    axes = np.atleast_1d(axes)
    for ax, r in zip(axes, rows):
        labels = [s["stage"] for s in r["stages"]]
        values = [s["notes"] for s in r["stages"]]
        ax.barh(np.arange(len(values))[::-1], values, .55, color=LAITON,
                zorder=3)
        ax.axvline(r["detection"]["reference"], color=ENCRE, ls="--", lw=1.5,
                   zorder=4)
        for i, v in enumerate(values):
            ax.text(v * 1.03, len(values) - 1 - i, str(v), va="center",
                    fontsize=9, color=ENCRE)
        ax.set_yticks(np.arange(len(values))[::-1])
        ax.set_yticklabels(labels, fontsize=9.5)
        ax.set_xlim(0, max(max(values), r["detection"]["reference"]) * 1.30)
        ax.set_title(r["name"], fontsize=12)
        ax.grid(axis="x", alpha=.7, zorder=0); ax.set_axisbelow(True)
    axes[0].set_xlabel("notes")
    fig.suptitle("L'entonnoir : ce que chaque etape laisse passer\n"
                 "le trait vertical est le nombre de notes de la partition",
                 fontsize=13.5, fontweight="bold", y=1.06)
    fig.tight_layout()
    save(fig, "5_entonnoir.png")

    # 6. cout par etape
    fig, ax = plt.subplots(figsize=(2.1 * len(rows) + 4.5, 4.8))
    labels = [s["stage"] for s in rows[0]["stages"]]
    colors = [LAITON, BLEU, VERT, ROUGE, ACIER, "#7A5C9E", "#3F7F7A"]
    bottom = np.zeros(len(rows))
    for k, label in enumerate(labels):
        values = np.array([next((s["seconds"] for s in r["stages"]
                                 if s["stage"] == label), 0.0) for r in rows])
        ax.bar(x, values, .55, bottom=bottom, color=colors[k % len(colors)],
               label=label, zorder=3, edgecolor=FOND, linewidth=1.5)
        bottom += values
    for i, r in enumerate(rows):
        ax.text(i, bottom[i] + max(bottom) * .03,
                f"{r['realtime']:.1f}x temps reel", ha="center",
                color=ENCRE, fontweight="bold", fontsize=10)
    ax.set_xticks(x); ax.set_xticklabels(names)
    ax.set_ylim(0, max(bottom) * 1.16)
    ax.set_ylabel("secondes de calcul")
    ax.set_title("Ou passe le temps de transcription")
    ax.legend(frameon=False, ncol=4, fontsize=10, loc="upper center",
              bbox_to_anchor=(0.5, -0.08))
    ax.grid(axis="y", alpha=.7, zorder=0); ax.set_axisbelow(True)
    fig.tight_layout()
    save(fig, "6_cout.png")

    # 7. le score fusionne, morceau par morceau
    #
    # Histogramme en miroir : le piano au-dessus de l'axe, la trompette en
    # dessous. Superposes avec de la transparence, les deux couleurs en
    # produiraient une troisieme, qui ne veut rien dire. Chaque cote est
    # normalise a une surface de 1, sinon la classe majoritaire ecrase
    # l'autre.
    import config
    usable = [r for r in rows if r.get("descriptors")]
    if usable:
        n = len(usable)
        fig, axes = plt.subplots(n, 1, figsize=(10.5, 1.9 * n + 0.8),
                                 sharex=True)
        axes = np.atleast_1d(axes)
        bins = np.linspace(-1, 1, 34)
        for ax, r in zip(axes, usable):
            piano, trumpet = split(r["descriptors"], 4)
            hp, _ = np.histogram(piano, bins=bins)
            ht, _ = np.histogram(trumpet, bins=bins)
            hp = hp / max(1, hp.sum()); ht = ht / max(1, ht.sum())
            centres = (bins[:-1] + bins[1:]) / 2
            width = (bins[1] - bins[0]) * .92
            ax.bar(centres, hp, width, color=LAITON, zorder=3)
            ax.bar(centres, -ht, width, color=BLEU, zorder=3)
            top = max(hp.max(), ht.max(), 1e-6) * 1.7
            ax.axhline(0, color="#CFD4DC", lw=1)
            ax.axvline(config.FUSION_THRESHOLD, color=ENCRE, ls="--", lw=1.7,
                       zorder=4)
            ax.text(-.97, top * .82, f"piano ({len(piano)})", color=LAITON,
                    fontweight="bold", fontsize=10.5, va="center")
            ax.text(-.97, -top * .86, f"trompette ({len(trumpet)})",
                    color=BLEU, fontweight="bold", fontsize=10.5, va="center")
            ax.text(.97, top * .82,
                    f"{100 * r['instruments']['balanced']:.0f} % justes",
                    color=ENCRE, fontweight="bold", fontsize=10.5, ha="right",
                    va="center")
            ax.set_title(r["name"], loc="left", fontsize=12)
            ax.set_ylim(-top, top); ax.set_yticks([])
            ax.set_xlim(-1, 1)
            ax.grid(axis="x", alpha=.6, zorder=0); ax.set_axisbelow(True)
            ax.spines["left"].set_visible(False)
        axes[-1].set_xlabel("score fusionne   "
                            "(-1 = piano certain, +1 = trompette certaine)  ;  "
                            f"seuil {config.FUSION_THRESHOLD}")
        fig.suptitle("Ce que voient les trois tests de timbre",
                     fontsize=14, fontweight="bold", y=1.005)
        fig.tight_layout(h_pad=1.8)
        save(fig, "7_timbre.png")

    for path in written:
        print("ecrit :", path)
    return written


# --- calibration des seuils ---------------------------------------------

TESTS = ("sustain", "flatness", "rolloff")
COLUMN = {"sustain": 1, "flatness": 2, "rolloff": 3}


def best_threshold(piano, trumpet):
    """Le seuil qui maximise la moyenne des deux justesses par classe.

    On maximise la justesse EQUILIBREE et non la justesse globale : les
    classes sont tres inegales (sur l'Ecossaise, 522 notes de piano contre
    225 de trompette) et un seuil optimise globalement se contenterait de
    tout appeler piano.
    """
    if len(piano) < 5 or len(trumpet) < 5:
        return None, 0.0
    piano, trumpet = np.array(piano), np.array(trumpet)
    best = (0.0, None)
    for s in np.sort(np.concatenate([piano, trumpet])):
        score = ((piano < s).mean() + (trumpet >= s).mean()) / 2
        if score > best[0]:
            best = (score, float(s))
    return best[1], best[0]


def accuracy_at(piano, trumpet, threshold):
    if not piano or not trumpet:
        return 0.0
    piano, trumpet = np.array(piano), np.array(trumpet)
    return ((piano < threshold).mean() + (trumpet >= threshold).mean()) / 2


def split(rows, column):
    "Les valeurs d'un descripteur, separees par la classe de la partition."
    piano = [r[column] for r in rows if r[0] == "piano" and r[column] is not None]
    trumpet = [r[column] for r in rows if r[0] == "trumpet" and r[column] is not None]
    return piano, trumpet


def calibrate(results=None):
    """Les seuils que chaque morceau donnerait, contre ceux de config.py.

    C'est la mesure qui dit si les seuils calibres sur l'Ecossaise valent
    pour les autres morceaux, ou si le classifieur est reste colle a son
    morceau de calibration.
    """
    import config

    results = results or load()
    current = {"sustain": config.SUSTAIN_THRESHOLD,
               "flatness": config.FLATNESS_THRESHOLD,
               "rolloff": config.ROLLOFF_THRESHOLD}

    pooled = [r for res in results.values() for r in res.get("descriptors", [])]
    blocks = list(results.items()) + [("TOUS", {"descriptors": pooled})]

    print(f"\nSEUILS  (seuil actuel de config.py entre parentheses)")
    print(f"{'morceau':14s} {'test':10s} {'mesurees':>9s} {'seuil ideal':>12s} "
          f"{'justesse':>9s} {'seuil actuel':>13s} {'justesse':>9s}")
    for name, res in blocks:
        rows = res.get("descriptors", [])
        if not rows:
            continue
        for test in TESTS:
            piano, trumpet = split(rows, COLUMN[test])
            ideal, best = best_threshold(piano, trumpet)
            here = accuracy_at(piano, trumpet, current[test])
            if ideal is None:
                print(f"{name:14s} {test:10s} {len(piano) + len(trumpet):9d} "
                      f"{'trop peu de notes mesurables':>36s}")
                continue
            print(f"{name:14s} {test:10s} {len(piano) + len(trumpet):9d} "
                  f"{ideal:12.4f} {100 * best:8.0f}% "
                  f"{current[test]:13.4f} {100 * here:8.0f}%")
        print()

    print("SCORE FUSIONNE")
    print(f"{'morceau':14s} {'notes':>7s} {'seuil ideal':>12s} {'justesse':>9s} "
          f"{'seuil actuel':>13s} {'justesse':>9s}")
    for name, res in blocks:
        rows = res.get("descriptors", [])
        piano, trumpet = split(rows, 4)
        if len(piano) < 5 or len(trumpet) < 5:
            continue
        ideal, best = best_threshold(piano, trumpet)
        here = accuracy_at(piano, trumpet, config.FUSION_THRESHOLD)
        print(f"{name:14s} {len(piano) + len(trumpet):7d} {ideal:12.4f} "
              f"{100 * best:8.0f}% {config.FUSION_THRESHOLD:13.4f} "
              f"{100 * here:8.0f}%")
    print()


# --- rapport HTML -------------------------------------------------------

def html(results=None):
    """Une page autonome : les tableaux et les figures au meme endroit.

    Les images sont incrustees en base64, donc le fichier se deplace seul
    -- pratique pour l'ouvrir depuis une cle ou l'envoyer.
    """
    import base64

    results = results or load()
    rows = list(results.values())
    figures = sorted(BENCH.glob("*.png"))

    def table(head, body):
        cells = "".join(f"<th>{h}</th>" for h in head)
        lines = "".join("<tr>" + "".join(f"<td>{c}</td>" for c in r) + "</tr>"
                        for r in body)
        return f"<table><thead><tr>{cells}</tr></thead><tbody>{lines}</tbody></table>"

    detection = table(
        ["morceau", "reference", "detecte", "rapport", "rappel", "precision", "F1"],
        [[r["name"], r["detection"]["reference"], r["detection"]["detected"],
          f"{r['detection']['ratio']:.2f}x",
          f"{100 * r['detection']['recall']:.0f} %",
          f"{100 * r['detection']['precision']:.0f} %",
          f"{100 * r['detection']['f1']:.1f}"] for r in rows])

    quality = table(
        ["morceau", "attaque mediane", "90e centile", "fausses notes",
         "dont harmoniques", "instrument (equilibre)", "x temps reel"],
        [[r["name"],
          f"{r['timing']['median']:.0f} ms" if r["timing"]["median"] else "-",
          f"{r['timing']['p90']:.0f} ms" if r["timing"]["p90"] else "-",
          r["ghosts"]["total"],
          f"{100 * r['ghosts']['share']:.0f} %",
          f"{100 * r['instruments']['balanced']:.0f} %",
          f"{r['realtime']:.2f}x"] for r in rows])

    images = ""
    for path in figures:
        data = base64.b64encode(path.read_bytes()).decode()
        images += (f'<figure><img alt="{path.stem}" '
                   f'src="data:image/png;base64,{data}"></figure>')

    notes = "".join(f"<li><b>{r['name']}</b> — {r['note']}</li>" for r in rows)

    page = f"""<!doctype html><html lang="fr"><head><meta charset="utf-8">
<title>Banc de mesure — transcription</title><style>
:root{{--ink:#1C1E24;--muted:#5F6470;--rule:#E2DED5;--bg:#FCFCFB;--brass:#B07D14}}
*{{box-sizing:border-box}}
body{{margin:0;background:var(--bg);color:var(--ink);
 font:16px/1.6 "DejaVu Sans",system-ui,sans-serif;padding:40px 24px 80px}}
.wrap{{max-width:1100px;margin:0 auto}}
h1{{font-size:34px;margin:0 0 6px;letter-spacing:-.02em}}
h2{{font-size:20px;margin:44px 0 12px;letter-spacing:-.01em}}
p.sub{{color:var(--muted);margin:0 0 8px}}
table{{border-collapse:collapse;width:100%;font-size:14.5px;margin:8px 0 4px}}
th,td{{text-align:left;padding:8px 12px 8px 0;border-bottom:1px solid var(--rule)}}
th{{font-size:12px;text-transform:uppercase;letter-spacing:.06em;
 color:var(--muted);font-weight:600}}
td:not(:first-child){{font-variant-numeric:tabular-nums}}
figure{{margin:22px 0}}img{{width:100%;height:auto;border:1px solid var(--rule);
 border-radius:3px;background:#fff}}
ul{{color:var(--muted);font-size:14.5px}}
footer{{margin-top:50px;padding-top:18px;border-top:1px solid var(--rule);
 color:var(--muted);font-size:13px}}
</style></head><body><div class="wrap">
<h1>Banc de mesure</h1>
<p class="sub">Transcription MP3 → MIDI, mesuree contre la partition de
chaque morceau. {len(rows)} morceaux, tolerance d'appariement {int(1000 * TOLERANCE)} ms.</p>
<h2>Detection</h2>{detection}
<h2>Qualite et cout</h2>{quality}
<h2>Figures</h2>{images}
<h2>Le corpus</h2><ul>{notes}</ul>
<footer>Genere par <code>python benchmark.py html</code> depuis
<code>bench/results.json</code>.</footer>
</div></body></html>"""

    BENCH.mkdir(exist_ok=True)
    path = BENCH / "rapport.html"
    path.write_text(page, encoding="utf-8")
    print("ecrit :", path)
    return path


# --- ligne de commande --------------------------------------------------

if __name__ == "__main__":
    mode = sys.argv[1] if len(sys.argv) > 1 else "report"
    args = sys.argv[2:]

    if mode == "run":
        report(run(args))
    elif mode == "report":
        report()
    elif mode == "charts":
        charts()
    elif mode == "html":
        html()
    elif mode == "calibrate":
        calibrate()
    elif mode == "all":
        results = run(args)
        report(results)
        charts(results)
        calibrate(results)
        html(results)
    elif mode == "list":
        for name in corpus.CORPUS:
            mark = " " if name in corpus.available() else "!"
            print(f"{mark} {name}")
    else:
        print(__doc__)
