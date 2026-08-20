# RailBeat

## Description
Analyse un fichier audio (MP3) et joue une animation de formes géométriques qui se déplacent comme un train au rythme de la musique.

## Fonctionnalités
- Transcription MP3 → MIDI (`mp3toMidi.py`)
- Animation de formes géométriques (carré, rectangle, triangle, cercle) en train via Pygame (`gui.py`, `shapes.py`)

## Installation
```bash
pip install -e .        # ou : uv sync
```

## Utilisation
1. Place un fichier MP3 dans `sounds/`
2. Inscrire le nom du fichier dans `main.py` afin de pointer sur le bon fichier 
3. Lance `main.py`

## Structure
- `sounds/` : fichiers audio d'entrée
- `shapes.py` : définition des formes géométriques
- `gui.py` : affichage et boucle d'animation
- `mp3toMidi.py` : transcription audio vers MIDI