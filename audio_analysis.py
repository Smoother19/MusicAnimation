import numpy as np
import librosa

def frequences_vers_note(frequence):
    if frequence is None or frequence <= 0 or np.isnan(frequence):
        return None
    midi = librosa.hz_to_midi(frequence)
    return librosa.midi_to_note(round(midi))


def extraire_evenements(chemin_fichier, fps=30):
    #Renvoie une liste de dicts : {"temps", "volume", "note", "onset"}
    #Chargement (librosa convertit deja en mono + normalise entre -1 et 1)
    signal, sample_rate = librosa.load(chemin_fichier, sr=None, mono=True)

    # Taille de fenetre correspondant a 1 image video (ex: 1/30s a 44100Hz)
    hop_length = int(sample_rate / fps)

    # 2. YIN probabiliste (pyin) : detecte la frequence fondamentale dans une plage pour piano/saxophone (do1 grave -> do7 aigu)
    f0, voise, probabilite = librosa.pyin(
        signal,
        fmin=librosa.note_to_hz("C1"),
        fmax=librosa.note_to_hz("C7"),
        sr=sample_rate,
        hop_length=hop_length,
    )

    # 3. Volume (RMS)
    rms = librosa.feature.rms(y=signal, hop_length=hop_length, frame_length=hop_length * 2)[0]

    # 4. Detection d'onsets : librosa repere les debuts de notes (attaques)
    onset_frames = librosa.onset.onset_detect(
        y=signal, sr=sample_rate, hop_length=hop_length, units="frames"
    )
    onset_set = set(onset_frames.tolist())

    # On aligne tout sur le meme nombre d'images (le plus petit des 3 tableaux)
    nb_images = min(len(f0), len(rms))

    evenements = []
    for i in range(nb_images):
        note = frequences_vers_note(f0[i]) if voise[i] and probabilite[i] > 0.5 else None # probabilité pour les notes peu fiables
        evenements.append({
            "temps": i * hop_length / sample_rate,
            "volume": float(rms[i]),
            "frequence": float(f0[i]) if not np.isnan(f0[i]) else 0.0,
            "note": note,
            "onset": i in onset_set,
        })

    return evenements, sample_rate