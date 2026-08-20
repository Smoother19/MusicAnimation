import math


class SyncMusic():
    def __init__(self, midi_array, train=None, clouds=None, fireworks=None, music=None):
        self.midi_array = midi_array
        self.train = train
        self.clouds = clouds
        self.fireworks = fireworks
        self.music = music
        self.notes = self.get_notes()
        self.cursor = 0

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