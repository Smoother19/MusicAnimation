import math
import random
import pygame as ui
from shapes import *
from config import *


def lerp(a, b, t):
    return a + (b - a) * t


def lerp_color(c1, c2, t):
    t = max(0.0, min(1.0, t))
    return tuple(int(lerp(a, b, t)) for a, b in zip(c1, c2))


def smoothstep(edge0, edge1, x):
    '''
    Interpolation douce entre 0 et 1 (derivees nulles aux bords)
    '''
    if edge1 == edge0:
        return 0.0
    t = max(0.0, min(1.0, (x - edge0) / (edge1 - edge0)))
    return t * t * (3 - 2 * t)


def draw_disc(screen, x, y, radius, color, parts=SKY_BODY_PARTS):
    '''
    Disque plat en eventail de triangles. On court-circuite facet() pour que les
    halos et le croissant de lune restent lisses
    '''
    points = [(x + radius * math.cos(math.tau * i / parts),
               y + radius * math.sin(math.tau * i / parts)) for i in range(parts)]
    for i in range(parts):
        ui.draw.polygon(screen, color, [(x, y), points[i], points[(i + 1) % parts]])
    STATS["triangles"] += parts


class CelestialBody(Circle):
    '''
    class CelestialBody

    Attributes:
        base_radius (float): Rayon au repos, avant pulsation.
        halo_color (tuple): Couleur du halo dessine autour de l'astre.
        elevation (float): Hauteur normalisee dans le ciel, -1 (nadir) a 1 (zenith).
        pulse (float): Energie de pulsation courante, alimentee par les notes.
        spin (float): Angle de rotation courant des rayons.

    Methods:
        set_phase(phase): Place l'astre sur son arc a partir de la phase du cycle.
        hit(strength): Injecte de l'energie de pulsation (appele sur une note).
        update(dt): Fait decroitre la pulsation et met a jour le rayon.
        draw_halo(screen, sky_color, rays, ray_energy): Dessine halo et rayons.
    '''

    def __init__(self, radius, color, halo_color, parts=SKY_BODY_PARTS,
                 halo_spread=0.9, halo_strength=1.0):
        super().__init__(0, 0, radius, color, parts)
        self.base_radius = radius
        self.halo_color = halo_color
        self.halo_spread = halo_spread
        self.halo_strength = halo_strength
        self.elevation = 0.0
        self.pulse = 0.0
        self.spin = 0.0
        self.visible = False

    def set_phase(self, phase):
        '''
        phase 0.0 = lever | 0.25 = zenith | 0.5 = coucher | 0.75 = minuit
        '''
        angle = math.tau * phase
        self.elevation = math.sin(angle)
        self.x = SKY_CENTER_X - SKY_RADIUS_X * math.cos(angle)
        self.y = HORIZON_Y - SKY_RADIUS_Y * self.elevation
        self.visible = self.elevation > -0.20

    def hit(self, strength=0.35):
        '''
        Une note vient de commencer : l'astre gonfle d'un coup
        '''
        self.pulse = min(1.5, self.pulse + strength)

    def update(self, dt):
        self.pulse *= math.exp(-dt * SKY_PULSE_DECAY)
        self.spin += dt * 0.25
        self.radius = self.base_radius * (1.0 + 0.20 * self.pulse)
        self.width = self.height = self.radius * 2

    def draw_halo(self, screen, sky_color, rays=0, ray_energy=0.0):
        '''
        Halo concentrique + rayons triangulaires optionnels (soleil)
        '''
        for i in range(SKY_HALO_LAYERS, 0, -1):
            k = i / SKY_HALO_LAYERS
            r = self.radius * (1.0 + self.halo_spread * k * (1.0 + 0.5 * self.pulse))
            mix = 1.0 - (1.0 - (k ** 0.6) * 0.92) * self.halo_strength
            color = lerp_color(self.halo_color, sky_color, mix)
            draw_disc(screen, self.x, self.y, r, color, self.parts)

        if rays <= 0:
            return

        length = self.radius * (0.45 + 1.1 * ray_energy + 0.5 * self.pulse)
        half = math.tau / rays * 0.16
        for i in range(rays):
            a = self.spin + math.tau * i / rays
            base_1 = (self.x + math.cos(a - half) * self.radius,
                      self.y + math.sin(a - half) * self.radius)
            base_2 = (self.x + math.cos(a + half) * self.radius,
                      self.y + math.sin(a + half) * self.radius)
            tip = (self.x + math.cos(a) * (self.radius + length),
                   self.y + math.sin(a) * (self.radius + length))
            TrianglePoints(base_1, base_2, tip, 0, 0,
                           lerp_color(self.halo_color, sky_color, 0.25)).draw(screen)


class Star(Circle):
    '''
    Etoile scintillante, visible uniquement quand la nuit tombe.

    Attributes:
        phase (float): Dephasage du scintillement, propre a chaque etoile.
        speed (float): Vitesse du scintillement.
        flash (float): Bonus de luminosite injecte par une note aigue.
    '''

    def __init__(self):
        size = random.uniform(1.6, 3.6)
        super().__init__(random.uniform(0, SCREEN_WIDTH),
                         random.uniform(10, HORIZON_Y - 60),
                         size, (255, 255, 255), 4)
        self.base_radius = size
        self.phase = random.uniform(0, math.tau)
        self.speed = random.uniform(1.5, 4.0)
        self.flash = 0.0

    def update(self, dt):
        self.phase += self.speed * dt
        self.flash *= math.exp(-dt * 2.5)
        self.radius = self.base_radius * (1.0 + 0.9 * self.flash)

    def draw_at(self, screen, night, sky_color):
        brightness = (0.55 + 0.45 * math.sin(self.phase)) * night
        brightness = min(1.0, brightness + self.flash * night)
        if brightness < 0.05:
            return
        self.color = lerp_color(sky_color, (255, 255, 255), brightness)
        self.draw(screen)


class Sky:
    '''
    Cycle jour/nuit complet : degrade de ciel, etoiles, soleil et lune,
    le tout pilote par la musique.

    Attributes:
        sync (SyncMusic): Source des notes et de la densite musicale.
        cycle_duration (float): Duree en secondes de musique d'un cycle complet.
        phase (float): Position dans le cycle, 0.0 a 1.0.
        light (float): Facteur de jour, 0.0 (nuit noire) a 1.0 (plein jour).
        energy (float): Densite musicale normalisee, 0.0 a 1.0.

    Methods:
        update(dt, t, notes): Avance le cycle et reagit aux notes commencees.
        draw(screen): Dessine le ciel, les etoiles et les astres.
        sky_color_at(y): Couleur du degrade a une hauteur donnee.
    '''

    def __init__(self, sync, cycle_duration=None, cycles=SKY_CYCLES_PER_TRACK,
                 nb_stars=SKY_NB_STARS, reactive=True):
        self.sync = sync
        self.reactive = reactive

        if cycle_duration is None:
            duration = getattr(sync, "duration", 0.0)
            cycle_duration = duration / cycles if duration > 1.0 else CYCLE_DURATION
        self.cycle_duration = max(4.0, cycle_duration)

        self.phase = SKY_START_PHASE
        self.prev_t = 0.0
        self.light = 1.0
        self.energy = 0.0

        self.sun = CelestialBody(SUN_RADIUS, SUN_COLOR, SUN_HALO)
        self.moon = CelestialBody(MOON_RADIUS, MOON_COLOR, MOON_HALO,
                                  halo_spread=0.55, halo_strength=0.45)
        self.sun.set_phase(self.phase)
        self.moon.set_phase(self.phase + 0.5)

        self.stars = [Star() for _ in range(nb_stars)]
        self.top_color = DAY_TOP
        self.bottom_color = DAY_BOTTOM

    @property
    def is_night(self):
        return self.light < 0.35

    def update(self, dt, t, notes=()):
        '''
        dt    : temps reel ecoule (s)
        t     : position dans la musique (s), negatif si la lecture n'a pas commence
        notes : notes demarrees sur cette frame (retour de SyncMusic.update)
        '''
        if t >= 0:
            dt_music = max(0.0, min(0.25, t - self.prev_t))
            self.prev_t = t
            factor = self.sync.speed_factor(t) if self.reactive else 1.0
            self.energy = self.sync.energy(t) if self.reactive else 0.0
        else:
            dt_music, factor = dt, 1.0

        # la musique dense accelere la course du soleil
        self.phase = (self.phase + dt_music / self.cycle_duration * factor) % 1.0
        self.sun.set_phase(self.phase)
        self.moon.set_phase(self.phase + 0.5)

        for note in notes:
            body = self.sun if self.sun.elevation >= self.moon.elevation else self.moon
            body.hit(0.10 + 0.30 * min(1.0, self.energy + 0.3))
            if note["pitch"] > 70 and self.is_night:
                random.choice(self.stars).flash = 1.0

        self.sun.update(dt)
        self.moon.update(dt)
        for star in self.stars:
            star.update(dt)

        self.compute_colors()

    def compute_colors(self):
        '''
        Melange les trois palettes (nuit, jour, crepuscule) selon la hauteur du soleil
        '''
        e = self.sun.elevation
        day = smoothstep(-0.05, 0.30, e)
        dusk = math.exp(-(e / 0.22) ** 2)

        self.light = day
        top = lerp_color(NIGHT_TOP, DAY_TOP, day)
        bottom = lerp_color(NIGHT_BOTTOM, DAY_BOTTOM, day)
        self.top_color = lerp_color(top, DUSK_TOP, dusk * 0.75)
        self.bottom_color = lerp_color(bottom, DUSK_BOTTOM, dusk * 0.85)

    def tint(self, color, strength=0.55):
        '''
        Assombrit une couleur selon l'heure : a utiliser pour les montagnes,
        les nuages ou le train, afin que toute la scene suive le cycle
        '''
        return lerp_color(lerp_color(color, AMBIENT_NIGHT, strength), color, self.light)

    def sky_color_at(self, y):
        return lerp_color(self.top_color, self.bottom_color,
                          max(0.0, min(1.0, y / HORIZON_Y)))

    def draw_gradient(self, screen):
        '''
        Degrade en bandes de 2 triangles. On dessine les polygones directement
        pour eviter le facettage de TriangularShape, qui ferait apparaitre les
        coutures entre les bandes.
        '''
        step = SCREEN_HEIGHT / SKY_BANDS
        for i in range(SKY_BANDS):
            y_0 = i * step
            y_1 = (i + 1) * step + 1
            color = self.sky_color_at((y_0 + y_1) / 2)
            top_left, top_right = (0, y_0), (SCREEN_WIDTH, y_0)
            bottom_left, bottom_right = (0, y_1), (SCREEN_WIDTH, y_1)
            ui.draw.polygon(screen, color, [top_left, top_right, bottom_left])
            ui.draw.polygon(screen, color, [top_right, bottom_right, bottom_left])
            STATS["triangles"] += 2

    def draw_moon(self, screen):
        '''
        Dessine la lune puis creuse un croissant en repeignant un disque decale
        avec la couleur du ciel
        '''
        sky_color = self.sky_color_at(self.moon.y)
        self.moon.draw_halo(screen, sky_color)
        self.moon.draw(screen)

        offset = self.moon.radius * MOON_CRESCENT
        if offset > 0.05:
            draw_disc(screen, self.moon.x - offset, self.moon.y - offset * 0.35,
                      self.moon.radius * 0.97, sky_color, self.moon.parts)

    def draw(self, screen):
        self.draw_gradient(screen)

        night = 1.0 - self.light
        if night > 0.05:
            for star in self.stars:
                star.draw_at(screen, night, self.sky_color_at(star.y))

        if self.moon.visible:
            self.draw_moon(screen)

        if self.sun.visible:
            sky_color = self.sky_color_at(self.sun.y)
            rays = SUN_MIN_RAYS + int(self.energy * (SUN_MAX_RAYS - SUN_MIN_RAYS))
            self.sun.draw_halo(screen, sky_color, rays, self.energy)
            self.sun.draw(screen)