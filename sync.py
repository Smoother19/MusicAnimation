import math
import statistics

class SyncMusic():
    def __init__(self, midi_array, train=None, clouds=None, fireworks=None, music=None):
        self.midi_array = midi_array
        self.train = train
        self.clouds = clouds
        self.fireworks = fireworks
        self.music = music
        
        # Séparation stricte par hauteur de note (Grave = Piano, Aigu = Trompette)
        self.notes, self.piano_notes, self.trumpet_notes = self.get_notes()
        
        self.cursor = 0
        self.piano_cursor = 0
        self.trumpet_cursor = 0
        
        self.build_density(window=0.25)

    def get_notes(self):
        piano = []
        trumpet = []
        all_notes = []
        
        for start, end, freq in self.midi_array:
            freq = float(freq)
            if freq <= 0:
                continue

            start_f = float(start)
            end_f = float(end)
            duration = end_f - start_f
            pitch = int(round(69 + 12 * math.log2(freq / 440.0)))

            note_data = {
                "start": start_f,
                "end": end_f,
                "freq": freq,
                "pitch": pitch,
                "duration": duration
            }
            all_notes.append(note_data)
            
            # --- LE FILTRE STRICT ---
            # La note 60 correspond au Do central du clavier. 
            # Mélodie (Trompette) = Aigu (>= 60)
            # Accompagnement (Piano) = Grave (< 60)
            if pitch >= 60:
                trumpet.append(note_data)
            else:
                piano.append(note_data)
                
        all_notes.sort(key=lambda n: n["start"])
        piano.sort(key=lambda n: n["start"])
        trumpet.sort(key=lambda n: n["start"])
        
        # Ce print va t'aider à voir si ton mp3toMidi a bien détecté des notes aiguës !
        #print(f"🎵 DIAGNOSTIC : {len(piano)} notes de Piano (<60) | {len(trumpet)} notes de Trompette (>=60)")
        
        return all_notes, piano, trumpet

    def update(self, t):
        started = []
        while self.cursor < len(self.notes) and self.notes[self.cursor]["start"] <= t:
            started.append(self.notes[self.cursor])
            self.cursor += 1
        return started

    def seek(self, t):
        self.cursor = 0
        self.piano_cursor = 0
        self.trumpet_cursor = 0
        
        while self.cursor < len(self.notes) and self.notes[self.cursor]["start"] < t:
            self.cursor += 1
        while self.piano_cursor < len(self.piano_notes) and self.piano_notes[self.piano_cursor]["start"] < t:
            self.piano_cursor += 1
        while self.trumpet_cursor < len(self.trumpet_notes) and self.trumpet_notes[self.trumpet_cursor]["start"] < t:
            self.trumpet_cursor += 1

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
        exact_i = t / self.window
        i0 = int(math.floor(exact_i))
        i1 = i0 + 1

        val0 = self.counts[i0] if 0 <= i0 < len(self.counts) else 0
        val1 = self.counts[i1] if 0 <= i1 < len(self.counts) else 0

        blend = exact_i - i0
        return val0 + (val1 - val0) * blend

    def speed_factor(self, t, lo=0.75, hi=1.35, dead=0.15):
        d = self.density(t)
        if self.ref_count <= 0: return 1.0
        r = d / self.ref_count
        if abs(r - 1.0) < dead: return 1.0
        return max(lo, min(hi, r))

    @property
    def duration(self):
        if not self.notes: return 0.0
        return max(n["end"] for n in self.notes)

    def energy(self, t, ceiling=2.5):
        if self.ref_count <= 0: return 0.0
        return max(0.0, min(1.0, self.density(t) / (self.ref_count * ceiling)))

    def check_piano_trigger(self, t, threshold=0.15): # <-- On passe à 0.15 au lieu de 0.05
        while self.piano_cursor < len(self.piano_notes) and self.piano_notes[self.piano_cursor]["end"] < t:
            self.piano_cursor += 1
            
        idx = self.piano_cursor
        while idx < len(self.piano_notes) and self.piano_notes[idx]["start"] <= t + threshold:
            if abs(self.piano_notes[idx]["start"] - t) <= threshold:
                return True
            idx += 1
        return False

    def check_trumpet_trigger(self, t, threshold=0.15): # <-- Pareil ici
        while self.trumpet_cursor < len(self.trumpet_notes) and self.trumpet_notes[self.trumpet_cursor]["end"] < t:
            self.trumpet_cursor += 1
            
        idx = self.trumpet_cursor
        while idx < len(self.trumpet_notes) and self.trumpet_notes[idx]["start"] <= t + threshold:
            if abs(self.trumpet_notes[idx]["start"] - t) <= threshold:
                return True
            idx += 1
        return False