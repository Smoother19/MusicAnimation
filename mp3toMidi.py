import librosa as lr
import soundfile as sf
import numpy as np
from pathlib import Path
import mido as md
import matplotlib.pyplot as plt

# Charge le fichier audio
music_dir = Path("sounds")
output_dir = Path("output")
audio, sample_rate = lr.load(str(music_dir / "Ecossaise_Both.mp3"), sr=None)

D = lr.stft(audio)
print(D)
plt.imshow(np.abs(D))
plt.show()
D_harmonic16, D_percussive16 = librosa.decompose.hpss(D, margin=16)



instruments = [
    (27.5, 4186, 'Piano'),
    (82, 880, 'Guitare acoustique'),
    (82, 1175, 'Guitare électrique'),
    (196, 3520, 'Violon'),
    (130, 1300, 'Alto'),
    (65, 1050, 'Violoncelle'),
    (41, 349, 'Contrebasse'),
    (30, 3500, 'Harpes'),
    (261, 2093, 'Flûte traversière'),
    (523, 4186, 'Flûte piccolo'),
    (164, 1567, 'Clarinette'),
    (98, 622, 'Clarinette basse'),
    (262, 1044, 'Saxophone soprano'),
    (220, 880, 'Saxophone alto'),
    (110, 698, 'Saxophone ténor'),
    (55, 523, 'Saxophone baryton'),
    (165, 988, 'Trompette'),
    (73, 523, 'Trombone'),
    (58, 698, 'Basson'),
    (233, 1170, 'Hautbois'),
    (30, 2000, 'Accordéon'),
    (16, 16744, 'Orgue'),
    (100, 250, 'Batterie (caisse claire)'),
    (30, 100, 'Batterie (grosse caisse)'),
    (60, 250, 'Timbales'),
    (300, 15000, 'Cymbales'),
    (1200, 15000, 'Glockenspiel'),
    (500, 2000, 'Xylophone'),
    (65, 1050, 'Marimba'),
    (500, 15000, 'Triangle'),
    (250, 1100, 'Voix humaine (soprano)'),
    (220, 880, 'Voix humaine (alto)'),
    (130, 520, 'Voix humaine (ténor)'),
    (82, 330, 'Voix humaine (basse)'),
]



for low, high, name in instruments :
    f0 = lr.yin(y=audio, sr=sample_rate, fmin=low, fmax=high)
    S = np.abs(lr.stft(audio))
    C = librosa.cqt(y=audio, sr=sample_rate)
    

    # Reconstruction audio
    audio_band = lr.hz_to_midi(f0)


    '''
    sf.write(f"{output_dir / name}.wav", audio_band, sample_rate)
    print(f"{name}.wav généré")
    '''