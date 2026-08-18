import pygame as ui
from shapes import *
from train import Train
import random

SCREEN_WIDTH = 1280
SCREEN_HEIGHT = 720
RAIL_Y = SCREEN_HEIGHT - 180
SPEED = 100.0 
BACKGROUND = (18, 18, 34)

def draw_rails(screen, y, offset):
    ui.draw.polygon(screen, (52, 48, 44),
                    [(0, y), (SCREEN_WIDTH, y), (SCREEN_WIDTH, y + 6), (0, y + 6)])
    tie = 34
    x = -(offset % tie)
    while x < SCREEN_WIDTH:
        ui.draw.polygon(screen, (70, 60, 52),
                        [(x, y + 6), (x + 16, y + 6), (x + 16, y + 14), (x, y + 14)])
        x += tie

def draw_shapes(screen, shapes):
    for shape in shapes:
        shape.draw(screen)

    
def gui(screen: ui.Surface):
    RUNNING = True
    frame = 0
    clock = ui.time.Clock()
    train = Train(y=RAIL_Y, n_wagons=random.randint(2, 5))
    train.set_speed(SPEED, True)
    train_x = (SCREEN_WIDTH - train.length) / 2   # le train reste centre
    scroll = 0.0
    while RUNNING:
        dt = clock.tick(60) / 1000.0
        for event in ui.event.get():
            if event.type == ui.QUIT:
                RUNNING = False
            elif event.type == ui.KEYDOWN:
                if event.key == ui.K_UP:
                    train.accelerate(40)
                elif event.key == ui.K_DOWN:
                    train.accelerate(-40)

        train.update(dt)
        scroll -= train.speed * dt

        STATS["triangles"] = 0
        screen.fill(BACKGROUND)
        draw_rails(screen, RAIL_Y, scroll)
        train.draw(screen, train_x, 0)
        ui.display.flip()

        frame += 1
        if frame % 30 == 0:
            ui.display.set_caption(
                f"RailBeat— {STATS['triangles']} triangles — "
                f"{clock.get_fps():.0f} fps")

    ui.quit()

def start_gui():
    ui.init()
    screen = ui.display.set_mode((SCREEN_WIDTH, SCREEN_HEIGHT))
    gui(screen)


if __name__ == "__main__":
    start_gui()