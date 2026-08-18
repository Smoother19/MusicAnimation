import pygame as ui
from shapes import *
from train import Train

SCREEN_WIDTH = 1280
SCREEN_HEIGHT = 720

RAIL_Y = SCREEN_HEIGHT * 0.78
BACKGROUND = (18, 18, 34)

def build_scene():
    decor = [
        Rectangle(SCREEN_WIDTH / 2, RAIL_Y + 3, SCREEN_WIDTH, 6, (96, 92, 126)),
        Rectangle(SCREEN_WIDTH / 2, RAIL_Y + 40, SCREEN_WIDTH, 80, (13, 13, 26)),
    ]
    train = Train(180, RAIL_Y, (50, 94, 140), wagons=2)
    return decor, train

def draw_shapes(screen, shapes):
    for shape in shapes:
        shape.draw(screen)

    
def gui(screen: ui.Surface, decor, train):
    RUNNING = True
    frame = 0
    clock = ui.time.Clock()
    while RUNNING:
        dt = clock.tick(60) / 1000.0
        for event in ui.event.get():
            if event.type == ui.QUIT:
                RUNNING = False

        STATS["triangles"] = 0
        screen.fill(BACKGROUND)
        draw_shapes(screen, decor)
        train.draw(screen)
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
    decor, train = build_scene()
    gui(screen, decor, train)


if __name__ == "__main__":
    start_gui()