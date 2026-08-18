import pygame as ui
from shapes import *
from train import Train

SCREEN_WIDTH = 1280
SCREEN_HEIGHT = 720

RAIL_Y = SCREEN_HEIGHT * 0.78
BACKGROUND = (18, 18, 34)

shapes = [
    Square(50, 50, 100, (255, 0, 0)),                  
    Rectangle(200, 50, 150, 80, (0, 255, 0)),          
    Triangle(400, 50, 100, 100, (0, 0, 255)),          
    Circle(200, 300, 50, (255, 255, 0), 30)            
]

def build_scene():
    decor = [
        Rectangle(SCREEN_WIDTH / 2, RAIL_Y + 3, SCREEN_WIDTH, 6, (96, 92, 126)),
        Rectangle(SCREEN_WIDTH / 2, RAIL_Y + 40, SCREEN_WIDTH, 80, (13, 13, 26)),
    ]
    train = Train(180, RAIL_Y, (50, 94, 140))
    return decor, train

def draw_shapes(screen, shapes):
    for shape in shapes:
        shape.draw(screen)

    
def gui(screen: ui.display, decor, train):
    RUNNING = True
    while RUNNING:
        for event in ui.event.get():
            if event.type == ui.QUIT:
                RUNNING = False

        screen.fill(BACKGROUND)
        draw_shapes(screen, decor)
        train.draw(screen)
        ui.display.flip()

    ui.quit()

def start_gui():
    ui.init()
    screen = ui.display.set_mode((SCREEN_WIDTH, SCREEN_HEIGHT))
    ui.display.set_caption("Music viz")
    clock = ui.time.Clock()
    decor, train = build_scene()
    gui(screen, decor, train)


if __name__ == "__main__":
    start_gui()