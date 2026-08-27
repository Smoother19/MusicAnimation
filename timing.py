import librosa as lr
import numpy as np
from config import SR, HOP, FS_ENV, MIN_FRAMES
from instruments import envelope

ONSET_HOP = 256
MIN_DURATION = MIN_FRAMES * HOP / SR      # ~0.14 s

def onset_times(y):
    """Onset times in seconds, at 5.8 ms resolution."""
    env = lr.onset.onset_strength(y=y, sr=SR, hop_length=ONSET_HOP,
                                  aggregate=np.median, lag=2, max_size=3)
    peaks = lr.util.peak_pick(x=env, pre_max=12, post_max=12,
                              pre_avg=12, post_avg=15,
                              delta=0.5 * np.std(env), wait=10)
    return lr.frames_to_time(peaks, sr=SR, hop_length=ONSET_HOP)


def snap_starts(notes, onsets, tolerance=0.12):
    """Pull each note onset to the nearest detected attack."""
    for note in notes:
        start, _ = note.seconds()
        near = onsets[np.abs(onsets - start) < tolerance]
        if len(near):
            note.start_s = float(near[np.argmin(np.abs(near - start))])
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
        origin = note.start * HOP / SR          # origine réelle de l'enveloppe
        end = origin + (peak + below[0]) / FS_ENV
        start, _ = note.seconds()
        if end > start + MIN_DURATION:
            note.end_s = end
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
                note.end_s = o_start
                break
    return notes