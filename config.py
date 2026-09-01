import numpy as np

SCREEN_WIDTH = 1280
SCREEN_HEIGHT = 720
RAIL_Y = SCREEN_HEIGHT - 180
BACKGROUND = (18, 18, 34)
SPEED = 100.0 

SCREEN_WIDTH = 1280
SCREEN_HEIGHT = 720
RAIL_Y = SCREEN_HEIGHT - 180
BACKGROUND = (18, 18, 34)
SPEED = 100.0 
# ---------------------------------------------------------------- Cycle jour/nuit
HORIZON_Y = 470                      # ligne d'horizon : base de la crete de premier plan
SKY_CENTER_X = SCREEN_WIDTH / 2
SKY_RADIUS_X = SCREEN_WIDTH * 0.45   # demi-largeur de la course des astres
SKY_RADIUS_Y = 400                   # hauteur max des astres au-dessus de l'horizon

CYCLE_DURATION = 24.0                # secondes de musique pour un cycle (si duree inconnue)
SKY_CYCLES_PER_TRACK = 4             # nb de cycles complets sur un morceau
SKY_START_PHASE = 0.10               # on demarre juste apres le lever du soleil
SKY_BANDS = 24                       # nb de bandes du degrade de ciel
SKY_NB_STARS = 70
SKY_BODY_PARTS = 24                  # nb de triangles par astre
SKY_HALO_LAYERS = 5
SKY_PULSE_DECAY = 3.0                # vitesse de retombee de la pulsation

SUN_RADIUS = 46
SUN_COLOR = (255, 216, 102)
SUN_HALO = (255, 148, 64)
SUN_MIN_RAYS = 8
SUN_MAX_RAYS = 20

MOON_RADIUS = 34
MOON_COLOR = (234, 238, 248)
MOON_HALO = (150, 175, 235)
MOON_CRESCENT = 0.28                 # 0 = pleine lune | 0.7 = fin croissant

DAY_TOP = (74, 152, 224)
DAY_BOTTOM = (186, 220, 240)
NIGHT_TOP = (8, 10, 28)
NIGHT_BOTTOM = (30, 33, 66)
DUSK_TOP = (62, 44, 100)
DUSK_BOTTOM = (240, 128, 78)
AMBIENT_NIGHT = (14, 16, 34)         # teinte vers laquelle Sky.tint() ramene la scene




SR = 44100

# Long window: frequency resolution, used for pitch detection.
N_FFT = 8192
HOP = 2048
BIN = SR / N_FFT

# Short window: time resolution, used for envelope and vibrato.
N_ENV = 1024
HOP_ENV = 256
BIN_ENV = SR / N_ENV
FS_ENV = SR / HOP_ENV

# Multi-pitch engine.
N_PARTIALS = 12
ALPHA, BETA = 52.0, 320.0       # Klapuri salience weighting
MAX_NOTES = 5                   # the pieces played here hold 4-5 voices
SALIENCE_THRESHOLD = 0.10       # relative to the first pitch found
CANCEL_FACTOR = 0.9

# Note segmentation.
SILENCE_THRESHOLD = 0.005       # RMS
MIN_FRAMES = 3                  # ~140 ms
GAP_TOLERANCE = 1               # frames
MIDI_MIN, MIDI_MAX = 33, 84     # A1 - C6

# Onset detection.
ONSET_HOP = 256
ONSET_DELTA = 0.10              # peak height, in standard deviations
ONSET_WAIT = 10                 # frames between two onsets, ~58 ms
# The peak of the onset strength lands after the attack that caused it, by
# the length of the smoothing windows the picker averages over. Measured at
# +43 ms on Ecossaise and +47 ms on PinkPanther -- a property of the
# detector, not of either recording, so it is subtracted back out.
ONSET_LAG = 0.040               # seconds

# Onset-driven re-segmentation.
SPLIT_RATIO = 1.5               # rise a note's own envelope must show to be cut
SPLIT_GUARD = 0.06              # no cut within this of a note boundary
SPLIT_WINDOW = 0.05             # seconds compared either side of an attack
MIN_DURATION = 0.09             # a fragment shorter than this is dropped
MERGE_GAP = 0.05                # two fragments closer than this are one note
SNAP_TOLERANCE = 0.10           # distance over which a start is pulled to an onset

# Harmonic decomposition (harmonics.py).
HARM_N_FFT = 4096
HARM_HOP = 512
HARM_FMAX = 6000.0
HARM_PARTIALS = 10
HARM_LOBE = 3                   # half-width of a partial template, in bins

# Note validation. A note carrying less than this share of the frame energy
# is an artefact of the harmonic combs, not a note that was played.
#
# This is the knob that sets how many notes come out. Measured on
# Ecossaise_Both.mp3 against its own score (746 notes):
#
#   0.060 -> 761 notes (1.02x)  recall 57%  precision 60%
#   0.070 -> 716 notes (0.96x)  recall 56%  precision 62%
#   0.095 -> 610 notes (0.82x)  recall 50%  precision 65%
#
# 0.070 lands on the right count, which is what the animation is driven
# by. Lower it to feed more events to the animation, raise it for fewer
# and cleaner ones.
MIN_RELATIVE_ENERGY = 0.070
MAX_POLYPHONY = 6               # simultaneous notes kept, strongest first
POLYPHONY_MIN_FRACTION = 0.5    # share of its frames a note must survive

# Piano / trumpet classification: three independent tests, each with its
# own threshold and its own reliability weight. Calibrated by
# `python evaluation.py calibration` on the separated Ecossaise tracks.
SUSTAIN_DELAY = 0.35            # seconds after the attack the sustain is read
SUSTAIN_THRESHOLD = 0.7567      # amplitude still held that long after the peak
FLATNESS_THRESHOLD = 0.6587     # geometric / arithmetic mean of the partials
ROLLOFF_THRESHOLD = -0.8509     # log-log slope of the partial amplitudes
TEST_WEIGHTS = {"sustain": 1.0, "flatness": 1.0, "rolloff": 1.0}
TEST_SPREAD = {"sustain": 0.2451, "flatness": 0.3191, "rolloff": 0.8916}
FUSION_THRESHOLD = -0.22        # above this the note is a trumpet

MIDI_PROGRAMS = {"piano": 0, "trumpet": 56}


def midi_to_hz(p):
    return 440.0 * 2.0 ** ((p - 69) / 12.0)


def hz_to_midi(f):
    return int(round(69 + 12 * np.log2(f / 440.0)))