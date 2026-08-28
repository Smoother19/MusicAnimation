"""Multi-pitch engine: harmonic salience with iterative cancellation.

No learning involved. Harmonic combs are built analytically and polyphony
is extracted by subtracting them one at a time from the residual spectrum.
"""

import numpy as np

from config import (SR, N_FFT, BIN, N_PARTIALS, ALPHA, BETA,
                    MAX_NOTES, SALIENCE_THRESHOLD, CANCEL_FACTOR)


def _build_grid(midi_min=21, midi_max=108, step=1 / 3):
    """Candidate pitches, one third of a semitone apart."""
    midi = np.arange(midi_min, midi_max + step, step)
    return 440.0 * 2 ** ((midi - 69) / 12)


GRID = _build_grid()


def _band(mag, f, rank=1):
    """Spectrum indices around f.

    Tolerance widens with the partial rank, to follow the upward drift
    caused by string stiffness.
    """
    tol = max(2 * BIN, 0.003 * rank * f)
    lo = max(int((f - tol) / BIN), 0)
    hi = min(int((f + tol) / BIN) + 1, len(mag))
    return lo, hi


def salience(mag, f0):
    """Weighted sum of the partials of f0 found in the spectrum."""
    total = 0.0
    for n in range(1, N_PARTIALS + 1):
        fn = n * f0
        if fn > SR / 2 - 50:
            break
        lo, hi = _band(mag, fn, n)
        if hi <= lo:
            continue
        total += (f0 + ALPHA) / (fn + BETA) * mag[lo:hi].max()
    return total


def salience_map(mag):
    return np.array([salience(mag, f0) for f0 in GRID])


def cancel(mag, f0, factor=CANCEL_FACTOR):
    """Remove the comb of f0 and return the residual.

    Deliberately partial: partials shared with other notes must survive
    for those notes to remain detectable.
    """
    res = mag.copy()
    for n in range(1, N_PARTIALS + 1):
        fn = n * f0
        if fn > SR / 2 - 50:
            break
        lo, hi = _band(res, fn, n)
        if hi > lo:
            res[lo:hi] *= (1 - factor)
    return res


def _too_close(f, found, semitones=0.75):
    return any(abs(12 * np.log2(f / g)) < semitones for g in found)


def detect(mag, max_notes=MAX_NOTES, threshold=SALIENCE_THRESHOLD):
    """Pitches present in a spectrum, in Hz, most salient first."""
    res = mag.copy()
    found, reference = [], None

    for _ in range(max_notes * 3):
        if len(found) >= max_notes:
            break

        sal = salience_map(res)
        i = int(np.argmax(sal))

        if reference is None:
            reference = sal[i]
        elif sal[i] < threshold * reference:
            break

        f = float(GRID[i])
        if not _too_close(f, found):
            found.append(round(f, 1))
        res = cancel(res, f)

    return found


# --- Test bench ---------------------------------------------------------

def comb(f0, duration=1.0, n_partials=12, stiffness=0.0):
    """Synthetic tone. stiffness = 0 for a pipe, > 0 for a string."""
    t = np.arange(int(duration * SR)) / SR
    y = np.zeros_like(t)
    for n in range(1, n_partials + 1):
        fn = n * f0 * np.sqrt(1 + stiffness * n**2)
        if fn > SR / 2:
            break
        y += (1 / n**0.8) * np.sin(2 * np.pi * fn * t)
    return y / np.max(np.abs(y))


def spectrum(y):
    seg = y[:N_FFT]
    if len(seg) < N_FFT:
        seg = np.pad(seg, (0, N_FFT - len(seg)))
    return np.abs(np.fft.rfft(seg * np.hanning(N_FFT)))


if __name__ == "__main__":
    cases = {
        "trumpet 440": comb(440),
        "piano 220": comb(220, stiffness=3e-4),
        "mix": 0.6 * comb(440) + 0.4 * comb(220, stiffness=3e-4),
    }
    for name, signal in cases.items():
        print(f"{name:14s} -> {detect(spectrum(signal))}")