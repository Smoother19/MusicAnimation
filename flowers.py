"""
La prairie sous la voie : des plantes engendrees par un L-systeme.

Trois idees se combinent ici.

1. La FORME vient d'une grammaire (lsystem.py). Quatre especes, quatre
   jeux de regles inspires des grammaires classiques de Prusinkiewicz.
   Chaque plante tire ses variantes au sort, donc aucune n'est le clone
   d'une autre, mais toujours avec un generateur graine par le morceau :
   le meme MP3 refait exactement la meme prairie.

2. Le SEMIS vient de la partition. Une plante par note retenue, plantee a
   l'abscisse ou passe le temps musical de cette note. Comme la voie lit
   la meme horloge (CurvesTrack.time_at), la fleur reste collee a son
   bout de terrain : elle defile avec lui, sans deriver. L'espece vient
   du registre de la note, la couleur de sa fleur de la meme echelle
   grave -> aigu que les marqueurs.

3. La TAILLE vient du relief. La place disponible sous la voie est
   exactement SCREEN_HEIGHT moins la hauteur de la voie a cet instant
   musical -- une constante, puisque la voie est elle-meme une fonction
   du temps musical. Chaque plante est donc calculee une fois pour toutes
   a la plantation ; a l'image, il ne reste qu'une translation.

Le seul travail par image est le balancement, une deformation en cisaille
dont l'amplitude suit la bande aigue du morceau.
"""

import bisect
import math
import random

import pygame as ui

from config import (SCREEN_WIDTH, SCREEN_HEIGHT, NOTE_LOW, NOTE_HIGH,
                    FLOWER_SPACING, FLOWER_MARGIN, FLOWER_MAX_DRAWN,
                    FLOWER_SWAY, FLOWER_PETALS, FLOWER_ACCENT,
                    FLOWER_CLEARANCE,
                    FLOWER_STEM_COLORS, FLOWER_BLOOM_TINTS, FLOWER_FILL)
from lsystem import LSystem, Turtle, tips
from shapes import TriangularShape, STATS, facet


# --- les especes --------------------------------------------------------
#
# Une espece par quart de registre : la note grave seme de l'herbe, la note
# aigue une fougere. Les grammaires viennent de *The Algorithmic Beauty of
# Plants*, figure 1.24, avec un second membre droit ajoute a chaque regle
# pour les rendre stochastiques.

# Deux strates, pour que la prairie ait une profondeur.
#
#   fond   : l'accompagnement (piano). Serre, court, sombre -- c'est la
#            masse d'herbe qui remplit la bande.
#   devant : la melodie (trompette). Plus rare, plus haut, plus clair, et
#            c'est lui qui porte les corolles.
#
# `shade` separe les deux plans : le devant est ECLAIRCI, le fond a peine
# assombri. L'inverse -- noyer le fond dans la couleur du sol, comme le
# veut la perspective aerienne -- ne marche pas ici : le sol est presque
# noir, et la strate entiere disparaissait.
STRATA = {
    "fond":   {"spacing": 0.11, "fill": (0.22, 0.50), "shade": -0.18,
               "species": (0, 1), "iterations": 2, "bloom_scale": 0.0,
               "leaves": 0.7},
    "devant": {"spacing": 0.50, "fill": (0.55, 0.95), "shade": 0.30,
               "species": (2, 3), "iterations": None, "bloom_scale": 1.7,
               "leaves": 0.85},
}


SPECIES = (
    {   # 0 -- herbe : peu de fourches, presque verticale, une seule tete
        "name": "herbe",
        "rules": {"X": [(2, "F[+X]F[-X]X"), (1, "F[-X]FX"), (1, "F[+X]FX")]},
        "axiom": "X", "angle": 12.0, "iterations": 3,
        "step": 9.0, "width": 2.4, "shrink": 0.90, "narrow": 0.82,
        "blooms": 1, "bloom_size": 2.0,
    },
    {   # 1 -- ombelle : la grammaire buissonnante, tetes en bouquet
        "name": "ombelle",
        "rules": {"F": [(2, "FF-[-F+F]+[+F-F]"), (1, "F-[-F+F]+[+F]")]},
        "axiom": "F", "angle": 22.5, "iterations": 2,
        "step": 9.0, "width": 2.8, "shrink": 0.82, "narrow": 0.74,
        "blooms": 3, "bloom_size": 2.8,
    },
    {   # 2 -- marguerite : tige nette, fleurs au bout de chaque branche
        "name": "marguerite",
        "rules": {"X": [(2, "F[+X]F[-X]+X"), (1, "F[-X]F[+X]-X"), (1, "F[+X]FX")]},
        "axiom": "X", "angle": 20.0, "iterations": 3,
        "step": 9.0, "width": 3.2, "shrink": 0.84, "narrow": 0.72,
        "blooms": 4, "bloom_size": 4.4,
    },
    {   # 3 -- fougere : tres ramifiee, ouverte, feuillage plutot que fleur
        "name": "fougere",
        "rules": {"X": [(2, "F-[[X]+X]+F[+FX]-X"), (1, "F-[[X]+X]+FX"),
                        (1, "F-[[X]+X]+F[-FX]+X")],
                  "F": "FF"},
        "axiom": "X", "angle": 22.5, "iterations": 2,
        "step": 7.0, "width": 2.6, "shrink": 0.86, "narrow": 0.76,
        "blooms": 3, "bloom_size": 3.2,
    },
)

def lerp_rgb(a, b, k):
    k = max(0.0, min(1.0, k))
    return tuple(int(u + (v - u) * k) for u, v in zip(a, b))


class Plant(TriangularShape):
    '''
    Une plante : sa geometrie locale, calculee une fois.

    Racine en (0, 0), la tige monte vers les y negatifs. `draw` translate
    l'ensemble a l'ecran et applique le balancement, qui est une simple
    cisaille : plus un point est haut sur la plante, plus il se decale.
    '''

    def __init__(self, species, rng, height, stem_color, bloom_color,
                 bloom_size=1.0, leaves=0.7, iterations=None, tilt=0.0):
        super().__init__(0, 0, 0, height, stem_color)
        self.species = species
        self.bloom_color = bloom_color

        word = LSystem(species["axiom"], species["rules"], species["angle"],
                       iterations or species["iterations"]).expand(rng)
        turtle = Turtle(step=species["step"], angle=species["angle"],
                        width=species["width"], shrink=species["shrink"],
                        narrow=species["narrow"], rng=rng)
        # Une prairie ou toutes les tiges sont verticales se lit comme une
        # rangee de piquets : chaque plante part legerement de travers.
        segments, marked = turtle.run(word, heading=-math.pi / 2 + tilt)

        if not segments:
            self.stems, self.leaves, self.blooms, self.height = [], [], [], 1.0
            return

        # Mise a l'echelle : la grammaire ne connait pas la place
        # disponible, la plante est ramenee a la hauteur qu'on lui donne.
        top = min(min(a[1], b[1]) for a, b, _, _ in segments)
        k = height / max(1.0, -top)

        self.stems = [((a[0] * k, a[1] * k), (b[0] * k, b[1] * k),
                       max(1.0, w * min(1.4, k)), d)
                      for a, b, w, d in segments]

        # Les feuilles : un triangle pose en travers d'un segment sur deux
        # a partir du premier embranchement. Une tige nue se lit comme une
        # brindille d'hiver ; c'est le feuillage qui fait la prairie, et il
        # ne coute qu'un triangle par feuille.
        self.leaves = []
        for i, (a, b, w, d) in enumerate(self.stems):
            if (d < 1 and -a[1] < self.height * 0.35) or i % 2 \
                    or rng.random() > leaves:
                continue
            mx, my = (a[0] + b[0]) / 2, (a[1] + b[1]) / 2
            dx, dy = b[0] - a[0], b[1] - a[1]
            n = math.hypot(dx, dy) or 1.0
            side = 1 if i % 4 == 0 else -1
            ex, ey = -dy / n * side, dx / n * side
            L = n * rng.uniform(0.40, 0.70)
            self.leaves.append([
                (mx, my),
                (mx + ex * L * 0.30 + dx / n * L * 0.55,
                 my + ey * L * 0.30 + dy / n * L * 0.55),
                (mx + dx / n * L * 1.15 + ex * L * 0.05,
                 my + dy / n * L * 1.15 + ey * L * 0.05)])

        heads = marked or tips(segments)
        heads.sort(key=lambda p: p[1])            # les plus hautes d'abord
        heads = heads[:species["blooms"]] if bloom_size > 0 else []
        radius = species["bloom_size"] * bloom_size
        self.blooms = [(x * k, y * k, radius * (0.7 + 0.3 * rng.random()))
                       for x, y, _ in heads]

        self.height = max(1.0, height)
        self.phase = rng.uniform(0, math.tau)
        self._bake()

    def _bake(self):
        '''
        Prepare les polygones une fois pour toutes.

        Chaque sommet est range sous la forme (x, y, k) ou k est deja le
        poids de balancement de ce point -- le carre de sa hauteur relative.
        A l'image il ne reste qu'une addition par coordonnee ; sans ce
        pre-calcul, la prairie refaisait onze mille divisions et racines
        carrees par image, et c'est la, pas dans le remplissage, que
        passaient les sept images par seconde qu'elle coutait.
        '''
        h = self.height

        def bake(points):
            return [(x, y, min(1.0, -y / h) ** 2) for x, y in points]

        self.polygons = []            # (groupe, index de teinte, sommets)
        for i, (a, b, w, _) in enumerate(self.stems):
            self.polygons.append(("stem", i, bake(self._quad(a, b, w))))
        for i, leaf in enumerate(self.leaves):
            self.polygons.append(("leaf", i, bake(leaf)))
        for j, (x, y, r) in enumerate(self.blooms):
            star = []
            for i in range(2 * FLOWER_PETALS):
                a = math.pi * i / FLOWER_PETALS
                k = r if i % 2 == 0 else r * 0.42
                star.append((x + math.cos(a) * k, y + math.sin(a) * k))
            self.polygons.append(("bloom", j, bake(star)))
            if r > 3.0:
                self.polygons.append(("heart", j, bake([
                    (x - r * 0.30, y + r * 0.18),
                    (x, y - r * 0.36),
                    (x + r * 0.30, y + r * 0.18)])))

        # Nombre de triangles reellement dessines, pour le compteur.
        self.n_triangles = (2 * len(self.stems) + len(self.leaves)
                            + (2 * FLOWER_PETALS + 1) * len(self.blooms))

    # --- geometrie ------------------------------------------------------

    def _quad(self, a, b, w):
        'Un segment epais : deux triangles, comme tout le reste du projet.'
        dx, dy = b[0] - a[0], b[1] - a[1]
        n = math.hypot(dx, dy) or 1.0
        px, py = -dy / n * w * 0.5, dx / n * w * 0.5
        return ((a[0] + px, a[1] + py), (a[0] - px, a[1] - py),
                (b[0] - px, b[1] - py), (b[0] + px, b[1] + py))

    def _petals(self, x, y, r):
        '''
        Une corolle en etoile : un eventail de triangles dont le rayon
        alterne. A cette taille (4 a 8 px) une etoile se lit comme une
        fleur la ou un disque se lirait comme un point.
        '''
        out = []
        n = FLOWER_PETALS
        for i in range(n):
            a0 = math.tau * i / n
            a1 = math.tau * (i + 0.5) / n
            a2 = math.tau * (i + 1) / n
            out.append([(x, y),
                        (x + math.cos(a0) * r, y + math.sin(a0) * r),
                        (x + math.cos(a1) * r * 0.45, y + math.sin(a1) * r * 0.45)])
            out.append([(x, y),
                        (x + math.cos(a1) * r * 0.45, y + math.sin(a1) * r * 0.45),
                        (x + math.cos(a2) * r, y + math.sin(a2) * r)])
        return out

    def list_triangles(self):
        'Coordonnees locales, racine en (0, 0) -- pour STATS et les tests.'
        out = []
        for a, b, w, _ in self.stems:
            p = self._quad(a, b, w)
            out.append([p[0], p[1], p[2]])
            out.append([p[0], p[2], p[3]])
        out.extend(list(leaf) for leaf in self.leaves)
        for x, y, r in self.blooms:
            out.extend(self._petals(x, y, r))
        return out

    # --- rendu ----------------------------------------------------------

    def draw(self, screen, ox=0, oy=0, angle=0, pivot=None, sway=0.0,
             palette=None):
        '''
        Pose la plante en (ox, oy) et la fait ployer de `sway` pixels a son
        sommet. La base ne bouge pas, la tete bouge tout.

        Le modele reste triangulaire -- list_triangles() en fait foi -- mais
        le rendu regroupe les deux triangles d'un segment en un quadrilatere
        et les dix d'une corolle en une etoile : meme geometrie, trois fois
        moins d'appels a pygame.

        `palette` est le dictionnaire de couleurs deja teinte par la saison
        et par l'heure, prepare une seule fois par FlowerField pour toutes
        les plantes de la meme strate.
        '''
        palette = palette or self._palette()

        for group, i, points in self.polygons:
            ui.draw.polygon(screen, palette[group][i % 8],
                            [(x + ox + sway * k, y + oy) for x, y, k in points])

        STATS["triangles"] += self.n_triangles
        return self.n_triangles

    def _palette(self):
        'Palette de secours, quand la plante est dessinee seule.'
        return palette_for(self.color, self.bloom_color)


def palette_for(stem, bloom):
    '''
    Les quatre familles de teintes d'une strate, chacune declinee en huit
    facettes.

    Le facettage est le meme que partout ailleurs dans le projet : deux
    triangles voisins ne recoivent jamais exactement la meme teinte, ce qui
    donne du relief a un aplat. Le calculer une fois par strate plutot
    qu'une fois par polygone economise, a soixante images par seconde,
    quelques dizaines de milliers de conversions de couleur.
    '''
    foliage = lerp_rgb(stem, (150, 200, 120), 0.22)
    heart = lerp_rgb(bloom, (255, 245, 210), 0.6)
    return {
        "stem":  [facet(stem, i) for i in range(8)],
        "leaf":  [facet(foliage, i) for i in range(8)],
        "bloom": [facet(bloom, i) for i in range(8)],
        "heart": [heart] * 8,
    }


class FlowerField:
    '''
    Le semis complet, tire de la partition une fois pour toutes.

    Les plantes sont rangees par temps musical croissant. A chaque image
    on ne reveille que la tranche visible, trouvee par dichotomie : le
    cout ne depend pas de la longueur du morceau.

    Le semis boucle sur la duree du morceau, comme le relief de la voie :
    quand la musique s'arrete la prairie continue de defiler au lieu de
    se vider.
    '''

    def __init__(self, sync, track, seed=0, spacing=FLOWER_SPACING,
                 fill=FLOWER_FILL, max_drawn=FLOWER_MAX_DRAWN):
        self.sync = sync
        self.track = track
        self.max_drawn = max_drawn
        self.season = 0
        self.time = 0.0

        self.period = max(1.0, sync.duration)
        self.plants = []
        self.times = []
        self._sow(seed, spacing, fill)
        print(f"prairie : {len(self.plants)} plantes semees")

    # --- semis ----------------------------------------------------------

    def _sow(self, seed, spacing, fill):
        '''
        Une plante par note retenue, repartie sur les deux strates.

        La piste decide de la strate : l'accompagnement fait l'herbe de
        fond, la melodie les fleurs de devant. Le registre decide de
        l'espece. Le relief decide de la taille. Rien n'est tire au sort
        sauf les variantes de la grammaire, et elles le sont sur un
        generateur graine par le morceau.

        `spacing` est un espacement MINIMAL en secondes de musique, par
        strate : sans lui un passage dense planterait quarante tiges sur
        trente pixels.
        '''
        rng = random.Random(seed)
        last = {name: -1e9 for name in STRATA}

        # Quand le MIDI n'a qu'une piste -- c'est le cas des transcriptions
        # mono-instrument -- la melodie ne peut pas designer le premier
        # plan. Le registre prend le relais : le tiers aigu fleurit.
        by_track = any(n["instrument"] == FLOWER_ACCENT for n in self.sync.notes)

        for note in self.sync.notes:
            t = note["start"]
            if by_track:
                front = note["instrument"] == FLOWER_ACCENT
            else:
                front = self.sync.ratio(note) > 0.66
            layer = "devant" if front else "fond"
            rules = STRATA[layer]
            gap = rules["spacing"] * (spacing / FLOWER_SPACING)
            if t - last[layer] < gap:
                continue
            last[layer] = t

            r = self.sync.ratio(note)
            choices = rules["species"]
            species = SPECIES[choices[min(len(choices) - 1, int(r * len(choices)))]]

            # Place disponible sous la voie a cet instant musical. Elle ne
            # bouge jamais : la voie est une fonction du temps, pas du
            # temps ecoule.
            y_track = self.track.height_at_time(t)
            room = SCREEN_HEIGHT - y_track - FLOWER_CLEARANCE
            if room < 30:
                continue

            lo, hi = rules["fill"]
            height = max(16.0, room * rng.uniform(lo, hi) * fill / FLOWER_FILL)
            bloom = tuple(int(a + (b - a) * r) for a, b in zip(NOTE_LOW, NOTE_HIGH))

            plant = Plant(species, rng, height,
                          stem_color=FLOWER_STEM_COLORS[0],
                          bloom_color=bloom,
                          bloom_size=rules["bloom_scale"] * (0.8 + 0.5 * r),
                          leaves=rules["leaves"],
                          iterations=rules["iterations"],
                          tilt=rng.uniform(-0.24, 0.24))
            # Enracinee sous le bord de l'ecran : une tige coupee net par
            # le bas se lit comme une herbe, pas comme un objet flottant.
            plant.root_y = SCREEN_HEIGHT + rng.uniform(2.0, 16.0)
            plant.wind = rng.uniform(0.6, 1.4)
            plant.shade = rules["shade"]
            self.plants.append((t, plant))

        # Le fond d'abord : il doit passer derriere les fleurs de devant.
        self.plants.sort(key=lambda row: row[0])
        self.times = [t for t, _ in self.plants]
        self.plants = [p for _, p in self.plants]

    # --- lecture --------------------------------------------------------

    def visible(self, margin=FLOWER_MARGIN):
        '''
        Les plantes dont l'abscisse tombe dans l'ecran, avec cette
        abscisse. Trouvees par dichotomie sur la fenetre temporelle que
        l'ecran couvre, en tenant compte du bouclage du morceau.
        '''
        if not self.times:
            return

        a = self.track.time_at(-margin)
        b = self.track.time_at(SCREEN_WIDTH + margin)
        lo, hi = (a, b) if a <= b else (b, a)

        first = math.floor(lo / self.period)
        last = math.floor(hi / self.period)
        drawn = 0

        for turn in range(first, last + 1):
            shift = turn * self.period
            i = bisect.bisect_left(self.times, lo - shift)
            j = bisect.bisect_right(self.times, hi - shift)
            for k in range(i, j):
                if drawn >= self.max_drawn:
                    return
                yield self.plants[k], self.track.x_at(self.times[k] + shift)
                drawn += 1

    # --- boucle ---------------------------------------------------------

    def update(self, dt, level=0.0, season=0):
        '''
        level  : energie de la bande aigue (sync.band(t, 2)), 0 a 1
        season : indice de saison, pour la palette des tiges
        '''
        self.time += dt
        self.level = max(0.0, min(1.0, level))
        self.season = season % len(FLOWER_STEM_COLORS)

    def draw(self, screen, sky=None):
        '''
        A appeler APRES CurvesTrack.draw : la prairie se pose sur le sol,
        qui la recouvrirait sinon.
        '''
        stem = FLOWER_STEM_COLORS[self.season]
        if sky is not None:
            stem = sky.tint(stem, 0.65)
        season_tint, season_mix = FLOWER_BLOOM_TINTS[self.season]

        amplitude = FLOWER_SWAY * (0.25 + 0.75 * getattr(self, "level", 0.0))

        palettes = {}

        for plant, x in self.visible():
            sway = amplitude * plant.wind * math.sin(
                self.time * 1.7 * plant.wind + plant.phase + x * 0.006)

            key = (plant.shade, plant.bloom_color, self.season)
            palette = palettes.get(key)
            if palette is None:
                k = plant.shade
                tone = (lerp_rgb(stem, (150, 205, 110), k) if k > 0
                        else lerp_rgb(stem, (18, 34, 30), -k))
                bloom = lerp_rgb(plant.bloom_color, season_tint, season_mix)
                if sky is not None:
                    bloom = sky.tint(bloom, 0.5)
                palette = palettes[key] = palette_for(tone, bloom)

            plant.draw(screen, ox=x, oy=plant.root_y, sway=sway,
                       palette=palette)
