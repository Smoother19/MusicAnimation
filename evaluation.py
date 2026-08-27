import sys

import numpy as np
import pretty_midi

from notes import transcribe
from instruments import measure, label

PIANO = "./sounds/PinkPanther_Piano_Only.mp3"
TRUMPET = "./sounds/PinkPanther_Trumpet_Only.mp3"
PIANO_REF = "./sounds/PinkPanther_Piano_Only_converted_by_jukeblocks.mid"


def evaluate(notes, reference_path, tolerance=0.15):
    """Compare detected notes against a reference MIDI.

    A note counts as found when its pitch is exact and its onset within
    `tolerance` seconds. Returns (recall, precision).

    The reference must match the same recording, duration included, or the
    numbers are meaningless.
    """
    ref = pretty_midi.PrettyMIDI(reference_path)
    expected = [(n.pitch, n.start) for inst in ref.instruments for n in inst.notes]
    obtained = [(n.midi, n.seconds()[0]) for n in notes]

    def matches(a, b):
        return a[0] == b[0] and abs(a[1] - b[1]) < tolerance

    found = sum(1 for e in expected if any(matches(e, o) for o in obtained))
    correct = sum(1 for o in obtained if any(matches(e, o) for e in expected))

    return found / len(expected), correct / len(obtained)


def best_threshold(piano_values, trumpet_values):
    """Threshold maximising the mean of both per-class accuracies.

    Balancing is essential here: the classes are very uneven (about 310
    piano notes against 62 trumpet ones) and a global accuracy would
    reward a rule that labels everything as piano.
    """
    best = (0.0, None)
    for s in sorted(piano_values + trumpet_values):
        rate_p = sum(1 for v in piano_values if v < s) / len(piano_values)
        rate_t = sum(1 for v in trumpet_values if v >= s) / len(trumpet_values)
        accuracy = (rate_p + rate_t) / 2
        if accuracy > best[0]:
            best = (accuracy, s)
    return best[1], best[0]


def describe(path):
    """Transcribe a file and measure every descriptor of its notes."""
    y, notes = transcribe(path)
    return measure(y, notes)


def _values(notes, field):
    return [getattr(n, field) for n in notes if getattr(n, field) is not None]


def calibrate(plot=True):
    """Compare descriptors between the piano-only and trumpet-only tracks."""
    piano = label(describe(PIANO))
    trumpet = label(describe(TRUMPET))

    rate_p = sum(1 for n in piano if n.instrument == "piano") / len(piano)
    rate_t = sum(1 for n in trumpet if n.instrument == "trumpet") / len(trumpet)
    print(f"piano    : {100 * rate_p:.0f}%")
    print(f"trumpet  : {100 * rate_t:.0f}%")
    print(f"balanced : {50 * (rate_p + rate_t):.0f}%\n")

    results = {}
    for field in ("slope", "vibrato"):
        vp, vt = _values(piano, field), _values(trumpet, field)
        threshold, accuracy = best_threshold(vp, vt)
        results[field] = (vp, vt, threshold, accuracy)
        print(f"{field:8s} piano {len(vp):3d} notes med {np.median(vp):+.4f} | "
              f"trumpet {len(vt):3d} notes med {np.median(vt):+.4f} | "
              f"threshold {threshold:+.4f} -> {100 * accuracy:.0f}%")

    if plot:
        import matplotlib.pyplot as plt
        _, axes = plt.subplots(1, 2, figsize=(12, 4))
        for ax, field in zip(axes, ("slope", "vibrato")):
            vp, vt, threshold, _ = results[field]
            ax.hist(vp, bins=30, alpha=0.6, density=True, label="piano")
            ax.hist(vt, bins=30, alpha=0.6, density=True, label="trumpet")
            ax.axvline(threshold, color="k", ls="--")
            ax.set_xlabel(field)
            ax.legend()
        plt.tight_layout()
        plt.show()

    return results


if __name__ == "__main__":
    mode = sys.argv[1] if len(sys.argv) > 1 else "transcription"

    if mode == "transcription":
        _, notes = transcribe(PIANO)
        print(f"{len(notes)} notes detected")
        recall, precision = evaluate(notes, PIANO_REF)
        print(f"recall    : {100 * recall:.0f}%")
        print(f"precision : {100 * precision:.0f}%")
    elif mode == "calibration":
        calibrate()
    else:
        print(__doc__)