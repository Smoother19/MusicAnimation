import math
import statistics


class SyncMusic():

    def __init__(self, midi_array, train=None, clouds=None, fireworks=None,
                 music=None, latency=0.04):
        self.midi_array = midi_array
        self.train = train
        self.clouds = clouds
        self.fireworks = fireworks
        self.music = music

        self.latency = latency

        self.notes = self.get_notes()
        self.cursor = 0
        self.playing = []
        self.last_t = 0.0

        pitches = sorted(n["pitch"] for n in self.notes) or [60]
        self.pitch_lo = pitches[int(len(pitches) * 0.05)]
        self.pitch_hi = max(self.pitch_lo + 6, pitches[int(len(pitches) * 0.95)])

        self.build_density(window=0.25)

    # --- lecture du MIDI ------------------------------------------------

    def get_notes(self):
        notes = []
        for row in self.midi_array:
            freq = float(row[2])
            if freq <= 0:
                continue
            start, end = float(row[0]), float(row[1])
            notes.append({
                "start": start,
                "end": end,
                "duration": end - start,
                "freq": freq,
                "pitch": int(round(69 + 12 * math.log2(freq / 440.0))),
                "instrument": row[3] if len(row) > 3 else "piano",
            })
        notes.sort(key=lambda n: n["start"])

        kinds = {n["instrument"] for n in notes}
        if len(kinds) < 2:
            print("sync : une seule piste dans le MIDI, tout passe en piano. "
                  "Regenere la transcription pour avoir piano et trompette.")
        return notes

    def update(self, t):
        t -= self.latency
        if t < self.last_t:              # la lecture est repartie en arriere
            self.seek(t)
            self.playing = []
        self.last_t = t

        started = []
        while self.cursor < len(self.notes) and self.notes[self.cursor]["start"] <= t:
            started.append(self.notes[self.cursor])
            self.cursor += 1

        self.playing = [n for n in self.playing if n["end"] > t] + started
        return started

    def active(self):
        return self.playing

    def seek(self, t):
        self.cursor = 0
        while self.cursor < len(self.notes) and self.notes[self.cursor]["start"] < t:
            self.cursor += 1

    # --- position d'une note dans le morceau ----------------------------

    def ratio(self, note):
        span = self.pitch_hi - self.pitch_lo
        return max(0.0, min(1.0, (note["pitch"] - self.pitch_lo) / span))

    # --- densite --------------------------------------------------------

    def build_density(self, window=0.25):
        self.window = window
        if not self.notes:
            self.counts = [0]
            self.ref_count = 1.0
            return

        end = max(n["end"] for n in self.notes)
        self.counts = [0] * (int(end / window) + 2)
        for n in self.notes:
            self.counts[int(n["start"] / window)] += 1

        active = [c for c in self.counts if c > 0]
        self.ref_count = float(statistics.mean(active)) if active else 1.0

    def density(self, t):
        'Interpolee entre deux blocs : la vitesse varie sans marches.'
        exact = t / self.window
        i0 = int(math.floor(exact))
        i1 = i0 + 1
        v0 = self.counts[i0] if 0 <= i0 < len(self.counts) else 0
        v1 = self.counts[i1] if 0 <= i1 < len(self.counts) else 0
        return v0 + (v1 - v0) * (exact - i0)

    def speed_factor(self, t, lo=0.75, hi=1.35, dead=0.15):
        if self.ref_count <= 0:
            return 1.0
        r = self.density(t) / self.ref_count
        if abs(r - 1.0) < dead:
            return 1.0
        return max(lo, min(hi, r))

    def energy(self, t, ceiling=2.5):
        'Densite ramenee entre 0.0 (silence) et 1.0 (passage dense).'
        if self.ref_count <= 0:
            return 0.0
        return max(0.0, min(1.0, self.density(t) / (self.ref_count * ceiling)))

    @property
    def duration(self):
        'Duree totale du morceau en secondes (fin de la derniere note).'
        if not self.notes:
            return 0.0
        return max(n["end"] for n in self.notes)
