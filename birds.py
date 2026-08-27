import math
import random

import pygame as ui

from shapes import TriangularShape, STATS, shade
from sky import lerp, lerp_color
from config import *

# ----------------------------------------------------------------
BIRD_Y_TOP = 60                  # altitude de la note la plus aigue du morceau
BIRD_Y_BOTTOM = HORIZON_Y - 40   # altitude de la note la plus grave
BIRD_SIZE = 30                   # longueur d'un oiseau au premier plan (px)
BIRD_COLOR = (40, 42, 54)        # plumage de jour : silhouette sombre
BIRD_COLOR_NIGHT = (108, 116, 152)  # plumage de nuit : eclaire par la lune
BEAK_COLOR = (226, 158, 72)
BIRD_SPEED = 55.0                # vitesse de croisiere horizontale (px/s)
BIRD_FLAP = 6.5                  # battements par seconde au repos
BIRD_SPRING = 3.0                # raideur du rattrapage de la formation
BIRD_DAMPING = 2.6               # freinage : plus haut = vol plus rigide
BIRD_SPACING = 1.35              # ecart entre deux rangs du V (x taille)
BIRD_HAZE = 0.75                 # perspective aerienne : fondu des plans lointains
BIRD_ALT_RATE = 1.6              # vitesse de montee/descente vers la note visee
BIRD_BAND_STRETCH = 2.2          # amplitude verticale d une nuee dans son registre

PLANE_FAR, PLANE_MID, PLANE_NEAR = 0, 1, 2
PLANE_DEPTH = {PLANE_FAR: 0.15, PLANE_MID: 0.5, PLANE_NEAR: 0.95}


class Bird(TriangularShape):
    '''
    Un oiseau dessine en 6 triangles : corps (2), aile haute, aile basse,
    queue et bec. Les ailes battent autour de l'axe du corps et l'oiseau
    s'incline selon sa vitesse verticale.

    Attributes:
        x, y (float): position du centre du corps a l'ecran.
        depth (float): 0.0 = plan lointain, 1.0 = premier plan.
        size (float): longueur du corps, deja mise a l'echelle de la profondeur.
        phase (float): position dans le cycle de battement d'ailes.
        flap_speed (float): battements par seconde propres a cet oiseau.
        heading (float): angle de l'oiseau, calcule depuis sa vitesse.

    Methods:
        update(dt, tx, ty, boost): rejoint sa place dans la formation.
        parts(): retourne [(triangle, couleur)] pour la frame courante.
        list_triangles(): API TriangularShape, sans les couleurs.
        draw(screen): dessine les 6 triangles avec leurs couleurs propres.
    '''

    def __init__(self, x, y, depth=1.0, base_size=BIRD_SIZE, color=BIRD_COLOR,
                 flap=BIRD_FLAP, rng=random):
        size = base_size * lerp(0.35, 1.0, depth)
        super().__init__(x, y, size, size * 0.5, color)
        self.depth = depth
        self.size = size
        self.vx = 0.0
        self.vy = 0.0
        self.tilt = 0.0
        self.facing = -1        # -1 : vers la gauche, +1 : vers la droite
        self.phase = rng.uniform(0, math.tau)
        self.flap_speed = flap * rng.uniform(0.85, 1.15)
        self.beak_color = BEAK_COLOR

    def update(self, dt, tx, ty, boost=0.0):
        '''
        tx, ty : place visee dans la formation
        boost  : 0.0 a 1.0, accelere le battement quand la musique s'anime
        '''
        # ressort amorti vers la position visee : donne un vol souple
        self.vx += (tx - self.x) * BIRD_SPRING * dt
        self.vy += (ty - self.y) * BIRD_SPRING * dt
        damp = math.exp(-BIRD_DAMPING * dt)
        self.vx *= damp
        self.vy *= damp
        self.x += self.vx * dt
        self.y += self.vy * dt

        # l'oiseau pique ou cabre selon sa vitesse verticale
        self.tilt = max(-0.5, min(0.5, math.atan2(self.vy, max(30.0, abs(self.vx)))))
        if abs(self.vx) > 8.0:
            self.facing = 1 if self.vx > 0 else -1

        # il bat plus vite quand il monte et quand la musique est dense
        climb = max(0.0, -self.vy) / 120.0
        self.phase += self.flap_speed * (1.0 + 0.7 * boost + 0.5 * climb) * dt * math.tau

    def _place(self, points):
        '''
        Coordonnees locales (nez vers +x, y vers le bas) -> coordonnees ecran.
        On applique d abord le miroir horizontal selon le sens de vol, puis
        l inclinaison : le ventre reste toujours en bas.
        '''
        f = self.facing
        theta = self.tilt * f
        cos_a, sin_a = math.cos(theta), math.sin(theta)
        out = []
        for px, py in points:
            px *= f
            out.append((self.x + px * cos_a - py * sin_a,
                        self.y + px * sin_a + py * cos_a))
        return out

    def wing(self, shoulder_y, span, lift, lag):
        '''
        Une aile = 1 triangle. Elle part de l epaule, file vers l arriere et
        sa pointe monte ou descend selon le battement.
        '''
        a = 0.85 * math.sin(self.phase + lag)
        s = self.size
        tip = (-0.02 * s - span * 0.38, shoulder_y - span * math.sin(a) * lift)
        return [(0.22 * s, shoulder_y + 0.02 * s),
                (-0.20 * s, shoulder_y - 0.01 * s),
                tip]

    def parts(self):
        '''
        Geometrie de l oiseau pour la frame courante : liste de
        (triangle, couleur). Corps (2 triangles), 2 ailes, queue et bec.
        '''
        s = self.size
        span = 0.66 * s

        nose = (0.46 * s, -0.02 * s)
        back = (-0.06 * s, -0.11 * s)
        joint = (-0.34 * s, -0.02 * s)
        belly = (0.06 * s, 0.12 * s)

        body_up = [nose, back, joint]
        body_dn = [nose, joint, belly]
        tail = [(-0.26 * s, -0.07 * s), (-0.62 * s, -0.12 * s), (-0.56 * s, 0.05 * s)]
        beak = [(0.42 * s, -0.06 * s), (0.42 * s, 0.01 * s), (0.60 * s, -0.03 * s)]
        # les deux ailes battent ensemble, la plus proche avec un leger retard
        wing_far = self.wing(-0.06 * s, span, 0.85, 0.35)
        wing_near = self.wing(0.0, span, 1.0, 0.0)

        c = self.color
        return [
            (self._place(wing_far), shade(c, 0.72)),    # aile eloignee : dans l ombre
            (self._place(tail), shade(c, 0.90)),
            (self._place(body_up), shade(c, 0.95)),
            (self._place(body_dn), c),
            (self._place(beak), self.beak_color),
            (self._place(wing_near), shade(c, 1.18)),   # aile proche : eclairee
        ]

    def list_triangles(self):
        return [tri for tri, _ in self.parts()]

    def draw(self, screen, ox=0, oy=0, angle=0, pivot=None):
        parts = self.parts()
        STATS["triangles"] += len(parts)
        for tri, color in parts:
            pts = [(px + ox, py + oy) for px, py in tri]
            if angle != 0 and pivot is not None:
                pts = [self.rotate_point(p, pivot, angle) for p in pts]
            ui.draw.polygon(screen, color, pts)


class Flock:
    '''
    Une nuee en V. Elle traverse l'ecran horizontalement et son altitude suit
    la hauteur des notes de son registre : plus la note est aigue, plus la
    nuee monte. Chaque nuee vit sur un seul plan de profondeur.

    Attributes:
        depth (float): 0.0 lointain a 1.0 premier plan.
        plane (int): PLANE_FAR, PLANE_MID ou PLANE_NEAR, pour l'ordre de dessin.
        pitch_lo, pitch_hi (int): registre MIDI auquel cette nuee reagit.
        birds (list[Bird]): le chef est birds[0], les autres tiennent le V.
        alt, alt_target (float): altitude courante et altitude visee.
        excite (float): 0.0 a 1.0, retombe apres chaque note.

    Methods:
        update(dt, notes, energy, scroll_speed, sky): avance la nuee.
        draw(screen): dessine tous les oiseaux de la nuee.
    '''

    def __init__(self, depth, nb_birds, pitch_lo, pitch_hi, y_map,
                 direction=-1, rng=random):
        self.depth = depth
        self.plane = PLANE_FAR if depth < 0.33 else (PLANE_MID if depth < 0.7 else PLANE_NEAR)
        self.pitch_lo = pitch_lo
        self.pitch_hi = pitch_hi
        self.y_map = y_map                 # fonction pitch -> y ecran
        self.direction = direction         # -1 : vers la gauche, +1 : vers la droite
        self.rng = rng
        self.speed = BIRD_SPEED * lerp(0.45, 1.0, depth) * rng.uniform(0.85, 1.2)

        self.alt = y_map((pitch_lo + pitch_hi) / 2)
        self.alt_target = self.alt
        self.excite = 0.0
        self.wobble = rng.uniform(0, math.tau)

        self.lead_x = self._spawn_x()
        self.birds = [Bird(self.lead_x, self.alt, depth, rng=rng)
                      for _ in range(nb_birds)]
        for i, bird in enumerate(self.birds):
            dx, dy = self.formation_offset(i)
            bird.x = self.lead_x + dx
            bird.y = self.alt + dy

    def _spawn_x(self):
        margin = 220
        return SCREEN_WIDTH + margin if self.direction < 0 else -margin

    def formation_offset(self, i):
        'Place l oiseau i dans le V, derriere le chef'
        if i == 0:
            return 0.0, 0.0
        rank = (i + 1) // 2
        side = -1 if i % 2 else 1
        step = self.birds[0].size * BIRD_SPACING
        return -self.direction * rank * step, side * rank * step * 0.55

    def register_hit(self, notes):
        'Retient les notes du registre de la nuee et vise leur hauteur'
        mine = [n for n in notes if self.pitch_lo <= n["pitch"] <= self.pitch_hi]
        if not mine:
            return
        pitch = sum(n["pitch"] for n in mine) / len(mine)
        self.alt_target = self.y_map(pitch)
        self.excite = min(1.0, self.excite + 0.35 + 0.1 * len(mine))

    def update(self, dt, notes=(), energy=0.0, scroll_speed=0.0, sky=None):
        self.register_hit(notes)
        self.excite = max(0.0, self.excite - dt * 1.2)
        self.wobble += dt * 0.8

        # montee / descente progressive vers la note visee
        self.alt += (self.alt_target - self.alt) * min(1.0, dt * BIRD_ALT_RATE)

        # le chef avance, un peu emporte par le defilement du decor
        drift = -scroll_speed * 0.05 * self.depth
        self.lead_x += (self.direction * self.speed + drift) * dt

        out = -400 if self.direction < 0 else SCREEN_WIDTH + 400
        if (self.direction < 0 and self.lead_x < out) or \
           (self.direction > 0 and self.lead_x > out):
            self.respawn()

        boost = min(1.0, self.excite + energy * 0.6)
        for i, bird in enumerate(self.birds):
            dx, dy = self.formation_offset(i)
            # petit balancement propre a chaque oiseau : le V n'est pas fige
            sway = math.sin(self.wobble + i * 1.7) * bird.size * 0.35
            bird.update(dt, self.lead_x + dx, self.alt + dy + sway, boost)
            if sky is not None:
                bird.color = self.ambient_color(bird, sky)

    def ambient_color(self, bird, sky):
        '''
        De jour l oiseau est une silhouette sombre, de nuit un plumage clair
        eclaire par la lune : dans les deux cas il reste lisible sur le ciel.
        Puis on le fond dans le ciel selon sa distance (perspective aerienne).
        '''
        nuit = 1.0 - sky.light
        color = lerp_color(BIRD_COLOR, BIRD_COLOR_NIGHT, nuit)
        fond = sky.sky_color_at(bird.y)
        haze = (1.0 - self.depth) * BIRD_HAZE
        bird.beak_color = lerp_color(lerp_color(BEAK_COLOR, color, nuit * 0.8),
                                     fond, haze)
        return lerp_color(color, fond, haze)

    def respawn(self):
        'La nuee ressort de l autre cote, avec une nouvelle taille et vitesse'
        self.direction *= -1 if self.rng.random() < 0.35 else 1
        self.lead_x = self._spawn_x()
        self.speed = BIRD_SPEED * lerp(0.45, 1.0, self.depth) * self.rng.uniform(0.85, 1.2)
        for i, bird in enumerate(self.birds):
            dx, dy = self.formation_offset(i)
            bird.x = self.lead_x + dx
            bird.y = self.alt + dy
            bird.vx = bird.vy = 0.0

    def draw(self, screen):
        for bird in self.birds:
            bird.draw(screen)


class Birds:
    '''
    Chef d orchestre des nuees. Le nombre de nuees, leur profondeur et leur
    registre sont tires du morceau lui-meme : deux MIDI differents ne donnent
    pas la meme composition de ciel, mais un meme MIDI la redonne a l identique.

    Attributes:
        flocks (list[Flock]): les nuees, du plan le plus lointain au plus proche.
        pitch_lo, pitch_hi (int): registre utile du morceau (5e / 95e centile).

    Methods:
        update(dt, t, notes, sky, scroll_speed): avance toutes les nuees.
        draw(screen, plane): dessine les nuees d un plan de profondeur.
    '''

    def __init__(self, sync, nb_flocks=None):
        self.sync = sync
        pitches = sorted(n["pitch"] for n in sync.notes) or [60]
        self.pitch_lo = pitches[int(len(pitches) * 0.05)]
        self.pitch_hi = max(self.pitch_lo + 6, pitches[int(len(pitches) * 0.95)])

        # signature du morceau : meme MIDI = meme ciel
        moyenne = sum(pitches) / len(pitches)
        rng = random.Random(int(len(pitches) * 1000 + moyenne * 7))

        duree = max(1.0, getattr(sync, "duration", 30.0))
        densite = len(pitches) / duree
        if nb_flocks is None:
            nb_flocks = 2 if densite < 3 else (3 if densite < 8 else 4)

        # un morceau grave reste au loin, un morceau aigu vient au premier plan
        aigu = min(1.0, max(0.0, (moyenne - 48) / 30.0))
        planes = self.choose_planes(nb_flocks, aigu, rng)

        self.flocks = []
        span = (self.pitch_hi - self.pitch_lo) / nb_flocks
        for i, plane in enumerate(planes):
            depth = PLANE_DEPTH[plane] * rng.uniform(0.85, 1.15)
            lo = self.pitch_lo + span * i
            hi = self.pitch_lo + span * (i + 1) + (2 if i == nb_flocks - 1 else 0)
            nb_birds = rng.randint(5, 9) if plane == PLANE_FAR else rng.randint(3, 6)
            self.flocks.append(Flock(depth, nb_birds, lo, hi, self.band_map(lo, hi),
                                     direction=rng.choice((-1, -1, 1)), rng=rng))
        self.flocks.sort(key=lambda f: f.depth)

    def choose_planes(self, nb, aigu, rng):
        'Repartit les nuees dans la profondeur selon le registre du morceau'
        poids = [1.6 - aigu, 1.1, 0.4 + aigu]      # grave -> loin, aigu -> proche
        planes = [PLANE_FAR]                        # toujours une nuee lointaine
        if nb >= 3:
            planes.append(PLANE_MID)                # et un plan intermediaire
        while len(planes) < nb:
            planes.append(rng.choices([PLANE_FAR, PLANE_MID, PLANE_NEAR], poids)[0])
        rng.shuffle(planes)
        return planes

    def altitude(self, pitch):
        'Hauteur de note MIDI -> altitude a l ecran (aigu = haut)'
        t = (pitch - self.pitch_lo) / (self.pitch_hi - self.pitch_lo)
        t = max(0.0, min(1.0, t))
        return lerp(BIRD_Y_BOTTOM, BIRD_Y_TOP, t)

    def band_map(self, lo, hi, stretch=BIRD_BAND_STRETCH):
        '''
        Fabrique le mapping pitch -> altitude propre a une nuee. Son registre
        est etire sur une tranche de ciel plus large que sa part exacte, sinon
        une nuee cantonnee a 10 demi-tons ne bougerait presque pas.
        '''
        y_bas, y_haut = self.altitude(lo), self.altitude(hi)
        centre = (y_bas + y_haut) / 2
        y_bas = centre + (y_bas - centre) * stretch
        y_haut = centre + (y_haut - centre) * stretch

        def mapping(pitch):
            t = (pitch - lo) / (hi - lo) if hi > lo else 0.5
            t = max(0.0, min(1.0, t))
            return max(BIRD_Y_TOP, min(BIRD_Y_BOTTOM, lerp(y_bas, y_haut, t)))

        return mapping

    def update(self, dt, t, notes=(), sky=None, scroll_speed=0.0):
        energy = self.sync.energy(t) if t >= 0 else 0.0
        for flock in self.flocks:
            flock.update(dt, notes, energy, scroll_speed, sky)

    def draw(self, screen, plane):
        'A appeler trois fois dans la boucle : loin, moyen, proche'
        for flock in self.flocks:
            if flock.plane == plane:
                flock.draw(screen)