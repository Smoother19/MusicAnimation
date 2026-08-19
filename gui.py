import pygame as ui
import random
from shapes import *
from cloud import Cloud
from train import Train
import random
from smokeemitter import SmokeEmitter
from config import *

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
    clouds = []
    RUNNING = True
    frame = 0
    clock = ui.time.Clock()
    train = Train(y=RAIL_Y, n_wagons=random.randint(2, 5))
    train.set_speed(SPEED, True)
    train_x = (SCREEN_WIDTH - train.length) / 2
    scroll = 0.0
    smoke = SmokeEmitter()
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
                elif event.key == ui.K_c:
                    params = Cloud.get_random_param()
                    clouds.append(Cloud(*params))

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
        train.update(dt)
        sx, sy = train.smoke_position(train_x, 0)
        smoke.update(dt, sx, sy, wind=train.speed)
        scroll -= train.speed * dt

        STATS["triangles"] = 0
        screen.fill(BACKGROUND)
        draw_rails(screen, RAIL_Y, scroll)
        smoke.draw(screen)
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