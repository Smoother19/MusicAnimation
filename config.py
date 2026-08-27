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