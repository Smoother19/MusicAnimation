"""Harmonic decomposition of a polyphonic mix, by non-negative least squares.

At every frame the magnitude spectrum is modelled as a non-negative sum of
partial templates, one per (note, partial rank) of the notes active at that
instant. Solving the system attributes the energy of a shared bin to the
notes that dispute it, instead of crediting it in full to each of them.

Nothing is learned: the templates are the analytic main lobes of the
analysis window, placed at n*f0.
"""

import numpy as np
import librosa as lr
from scipy.optimize import nnls

from config import (SR, HARM_N_FFT, HARM_HOP, HARM_FMAX, HARM_PARTIALS,
                    HARM_LOBE, SUSTAIN_DELAY, midi_to_hz)

BIN_H = SR / HARM_N_FFT
FS_H = SR / HARM_HOP
K_MAX = int(HARM_FMAX / BIN_H)

_TEMPLATES = {}


def _templates(midi):
    """Columns of the model matrix for one pitch, one per partial rank.

    Each partial keeps its own amplitude: the timbre is never assumed.
    """
    if midi in _TEMPLATES:
        return _TEMPLATES[midi]

    f0 = midi_to_hz(midi)
    columns, ranks = [], []
    for n in range(1, HARM_PARTIALS + 1):
        centre = n * f0
        if centre > HARM_FMAX - 100:
            break
        k = centre / BIN_H
        column = np.zeros(K_MAX)
        for offset in range(-HARM_LOBE, HARM_LOBE + 1):
            bin_ = int(round(k)) + offset
            if 0 <= bin_ < K_MAX:
                column[bin_] = max(column[bin_],
                                   1.0 - abs(bin_ - k) / (HARM_LOBE + 1e-9))
        if column.sum() > 0:
            columns.append(column)
            ranks.append(n)

    _TEMPLATES[midi] = (np.array(columns).T if columns else None, ranks)
    return _TEMPLATES[midi]


def spectrogram(y):
    return np.abs(lr.stft(y, n_fft=HARM_N_FFT, hop_length=HARM_HOP))[:K_MAX]


def _active(notes, n_frames, tail=0.20):
    """Frames where each note sounds, plus the frame -> notes index."""
    spans, active = [], [[] for _ in range(n_frames)]
    for i, note in enumerate(notes):
        start, end = note.seconds()
        a = max(0, int(start * FS_H))
        b = min(n_frames, int((end + tail) * FS_H))
        spans.append((a, b))
        for t in range(a, b):
            active[t].append(i)
    return spans, active


def decompose(y, notes, residual_gain=False):
    """Partial amplitudes of every note, frame by frame.

    Returns a list, parallel to `notes`, of (ranks, amplitudes) where
    amplitudes has one row per partial rank and one column per frame of
    the note. When `residual_gain` is set, each note also gets the mean
    relative drop of the fitting residual it is responsible for: a note
    that explains nothing the others already explain scores near zero.
    """
    S = spectrogram(y)
    n_frames = S.shape[1]
    spans, active = _active(notes, n_frames)

    amplitudes = [{} for _ in notes]
    gains = [[] for _ in notes]

    for t in range(n_frames):
        ids = active[t]
        if not ids:
            continue

        blocks = [_templates(notes[i].midi) for i in ids]
        if any(matrix is None for matrix, _ in blocks):
            continue

        A = np.hstack([matrix for matrix, _ in blocks])
        b = S[:, t]
        x, residual = nnls(A, b)

        edges = np.cumsum([0] + [matrix.shape[1] for matrix, _ in blocks])
        for j, i in enumerate(ids):
            _, ranks = blocks[j]
            for rank, value in zip(ranks, x[edges[j]:edges[j + 1]]):
                amplitudes[i].setdefault(rank, {})[t] = float(value)

        if residual_gain:
            norm = np.linalg.norm(b) + 1e-9
            for j, i in enumerate(ids):
                keep = np.ones(A.shape[1], bool)
                keep[edges[j]:edges[j + 1]] = False
                _, without = nnls(A[:, keep], b)
                gains[i].append((without - residual) / norm)

    out = []
    for i, note in enumerate(notes):
        table = amplitudes[i]
        if not table:
            out.append(None)
            continue
        ranks = sorted(table)
        frames = sorted({t for rank in table for t in table[rank]})
        matrix = np.array([[table[rank].get(t, 0.0) for t in frames]
                           for rank in ranks])
        out.append((np.array(ranks), matrix, frames))

    if residual_gain:
        return out, [float(np.mean(g)) if g else 0.0 for g in gains]
    return out


def relative_energy(harmonics):
    """Share of the frame energy each note carries, averaged over its span.

    Loudness-independent, so a single threshold transfers between pieces.
    """
    total = {}
    for entry in harmonics:
        if entry is None:
            continue
        _, matrix, frames = entry
        for t, value in zip(frames, matrix.sum(axis=0)):
            total[t] = total.get(t, 0.0) + value

    out = []
    for entry in harmonics:
        if entry is None:
            out.append(0.0)
            continue
        _, matrix, frames = entry
        shares = [value / (total[t] + 1e-12)
                  for t, value in zip(frames, matrix.sum(axis=0))]
        out.append(float(np.mean(shares)) if shares else 0.0)
    return out


def validate(notes, harmonics, min_energy=None, max_polyphony=None):
    """Drop the notes the harmonic model does not actually need.

    Two criteria, both read off the decomposition:

    - a note whose share of the frame energy stays below `min_energy` is
      an artefact of the salience combs (an octave or a fifth of a real
      note), not something that was played;
    - at most `max_polyphony` notes may sound at once, the strongest
      first, which is what the instruments themselves can do.

    Returns the surviving notes together with their decomposition, so the
    classifier does not have to solve the whole system a second time.
    """
    from config import MIN_RELATIVE_ENERGY, MAX_POLYPHONY, POLYPHONY_MIN_FRACTION

    min_energy = MIN_RELATIVE_ENERGY if min_energy is None else min_energy
    max_polyphony = MAX_POLYPHONY if max_polyphony is None else max_polyphony

    shares = relative_energy(harmonics)
    keep = {i for i, share in enumerate(shares) if share >= min_energy}

    per_frame = {}
    for i in keep:
        entry = harmonics[i]
        if entry is None:
            continue
        _, matrix, frames = entry
        for t, value in zip(frames, matrix.sum(axis=0)):
            per_frame.setdefault(t, []).append((value, i))

    survived = {}
    for t, ranked in per_frame.items():
        ranked.sort(reverse=True)
        for _, i in ranked[:max_polyphony]:
            survived[i] = survived.get(i, 0) + 1

    kept_notes, kept_harmonics = [], []
    for i in sorted(keep):
        entry = harmonics[i]
        span = len(entry[2]) if entry is not None else 0
        if span == 0:
            continue
        if survived.get(i, 0) / span >= POLYPHONY_MIN_FRACTION:
            kept_notes.append(notes[i])
            kept_harmonics.append(entry)
    return kept_notes, kept_harmonics


def descriptors(entry, note):
    """The three timbre descriptors of one note, from its decomposition.

    Any of them may be None: a test that cannot be measured abstains
    rather than voting for the majority class.
    """
    empty = {"sustain": None, "flatness": None, "rolloff": None}
    if entry is None:
        return empty

    ranks, matrix, frames = entry
    envelope = matrix.sum(axis=0)
    if envelope.max() <= 0:
        return empty

    peak = int(np.argmax(envelope))
    held = peak + int(SUSTAIN_DELAY * FS_H)

    mean = matrix[:, max(0, peak - 2):peak + 5].mean(axis=1)
    total = mean.sum()

    if total <= 0:
        return empty
    share = mean / total

    heard = mean > 1e-9

    return {
        # Free decay against blown sustain: the piano lets go, the
        # trumpet holds as long as the player breathes. Read at a fixed
        # delay after the attack, never over "the end of the note": the
        # note boundaries are themselves estimated, and measuring the
        # tail of a mis-cut span reverses the test outright. On a note
        # too short for the delay to fit, this test abstains.
        "sustain": (float(envelope[held] / (envelope[peak] + 1e-12))
                    if held < len(envelope) else None),
        # How evenly the energy is spread over the partials. A string
        # piles almost everything onto the first two; the non-linear
        # propagation in a brass bore feeds them all.
        "flatness": float(np.exp(np.mean(np.log(share + 1e-12)))
                          / (np.mean(share) + 1e-12)),
        # Slope of the harmonic roll-off, fitted in log-log so it does
        # not depend on which partial ranks came through. A string dies
        # off near n^-1.4, a bore near n^-0.2.
        "rolloff": (float(np.polyfit(np.log(ranks[heard]),
                                     np.log(mean[heard]), 1)[0])
                    if heard.sum() >= 3 else None),
    }
