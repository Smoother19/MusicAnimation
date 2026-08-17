import pygame as ui
from shapes import *

SCREEN_WIDTH = 1280
SCREEN_HEIGHT = 720

shapes = [
    Square(50, 50, 100, (255, 0, 0)),                     # Carré rouge
    Rectangle(200, 50, 150, 80, (0, 255, 0)),             # Rectangle vert
    Triangle(400, 50, 100, 100, (0, 0, 255)),             # Triangle bleu
    Circle(200, 300, 50, (255, 255, 0), 30)               # Cercle jaune (centre en 200,300)
]

def start_gui():
    ui.init()
    screen = ui.display.set_mode((SCREEN_WIDTH, SCREEN_HEIGHT))
    clock = ui.time.Clock()
    gui(screen)
    
def gui(screen: ui.display):
    RUNNING = True
    while RUNNING:
        for event in ui.event.get():
            if event.type == ui.QUIT:
                RUNNING = False

        screen.fill((0, 0, 0))
        for shape in shapes:
            shape.draw(screen)
        ui.display.flip()

    ui.quit()

if __name__ == "__main__":
    start_gui()