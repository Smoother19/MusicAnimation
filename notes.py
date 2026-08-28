from dataclasses import dataclass

import librosa
import numpy as np

from config import (SR, N_FFT, HOP, MAX_NOTES, SILENCE_THRESHOLD, MIN_FRAMES,
                    GAP_TOLERANCE, MIDI_MIN, MIDI_MAX, midi_to_hz, hz_to_midi)
from salience import detect


@dataclass
class Note:
    """A detected note. Times are in frames; use seconds() to convert.

    slope, vibrato and instrument are filled in by the instruments module.
    start_s and end_s are set by the timing module when available.
    """
    midi: int
    start: int
    end: int
    slope: float | None = None
    vibrato: float | None = None
    instrument: str | None = None
    start_s: float | None = None
    end_s: float | None = None

    @property
    def duration(self):
        return self.end - self.start

    @property
    def f0(self):
        return midi_to_hz(self.midi)

    def seconds(self):
        start = self.start_s if self.start_s is not None else self.start * HOP / SR
        end = self.end_s if self.end_s is not None else self.end * HOP / SR
        return start, end


def _pitches_per_frame(y, max_notes):
    window = np.hanning(N_FFT)
    frames = []

    for start in range(0, len(y) - N_FFT, HOP):
        seg = y[start:start + N_FFT] * window

        if np.sqrt(np.mean(seg**2)) < SILENCE_THRESHOLD:
            frames.append([])
            continue

        mag = np.abs(np.fft.rfft(seg))
        pitches = (hz_to_midi(f) for f in detect(mag, max_notes=max_notes))
        frames.append([p for p in pitches if MIDI_MIN <= p <= MIDI_MAX])

    return frames


def _stabilize(frames, width=2):
    """Drop a pitch when a neighbour one semitone away dominates around it."""
    out = []
    for i, active in enumerate(frames):
        lo, hi = max(0, i - width), min(len(frames), i + width + 1)
        around = [q for j in range(lo, hi) for q in frames[j]]
        out.append([p for p in active
                    if around.count(p) >= around.count(p - 1)
                    and around.count(p) >= around.count(p + 1)])
    return out


def _fill_gaps(frames, tolerance=GAP_TOLERANCE):
    """Bridge short dropouts so a sustained note stays a single note."""
    seen = {}
    for i, active in enumerate(frames):
        for p in active:
            seen.setdefault(p, []).append(i)

    out = [set(a) for a in frames]
    for p, indices in seen.items():
        for a, b in zip(indices, indices[1:]):
            if 1 < b - a <= tolerance + 1:
                for k in range(a + 1, b):
                    out[k].add(p)

    return [sorted(s) for s in out]


def _group(frames):
    """Merge consecutive frames of the same pitch into notes.

    Notes still open when the signal ends are discarded.
    """
    notes, open_notes = [], {}

    for i, active in enumerate(frames):
        for p in list(open_notes):
            if p not in active:
                start = open_notes.pop(p)
                if i - start >= MIN_FRAMES:
                    notes.append(Note(midi=p, start=start, end=i))
        for p in active:
            open_notes.setdefault(p, i)

    return notes


def transcribe(path, max_notes=MAX_NOTES):
    """Transcribe an audio file into notes. Returns (signal, notes).

    The signal is returned because the instrument descriptors need it.
    """
    y, _ = librosa.load(path, sr=SR, mono=True)

    frames = _pitches_per_frame(y, max_notes)
    frames = _stabilize(frames)
    frames = _fill_gaps(frames)

    return y, _group(frames)