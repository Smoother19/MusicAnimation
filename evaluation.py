"""Measuring the pipeline against a reference score.

Two modes:
    python evaluation.py transcription   note detection, stage by stage
    python evaluation.py calibration     thresholds of the three tests
"""

import sys

import numpy as np
import pretty_midi

MIX = "./sounds/Ecossaise_Both.mp3"
PIANO = "./sounds/Ecossaise_Piano.mp3"
TRUMPET = "./sounds/Ecossaise_Trumpet.mp3"
REFERENCE = "./sounds/Ecossaise_Beethoven.midi"
MELODY_TRACK = "Flute"          # the melody of the reference, played by the trumpet


def reference_notes(path=REFERENCE, min_duration=0.02):
    """(instrument, pitch, start, end) of every note of the reference."""
    midi = pretty_midi.PrettyMIDI(path)
    out = []
    for track in midi.instruments:
        name = "trumpet" if track.name == MELODY_TRACK else "piano"
        for note in track.notes:
            if note.end - note.start > min_duration:
                out.append((name, note.pitch, note.start, note.end))
    return out


def evaluate(notes, reference=None, tolerance=0.15):
    """Compare detected notes against a reference.

    A note counts as found when its pitch is exact and its onset within
    `tolerance` seconds. Returns (recall, precision, f1, count ratio).

    The count ratio matters as much as the rest here: the animation is
    driven by note events, so detecting twice too many is as wrong as
    detecting half of them.
    """
    reference = reference_notes() if reference is None else reference
    expected = [(pitch, start) for _, pitch, start, _ in reference]
    obtained = [(n.midi, n.seconds()[0]) for n in notes]

    def matches(a, b):
        return a[0] == b[0] and abs(a[1] - b[1]) < tolerance

    found = sum(1 for e in expected if any(matches(e, o) for o in obtained))
    correct = sum(1 for o in obtained if any(matches(e, o) for e in expected))

    recall = found / len(expected)
    precision = correct / max(1, len(obtained))
    f1 = 2 * recall * precision / (recall + precision + 1e-9)
    return recall, precision, f1, len(obtained) / len(expected)


def classification(notes, reference=None, tolerance=0.15):
    """Balanced accuracy of the instrument labels, on matched notes only.

    Balancing is essential: the classes are very uneven (about 480 piano
    notes against 180 trumpet ones) and a global accuracy would reward a
    rule that labels everything as piano.
    """
    reference = reference_notes() if reference is None else reference
    hits = {"piano": [0, 0], "trumpet": [0, 0]}

    for name, pitch, start, _ in reference:
        for note in notes:
            if note.midi == pitch and abs(note.seconds()[0] - start) < tolerance:
                hits[name][1] += 1
                hits[name][0] += int(note.instrument == name)
                break

    rates = {}
    for name, (ok, total) in hits.items():
        rates[name] = ok / total if total else 0.0
    return rates, hits


def best_threshold(piano_values, trumpet_values):
    """Threshold maximising the mean of both per-class accuracies."""
    if len(piano_values) < 5 or len(trumpet_values) < 5:
        return None, 0.0
    piano, trumpet = np.array(piano_values), np.array(trumpet_values)
    best = (0.0, None)
    for s in np.sort(np.concatenate([piano, trumpet])):
        accuracy = ((piano < s).mean() + (trumpet >= s).mean()) / 2
        if accuracy > best[0]:
            best = (accuracy, float(s))
    return best[1], best[0]


def describe(path, reference=None):
    """Descriptors of the reference notes, measured on `path`.

    The note positions come from the reference, so the calibration is not
    polluted by transcription errors.
    """
    import librosa
    from config import SR, HOP
    from notes import Note
    from harmonics import decompose
    from instruments import measure

    reference = reference_notes() if reference is None else reference
    y, _ = librosa.load(path, sr=SR, mono=True)

    labels, notes = [], []
    for name, pitch, start, end in reference:
        if end - start < 0.12:
            continue
        note = Note(midi=pitch, start=0, end=1)
        note.set_start(start)
        note.set_end(end)
        labels.append(name)
        notes.append(note)

    measure(y, notes, decompose(y, notes))
    return labels, notes


def detected(tolerance=0.15):
    """Notes as the pipeline really produces them, tagged by the reference.

    The only honest ground for calibration: the classifier will never see
    a note whose boundaries came from a score. Measured on reference
    spans instead, the sustain test reads 78% here and 53% in the
    pipeline -- the span itself was carrying the signal.
    """
    import librosa
    from config import SR
    from transcription import analyze
    from harmonics import decompose
    from instruments import measure

    reference = reference_notes()
    notes = analyze(MIX, classify=False)
    y, _ = librosa.load(MIX, sr=SR, mono=True)
    measure(y, notes, decompose(y, notes))

    labels = []
    for note in notes:
        start = note.seconds()[0]
        match = next((name for name, pitch, s, _ in reference
                      if pitch == note.midi and abs(s - start) < tolerance), None)
        labels.append(match)
    return labels, notes


def calibrate(source="pipeline"):
    """Thresholds of the three tests.

    `source="stems"` measures each instrument on its own recording, which
    says how separable the descriptors are at best. `source="mix"` uses
    the reference spans over the mix. `source="pipeline"` — the default —
    uses the notes the transcription actually found, which is the only
    set the classifier will ever be given. A threshold read off clean
    stems sits far too high once four other notes contribute to every
    partial: calibrating there is what made the previous version label
    98% of the trumpet as piano.
    """
    reference = reference_notes()
    piano_ref = [r for r in reference if r[0] == "piano"]
    trumpet_ref = [r for r in reference if r[0] == "trumpet"]

    if source == "stems":
        _, piano = describe(PIANO, piano_ref)
        _, trumpet = describe(TRUMPET, trumpet_ref)
    elif source == "mix":
        labels, notes = describe(MIX, reference)
        piano = [n for l, n in zip(labels, notes) if l == "piano"]
        trumpet = [n for l, n in zip(labels, notes) if l == "trumpet"]
    else:
        labels, notes = detected()
        piano = [n for l, n in zip(labels, notes) if l == "piano"]
        trumpet = [n for l, n in zip(labels, notes) if l == "trumpet"]

    print(f"{'test':10s} {'med piano':>10s} {'med trumpet':>12s} "
          f"{'threshold':>10s} {'accuracy':>9s}  measured")
    results = {}
    for field in ("sustain", "flatness", "rolloff"):
        vp = [getattr(n, field) for n in piano if getattr(n, field) is not None]
        vt = [getattr(n, field) for n in trumpet if getattr(n, field) is not None]
        threshold, accuracy = best_threshold(vp, vt)
        if threshold is None:
            print(f"{field:10s} not enough measurable notes")
            continue
        print(f"{field:10s} {np.median(vp):10.4f} {np.median(vt):12.4f} "
              f"{threshold:10.4f} {100 * accuracy:8.0f}%  "
              f"{len(vp)}/{len(piano)} vs {len(vt)}/{len(trumpet)}")
        results[field] = (threshold, float(np.std(vp + vt)))

    print("\ncopy into config.py:")
    for field, (threshold, spread) in results.items():
        print(f"  {field.upper()}_THRESHOLD = {threshold:.4f}"
              f"   # spread {spread:.4f}")
    return results


def _report(notes, label):
    recall, precision, f1, ratio = evaluate(notes)
    print(f"{label:26s} {len(notes):4d} notes ({ratio:.2f}x)  "
          f"recall {100 * recall:3.0f}%  precision {100 * precision:3.0f}%  "
          f"F1 {100 * f1:4.1f}")


if __name__ == "__main__":
    mode = sys.argv[1] if len(sys.argv) > 1 else "transcription"

    if mode == "transcription":
        from transcription import analyze
        reference = reference_notes()
        print(f"reference: {len(reference)} notes "
              f"({sum(1 for r in reference if r[0] == 'trumpet')} trumpet)\n")

        notes = analyze(MIX, classify=False, validate_notes=False,
                        refine_timing=False)
        _report(notes, "segmentation only")

        notes = analyze(MIX)
        _report(notes, "full pipeline")

        rates, hits = classification(notes)
        print(f"\ninstruments: piano {100 * rates['piano']:3.0f}% "
              f"({hits['piano'][0]}/{hits['piano'][1]})  "
              f"trumpet {100 * rates['trumpet']:3.0f}% "
              f"({hits['trumpet'][0]}/{hits['trumpet'][1]})  "
              f"balanced {50 * (rates['piano'] + rates['trumpet']):3.0f}%")

    elif mode == "calibration":
        source = sys.argv[2] if len(sys.argv) > 2 else "pipeline"
        print(f"measured on the {source}\n")
        calibrate(source)
    else:
        print(__doc__)
