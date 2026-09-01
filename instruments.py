import numpy as np

from config import (SR, N_FFT, HOP, N_ENV, HOP_ENV, BIN_ENV,
                    SUSTAIN_THRESHOLD, FLATNESS_THRESHOLD, ROLLOFF_THRESHOLD,
                    TEST_WEIGHTS, TEST_SPREAD, FUSION_THRESHOLD)

TESTS = ("sustain", "flatness", "rolloff")

THRESHOLDS = {"sustain": SUSTAIN_THRESHOLD,
              "flatness": FLATNESS_THRESHOLD,
              "rolloff": ROLLOFF_THRESHOLD}


# --- Envelope -----------------------------------------------------------

def envelope(y, f0, start, end):
    """Amplitude of a note over time, summed over its first six partials."""
    i0 = start * HOP
    i1 = min(end * HOP + N_FFT, len(y) - N_ENV)
    amp = []

    for i in range(i0, i1, HOP_ENV):
        mag = np.abs(np.fft.rfft(y[i:i + N_ENV] * np.hanning(N_ENV)))
        total = 0.0
        for n in range(1, 7):
            fn = n * f0
            if fn > SR / 2 - 50:
                break
            tol = max(2 * BIN_ENV, 0.01 * fn)
            lo, hi = int((fn - tol) / BIN_ENV), int((fn + tol) / BIN_ENV) + 1
            if lo < hi <= len(mag):
                total += mag[lo:hi].max()
        amp.append(total)

    return np.array(amp)


# --- Measurement --------------------------------------------------------

def measure(y, notes, harmonics=None):
    from harmonics import descriptors

    for i, note in enumerate(notes):
        entry = harmonics[i] if harmonics is not None else None
        values = descriptors(entry, note)
        note.sustain = values["sustain"]
        note.flatness = values["flatness"]
        note.rolloff = values["rolloff"]
    return notes


# --- Fusion -------------------------------------------------------------

def score(note):
    total, weight = 0.0, 0.0
    for name in TESTS:
        value = getattr(note, name, None)
        if value is None:
            continue
        w = TEST_WEIGHTS[name]
        total += w * np.tanh((value - THRESHOLDS[name]) / TEST_SPREAD[name])
        weight += w

    return float(total / weight) if weight else 0.0


def label(notes):
    for note in notes:
        note.score = score(note)
        note.instrument = "trumpet" if note.score > FUSION_THRESHOLD else "piano"
    return notes


def enforce_monophony(notes, margin=0.30):
    """A trumpet plays one note at a time.

    Between two overlapping trumpet notes only the higher-scoring one
    keeps the label, and only when the gap between the two scores is
    wide enough to mean something: applied to every overlap regardless,
    this rule strips the label off four trumpet notes out of five, since
    in this piece the piano plays right across the trumpet register.
    """
    ordered = sorted(notes, key=lambda n: n.seconds()[0])
    for i, note in enumerate(ordered):
        if note.instrument != "trumpet":
            continue
        _, end = note.seconds()
        for other in ordered[i + 1:]:
            o_start, _ = other.seconds()
            if o_start >= end:
                break
            if other.instrument == "trumpet" and other.score - note.score > margin:
                note.instrument = "piano"
                break
    return notes
