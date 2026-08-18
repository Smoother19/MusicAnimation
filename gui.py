import pygame as ui
import random
from shapes import *
from cloud import Cloud

SCREEN_WIDTH = 1280
SCREEN_HEIGHT = 720

shapes = [
    Square(50, 50, 100, (255, 0, 0)),         
    Rectangle(200, 50, 150, 80, (0, 255, 0)),
    Triangle(400, 50, 100, 100, (0, 0, 255)),
    Circle(200, 300, 50, (255, 255, 0), 30)
]

def start_gui():
    ui.init()
    screen = ui.display.set_mode((SCREEN_WIDTH, SCREEN_HEIGHT))
    clock = ui.time.Clock()
    gui(screen)

def gui(screen: ui.display):
    clouds = []
    cloud_base = Cloud(60, (100, 100), (41, 43, 67))
    clouds.append(cloud_base)

    RUNNING = True
    while RUNNING:
        for event in ui.event.get():
            if event.type == ui.QUIT:
                RUNNING = False
            if event.type == ui.KEYDOWN:
                if event.key == ui.K_c:
                    print("test")


        screen.fill((0, 0, 0))
        for shape in shapes:
            shape.draw(screen)

        clouds_left = []
        #Test if the cloudas list is not empty
        if clouds:
            for cloud in clouds:
                cloud.draw(screen)
                cloud.moving_cloud()

                #Add to temp list the non valid clouds
                if not cloud.is_out_of_screen(SCREEN_WIDTH):
                    clouds_left.append(cloud)

        #Update clouds list
        clouds = clouds_left

        ui.display.flip()

    ui.quit()

if __name__ == "__main__":
    start_gui()