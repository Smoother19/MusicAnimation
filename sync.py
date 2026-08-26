import math
import statistics


class SyncMusic():
    def __init__(self, midi_array, train=None, clouds=None, fireworks=None, music=None):
        self.midi_array = midi_array
        self.train = train
        self.clouds = clouds
        self.fireworks = fireworks
        self.music = music
        self.notes = self.get_notes()
        self.cursor = 0
        self.build_density()

    def get_notes(self):
        notes = []
        for start, end, freq in self.midi_array:
            freq = float(freq)
            if freq <= 0:
                continue
            notes.append({
                "start": float(start),
                "end": float(end),
                "freq": freq,
                "pitch": int(round(69 + 12 * math.log2(freq / 440.0))),
            })
        notes.sort(key=lambda n: n["start"])
        return notes

    def update(self, t):
        started = []
        while self.cursor < len(self.notes) and self.notes[self.cursor]["start"] <= t:
            started.append(self.notes[self.cursor])
            self.cursor += 1
        return started

    def seek(self, t):
        self.cursor = 0
        while self.cursor < len(self.notes) and self.notes[self.cursor]["start"] < t:
            self.cursor += 1

    def build_density(self, window=2.0):
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
        self.ref_count = float(statistics.median(active)) if active else 1.0
 
    def density(self, t):
        i = int(t / self.window)
        return self.counts[i] if 0 <= i < len(self.counts) else 0
 
    def density_ratio(self, t):
        i = int(t / self.window)
        if i <= 0 or i >= len(self.counts):
            return 1.0
        prev = self.counts[i - 1]
        return self.counts[i] / prev if prev else 1.0
 
    def speed_factor(self, t, lo=0.75, hi=1.35, dead=0.20):
        d = self.density(t)
        if self.ref_count <= 0:
            return 1.0
        r = d / self.ref_count
        if abs(r - 1.0) < dead:
            return 1.0
        return max(lo, min(hi, r))

    @property
    def duration(self):
        '''
        Duree totale du morceau en secondes (fin de la derniere note)
        '''
        if not self.notes:
            return 0.0
        return max(n["end"] for n in self.notes)

    def energy(self, t, ceiling=2.0):
        '''
        Densite de notes normalisee entre 0.0 (silence) et 1.0 (passage dense)
        '''
        if self.ref_count <= 0:
            return 0.0
        return max(0.0, min(1.0, self.density(t) / (self.ref_count * ceiling)))

    def speed_factor(self, t, lo=0.75, hi=1.35, dead=0.20):
        d = self.density(t)
        if self.ref_count <= 0:
            return 1.0
        r = d / self.ref_count
        if abs(r - 1.0) < dead:
            return 1.0
        return max(lo, min(hi, r))
