import pygame

from config import (SCREEN_WIDTH, SCREEN_HEIGHT, MARGIN, RAIL_Y,
                    BACKGROUND, GROUND, RAIL, SPEED)
from shapes import Rectangle, Circle, STATS, shade
from train_view import TrainView

pygame.init()
screen = pygame.display.set_mode((SCREEN_WIDTH, SCREEN_HEIGHT))
pygame.display.set_caption("Train generatif")
clock = pygame.time.Clock()
font = pygame.font.SysFont("consolas", 16)


# ---------------------------------------------------------------- fumee ----

class Smoke:
    """Bouffees de fumee emises par la cheminee. Uniquement des triangles."""

    def __init__(self, color=(150, 150, 160)):
        self.puffs = []
        self.color = color
        self._cooldown = 0.0

    def emit(self, pos, speed, dt):
        if pos is None:
            return
        self._cooldown -= dt
        if self._cooldown <= 0 and speed > 5:
            self.puffs.append([pos[0], pos[1], 4.0, 0.0])
            self._cooldown = max(0.05, 0.5 - speed / 400.0)

    def update(self, dt, speed):
        for p in self.puffs:
            p[0] -= (18 + speed * 0.35) * dt      # derive vers l'arriere
            p[1] -= 26 * dt                       # monte
            p[2] += 9 * dt                        # grossit
            p[3] += dt                            # age
        self.puffs = [p for p in self.puffs if p[3] < 2.6]

    def draw(self, surface):
        for x, y, r, age in self.puffs:
            k = max(0.25, 1.0 - age / 2.6)
            Circle(x, y, r, shade(self.color, 0.45 + 0.55 * k), 7).draw(surface)


# ---------------------------------------------------------------- decor ----

def draw_scene(surface):
    surface.fill(BACKGROUND)
    Rectangle(SCREEN_WIDTH / 2, RAIL_Y + (SCREEN_HEIGHT - RAIL_Y) / 2,
              SCREEN_WIDTH, SCREEN_HEIGHT - RAIL_Y, GROUND).draw(surface)
    Rectangle(SCREEN_WIDTH / 2, RAIL_Y + 2, SCREEN_WIDTH, 4, RAIL).draw(surface)


def hud(surface, train, tris):
    txt = (f"seed {train.seed}   {train.speed:5.0f} px/s   "
           f"{len(train.shapes)} formes   {tris} triangles   "
           f"R nouvelle seed   <- ->  seed +-1   HAUT/BAS vitesse   ESPACE stop")
    surface.blit(font.render(txt, True, (150, 158, 175)), (14, 12))


# ----------------------------------------------------------------- main ----

train = TrainView(seed=32, x=0, y=0)
train.set_speed(SPEED, instant=True)
smoke = Smoke()
scroll = True                      # False = train fige, on voit la silhouette

running = True
while running:
    dt = clock.tick(60) / 1000.0

    for event in pygame.event.get():
        if event.type == pygame.QUIT:
            running = False
        elif event.type == pygame.KEYDOWN:
            if event.key in (pygame.K_ESCAPE, pygame.K_q):
                running = False
            elif event.key == pygame.K_r:
                train.regenerate()
                smoke.puffs.clear()
            elif event.key == pygame.K_RIGHT:
                train.regenerate(train.seed + 1); smoke.puffs.clear()
            elif event.key == pygame.K_LEFT:
                train.regenerate(train.seed - 1); smoke.puffs.clear()
            elif event.key == pygame.K_UP:
                train.accelerate(40)
            elif event.key == pygame.K_DOWN:
                train.accelerate(-40)
            elif event.key == pygame.K_SPACE:
                train.stop()
            elif event.key == pygame.K_s:
                scroll = not scroll

    train.update(dt)

    # camera : le train defile, ou reste centre si on a coupe le defilement
    if scroll:
        cam = SCREEN_WIDTH - (train.distance % (train.length + SCREEN_WIDTH + 200))
    else:
        cam = (SCREEN_WIDTH - train.length) / 2 - MARGIN

    smoke.emit(train.smoke_position(cam, 0), train.speed, dt)
    smoke.update(dt, train.speed)

    STATS["triangles"] = 0
    draw_scene(screen)
    train.draw(screen, cam, 0)
    smoke.draw(screen)
    hud(screen, train, STATS["triangles"])

    pygame.display.flip()

pygame.quit()