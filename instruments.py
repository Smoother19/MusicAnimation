import numpy as np

from config import (SR, N_FFT, HOP, N_ENV, HOP_ENV, BIN_ENV, FS_ENV,
                    VIBRATO_THRESHOLD, TRANSITION_WIDTH, LOW_PITCH_LIMIT,
                    SCORE_NO_VIBRATO)


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


def _split_reattacks(amp, ratio=1.3, margin=15):
    """Cut the envelope wherever amplitude jumps back up.

    A key struck several times in a row ends up in one note segment;
    without this split the average slope is near zero for both
    instruments.
    """
    cuts = [0]
    for i in range(margin, len(amp) - margin):
        before = amp[i - margin:i].mean()
        after = amp[i:i + margin].mean()
        if before > 1e-9 and after / before > ratio and i - cuts[-1] > margin * 2:
            cuts.append(i)
    cuts.append(len(amp))
    return [amp[a:b] for a, b in zip(cuts, cuts[1:])]


def slope(amp, skip=8):
    """Median log-amplitude slope. Negative means free decay.

    Returns None when no segment is long enough for a reliable fit.
    """
    values = []
    for block in _split_reattacks(amp):
        if len(block) < skip + 20:
            continue
        a = block[skip:]
        a = a[a > 0]
        if len(a) < 20:
            continue
        values.append(float(np.polyfit(np.arange(len(a)), np.log(a), 1)[0]))
    return float(np.median(values)) if values else None


# --- Vibrato ------------------------------------------------------------

def f0_track(y, f0, start, end):
    """Track the fundamental frequency across the note.

    The peak is refined by parabolic interpolation, for sub-bin accuracy.
    """
    i0 = start * HOP
    i1 = min(end * HOP + N_FFT, len(y) - N_ENV)
    track = []

    for i in range(i0, i1, HOP_ENV):
        mag = np.abs(np.fft.rfft(y[i:i + N_ENV] * np.hanning(N_ENV)))
        lo = int(f0 * 0.94 / BIN_ENV)
        hi = int(f0 * 1.06 / BIN_ENV) + 1
        if hi >= len(mag) or hi <= lo + 1:
            return None

        k = lo + int(np.argmax(mag[lo:hi]))
        if 0 < k < len(mag) - 1:
            a, b, c = mag[k - 1], mag[k], mag[k + 1]
            denom = a - 2 * b + c
            offset = 0.5 * (a - c) / denom if abs(denom) > 1e-9 else 0.0
        else:
            offset = 0.0
        track.append((k + offset) * BIN_ENV)

    return np.array(track) if len(track) > 20 else None


def vibrato(track, fs=FS_ENV):
    """Share of the pitch modulation energy falling in the 4-8 Hz band."""
    if track is None or len(track) < 40:
        return None
    track = track[track > 0]
    if len(track) < 40:
        return None

    cents = 1200 * np.log2(track / np.median(track))
    x = np.arange(len(cents))
    cents = cents - np.polyval(np.polyfit(x, cents, 1), x)

    spec = np.abs(np.fft.rfft(cents * np.hanning(len(cents))))
    freqs = np.fft.rfftfreq(len(cents), 1 / fs)

    total = spec[freqs > 0.5].sum()
    if total <= 1e-9:
        return None
    return float(spec[(freqs >= 4) & (freqs <= 8)].sum() / total)


# --- Classification -----------------------------------------------------

def measure(y, notes):
    """Fill in the descriptors of every note, in place."""
    for note in notes:
        note.slope = slope(envelope(y, note.f0, note.start, note.end))
        note.vibrato = vibrato(f0_track(y, note.f0, note.start, note.end))
    return notes


def score(note):
    """Score in [-1, +1]: -1 is certainly piano, +1 certainly trumpet."""
    if note.midi < LOW_PITCH_LIMIT:
        return -1.0
    if note.vibrato is None:
        return SCORE_NO_VIBRATO
    return float(np.tanh((note.vibrato - VIBRATO_THRESHOLD) / TRANSITION_WIDTH))


def label(notes):
    for note in notes:
        note.instrument = "trumpet" if score(note) > 0 else "piano"
    return notes


def enforce_monophony(notes):
    """A trumpet plays one note at a time.

    Between two overlapping trumpet notes, only the higher-scoring one
    keeps the label.
    """
    for note in notes:
        if note.instrument != "trumpet":
            continue
        for other in notes:
            if other is note or other.instrument != "trumpet":
                continue
            if note.start < other.end and other.start < note.end:
                if score(other) > score(note):
                    note.instrument = "piano"
                    break
    return notes