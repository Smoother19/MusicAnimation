import os, sys; os.environ.setdefault("SDL_VIDEODRIVER","dummy")
import pygame; pygame.init()
from grammar_engine import generate
from shapes import STATS, Wheel
import config as C
import grammar as G

seeds = [int(a) for a in sys.argv[1:]] or [3, 7, 11, 15]
row = 220
C.RAIL_Y = row - 30; G.RAIL_Y = C.RAIL_Y
surf = pygame.Surface((1400, row * len(seeds)))
for i, seed in enumerate(seeds):
    band = pygame.Surface((1400, row)); band.fill(C.SKY)
    pygame.draw.polygon(band, C.GROUND, [(0, C.RAIL_Y), (1400, C.RAIL_Y),
                                         (1400, row), (0, row)])
    shapes, root, w = generate("Train", seed, x=C.MARGIN, bottom=C.RAIL_Y,
                               height=170, world=G.world(seed),
                               on_missing=G.missing, ctx=G.context(seed))
    for s in shapes: s.draw(band)
    surf.blit(band, (0, i * row))
pygame.image.save(surf, "sheet.png")
print("triangles:", STATS["triangles"])