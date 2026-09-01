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
        self.build_profile()
        self.build_relief()
        self.build_bands()


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


    def ratio(self, note):
        span = self.pitch_hi - self.pitch_lo
        return max(0.0, min(1.0, (note["pitch"] - self.pitch_lo) / span))


    def build_profile(self, step=0.05, smooth=1.5):
        self.profile_step = step
        n = int(self.duration / step) + 2
        if not self.notes:
            self.heights = [0.5] * n
            return

        sums, counts = [0.0] * n, [0] * n
        for note in self.notes:
            r = self.ratio(note)
            a = max(0, int(note["start"] / step))
            b = min(n - 1, int(note["end"] / step))
            for i in range(a, b + 1):
                sums[i] += r
                counts[i] += 1

        raw, last = [0.5] * n, 0.5
        for i in range(n):
            if counts[i]:
                last = sums[i] / counts[i]
            raw[i] = last

        w = max(1, int(smooth / step))
        for _ in range(2):
            raw = self._smooth(raw, w)
        lo, hi = min(raw), max(raw)
        span = hi - lo
        self.heights = [(v - lo) / span for v in raw] if span > 1e-6 else [0.5] * n

    def build_relief(self, step=0.05, smooth=6.0):
        self.relief_step = step
        n = len(self.heights)
        raw = [self.density(i * step) for i in range(n)]

        w = max(1, int(smooth / step))
        for _ in range(2):
            raw = self._smooth(raw, w)

        lo, hi = min(raw), max(raw)
        span = hi - lo
        # Jamais tout a fait plat : 0.35 au calme, 1.0 au plus dense.
        self.reliefs = ([0.35 + 0.65 * (v - lo) / span for v in raw]
                        if span > 1e-6 else [1.0] * n)

    @staticmethod
    def _smooth(values, w):
        n = len(values)
        span = 2 * w + 1
        return [sum(values[(i + k) % n] for k in range(-w, w + 1)) / span
                for i in range(n)]

    def _sample(self, table, t, step):
        if not table:
            return 0.5
        n = len(table)
        i = (t / step) % n
        i0 = int(math.floor(i))
        f = i - i0
        f = f * f * (3 - 2 * f)          # lissage aux extremites de l'echantillon
        return table[i0 % n] + (table[(i0 + 1) % n] - table[i0 % n]) * f

    def relief(self, t):
        return self._sample(self.reliefs, t, self.relief_step)

    def profile(self, t):
        return self._sample(self.heights, t, self.profile_step)

    BANDS = 3

    def build_bands(self, step=0.05, smooth=0.12, hold=0.25):
        self.band_step = step
        n = len(self.heights)
        raw = [[0.0] * n for _ in range(self.BANDS)]

        for note in self.notes:
            b = min(self.BANDS - 1, int(self.ratio(note) * self.BANDS))
            a = max(0, int(note["start"] / step))
            z = min(n - 1, int(note["end"] / step))
            for i in range(a, z + 1):
                raw[b][i] += 1.0

        w = max(1, int(smooth / step))
        decay = step / hold
        self.bands = []
        for values in raw:
            values = self._smooth(values, w)
            peak = max(values) or 1.0
            values = [v / peak for v in values]

            # Montee immediate, retombee progressive.
            held, level = [0.0] * n, 0.0
            for i, v in enumerate(values):
                level = v if v > level else max(v, level - decay)
                held[i] = level
            self.bands.append(held)

    def band(self, t, index):
        "Energie de la bande `index` a l'instant t, entre 0 et 1."
        if not self.bands:
            return 0.0
        return self._sample(self.bands[index % self.BANDS], t, self.band_step)

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
