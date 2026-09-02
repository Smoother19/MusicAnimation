"""
Systeme de Lindenmayer : la grammaire qui fait pousser les plantes.

Un L-systeme est une grammaire formelle qui, contrairement a une grammaire
de Chomsky, reecrit TOUS les symboles d'un mot en parallele a chaque pas.
C'est ce parallelisme qui modelise une croissance : dans une plante toutes
les cellules se divisent en meme temps, pas l'une apres l'autre.

    axiome            X
    regle             X -> F[+X][-X]FX
    apres 1 pas       F[+X][-X]FX
    apres 2 pas       F[+F[+X][-X]FX][-F[+X][-X]FX]FF[+X][-X]FX

Le mot obtenu n'est pas encore un dessin : c'est une suite d'ordres pour
une tortue graphique, qui le transforme en segments. La meme grammaire
donne donc autant de plantes que d'interpretations de la tortue.

La version utilisee ici est STOCHASTIQUE : une regle peut avoir plusieurs
membres droits, tires au sort avec leurs poids. Deux plantes de la meme
espece ne sont donc jamais identiques, alors qu'un L-systeme deterministe
en donnerait une foret de clones.

Reference : Prusinkiewicz & Lindenmayer, *The Algorithmic Beauty of
Plants* (1990), figure 1.24 -- les six grammaires classiques dont
s'inspirent les especes de flowers.py.
"""

import math
import random


class LSystem:
    '''
    Une grammaire et son deroulement.

    axiom      : le mot de depart
    rules      : {symbole: production} ou {symbole: [(poids, production), ...]}
    angle      : l'angle de rotation en degres, lu par la tortue
    iterations : le nombre de reecritures paralleles
    '''

    def __init__(self, axiom, rules, angle=25.0, iterations=3):
        self.axiom = axiom
        self.rules = rules
        self.angle = angle
        self.iterations = iterations

    def _pick(self, productions, rng):
        'Tire un membre droit parmi les variantes d\'une regle stochastique.'
        if isinstance(productions, str):
            return productions
        total = sum(weight for weight, _ in productions)
        draw = rng.uniform(0, total)
        for weight, production in productions:
            draw -= weight
            if draw <= 0:
                return production
        return productions[-1][1]

    def expand(self, rng, iterations=None, max_length=4000):
        '''
        Le mot apres n reecritures paralleles.

        `max_length` est un garde-fou : le mot croit exponentiellement (x3
        a x4 par pas selon la grammaire), et une iteration de trop suffit a
        faire tomber la boucle de jeu a une image par seconde.
        '''
        n = self.iterations if iterations is None else iterations
        word = self.axiom

        for _ in range(n):
            out = []
            for symbol in word:
                productions = self.rules.get(symbol)
                out.append(self._pick(productions, rng) if productions else symbol)
            word = "".join(out)
            if len(word) > max_length:
                break

        return word


class Turtle:
    '''
    L'interprete geometrique du mot.

    Le mot ne dit rien de la taille ni de l'orientation : c'est la tortue
    qui les fixe, et deux tortues reglees differemment sur le meme mot
    donnent une herbe et un arbuste.

    Alphabet lu :
        F   avance en tracant un segment
        f   avance sans tracer
        + - tourne a gauche / a droite de `angle`
        [ ] empile / depile la position, l'orientation et l'echelle
        *   pose une fleur a la position courante
        X Y points de croissance, aucun effet visible

    Repere ecran : y croit vers le bas, donc un cap de -90 degres monte.
    '''

    def __init__(self, step=8.0, angle=25.0, width=3.0,
                 shrink=0.78, narrow=0.72, jitter=0.28, rng=None):
        self.step = step
        self.angle = math.radians(angle)
        self.width = width
        self.shrink = shrink          # raccourcissement du pas par niveau
        self.narrow = narrow          # affinement du trait par niveau
        self.jitter = jitter          # part d'aleatoire sur chaque rotation
        self.rng = rng or random.Random()

    def _turn(self, sign):
        'Rotation bruitee : sans bruit, toutes les fourches sont identiques.'
        j = 1.0 + self.jitter * (2 * self.rng.random() - 1)
        return sign * self.angle * j

    def run(self, word, heading=-math.pi / 2):
        '''
        Deroule le mot et rend (segments, fleurs).

        segments : [((x0, y0), (x1, y1), largeur, profondeur)]
        fleurs   : [(x, y, profondeur)]  -- les * explicites du mot

        Les deux listes sont en coordonnees locales, racine en (0, 0).
        '''
        x, y = 0.0, 0.0
        depth = 0
        stack = []
        segments, blooms = [], []

        for symbol in word:
            if symbol in "FG":
                length = self.step * self.shrink ** depth
                nx = x + math.cos(heading) * length
                ny = y + math.sin(heading) * length
                segments.append(((x, y), (nx, ny),
                                 max(1.0, self.width * self.narrow ** depth),
                                 depth))
                x, y = nx, ny
            elif symbol == "f":
                x += math.cos(heading) * self.step * self.shrink ** depth
                y += math.sin(heading) * self.step * self.shrink ** depth
            elif symbol == "+":
                heading += self._turn(-1)
            elif symbol == "-":
                heading += self._turn(+1)
            elif symbol == "[":
                stack.append((x, y, heading, depth))
                depth += 1
            elif symbol == "]":
                if stack:
                    x, y, heading, depth = stack.pop()
            elif symbol == "*":
                blooms.append((x, y, depth))

        return segments, blooms


def tips(segments, grid=1.5):
    '''
    Les extremites libres : celles ou aucun autre segment ne repart.

    C'est la ou une plante fleurit. On pourrait le declarer dans la
    grammaire avec un symbole *, mais le deduire de la geometrie marche
    pour n'importe quelle grammaire, y compris celles qui n'ont pas prevu
    de fleurs.
    '''
    starts = {(round(a[0] / grid), round(a[1] / grid)) for a, _, _, _ in segments}
    out = []
    for _, b, _, depth in segments:
        if (round(b[0] / grid), round(b[1] / grid)) not in starts:
            out.append((b[0], b[1], depth))
    return out
