import librosa as lr
import numpy as np

from config import (SR, HOP, FS_ENV, MIN_FRAMES, ONSET_HOP, ONSET_DELTA,
                    ONSET_WAIT, ONSET_LAG, SPLIT_RATIO, SPLIT_GUARD, SPLIT_WINDOW,
                    MIN_DURATION, SNAP_TOLERANCE)
from instruments import envelope

MIN_NOTE = MIN_FRAMES * HOP / SR          # ~0.14 s


def onset_times(y):
    """Onset times in seconds, at 5.8 ms resolution.

    `max_size` stays at 1: the local-max filtering across frequency it
    otherwise applies swallows every attack that is not the loudest of
    its neighbourhood, which on a polyphonic piece is most of them.

    The picker's own lag is taken back off at the end: left in, it puts
    every onset a median 44 ms late, and since the note starts are then
    snapped onto these, the whole transcription inherits the offset.
    """
    strength = lr.onset.onset_strength(y=y, sr=SR, hop_length=ONSET_HOP,
                                       aggregate=np.median, lag=1, max_size=1)
    peaks = lr.util.peak_pick(x=strength, pre_max=6, post_max=6,
                              pre_avg=6, post_avg=8,
                              delta=ONSET_DELTA * np.std(strength),
                              wait=ONSET_WAIT)
    times = lr.frames_to_time(peaks, sr=SR, hop_length=ONSET_HOP) - ONSET_LAG
    return times[times >= 0]


def _reattacks(entry, onsets, start, end, ratio, guard, window):
    """The attacks inside a note where that note's own amplitude rises.

    An attack anywhere in the mix is not this note's attack. Cutting on
    all of them shreds every held note the moment another instrument
    plays over it, which is where three false notes out of four came
    from.
    """
    from harmonics import FS_H

    if entry is None:
        return []

    _, matrix, frames = entry
    amplitude = matrix.sum(axis=0)
    origin = frames[0] / FS_H
    half = max(2, int(window * FS_H))

    cuts = []
    for t in onsets:
        if not (start + guard < t < end - guard):
            continue
        k = int((t - origin) * FS_H)
        if k - half < 0 or k + half >= len(amplitude):
            continue
        before = amplitude[max(0, k - half):k].mean()
        after = amplitude[k:k + half].max()
        if before > 1e-9 and after / before >= ratio:
            cuts.append(float(t))
    return cuts


def split_on_onsets(notes, onsets, harmonics, ratio=SPLIT_RATIO,
                    guard=SPLIT_GUARD, window=SPLIT_WINDOW,
                    min_duration=MIN_DURATION):
    """Cut every note at its own re-attacks.

    Without this a key struck three times in a row is a single held note:
    the pitch never leaves the frame, so the grouping never closes it.
    The rise test decides which of the attacks heard in the mix belong
    to this note.
    """
    out = []
    for note, entry in zip(notes, harmonics):
        start, end = note.seconds()
        cuts = _reattacks(entry, onsets, start, end, ratio, guard, window)
        bounds = [start] + cuts + [end]
        for a, b in zip(bounds, bounds[1:]):
            if b - a >= min_duration:
                out.append(note.respan(a, b))
    return sorted(out, key=lambda n: n.seconds()[0])


def snap_starts(notes, onsets, tolerance=SNAP_TOLERANCE):
    """Pull each note onset to the nearest detected attack."""
    if not len(onsets):
        return notes
    for note in notes:
        start, end = note.seconds()
        distance = np.abs(onsets - start)
        if distance.min() < tolerance:
            snapped = float(onsets[int(np.argmin(distance))])
            if snapped < end - MIN_DURATION:
                note.set_start(snapped)
    return notes


def decay_ends(y, notes, ratio=0.35):
    """End each note when its own amplitude drops below `ratio` of its peak."""
    for note in notes:
        amp = envelope(y, note.f0, note.start, note.end)
        if len(amp) == 0:
            continue
        peak = int(np.argmax(amp))
        threshold = ratio * amp[peak]
        below = np.nonzero(amp[peak:] < threshold)[0]
        if len(below) == 0:
            continue
        origin = note.start * HOP / SR
        end = origin + (peak + below[0]) / FS_ENV
        start, _ = note.seconds()
        if end > start + MIN_NOTE:
            note.set_end(end)
    return notes


def clip_to_next(notes, max_gap=0.05):
    """Truncate each note when the next one starts in the same register."""
    ordered = sorted(notes, key=lambda n: n.seconds()[0])
    for i, note in enumerate(ordered):
        start, end = note.seconds()
        for other in ordered[i + 1:]:
            o_start, _ = other.seconds()
            if o_start >= end:
                break
            if abs(other.midi - note.midi) <= 4 and o_start > start + max_gap:
                note.set_end(o_start)
                break
    return notes
