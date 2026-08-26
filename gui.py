import pygame as ui
import random
from shapes import *
from cloud import Cloud
from fireworks import Fireworks
from train import Train
from rain import Rain
from moutains import Mountains
import random
from smokeemitter import SmokeEmitter
from config import *
from pathlib import Path
import os
from sync import SyncMusic
from midiDecoder import decode
from sky import Sky

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

def gui(screen: ui.Surface, sync):
    clouds = []
    fireworks = []
    RUNNING = True
    frame = 0
    clock = ui.time.Clock()
    train = Train(y=RAIL_Y, n_wagons=random.randint(2, 5))
    train.set_speed(SPEED, True)
    train_x = (SCREEN_WIDTH - train.length) / 2
    scroll = 0.0
    smoke = SmokeEmitter()

    curveTrack = CurvesTrack(RAIL_Y, amplitude=25)
    rain = Rain(SCREEN_WIDTH, SCREEN_HEIGHT, nb_drops=150)

    sky = Sky(sync)

    MOUNTAIN_COLORS = ((60, 70, 90), (45, 55, 75), (30, 40, 60))

    mountains = Mountains((0, 300), (SCREEN_WIDTH, 300), width=8, color=(60, 70, 90), type_curve=1, a=1.5, b=2.0, amplitude=60)
    ridge_mid = Mountains((0, 380),(SCREEN_WIDTH, 380), width=8,color=(45, 55, 75),type_curve=1,a=2.0,b=3.5,amplitude=40,bottom_y=SCREEN_HEIGHT)
    ridge_fore = Mountains((0, 460),(SCREEN_WIDTH, 460), width=8,color=(30, 40, 60),type_curve=1,a=1.0,b=5.0,amplitude=25,bottom_y=SCREEN_HEIGHT)

    while RUNNING:
        dt = clock.tick(60) / 1000.0
        STATS["triangles"] = 0
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
                elif event.key == ui.K_f:
                    params = Fireworks.get_random_params()
                    fw = Fireworks(*params)
                    fireworks.append(fw)

        t = ui.mixer.music.get_pos() / 1000.0
        started = sync.update(t) if t >= 0 else []
        if t >= 0:
            for note in started:
                # les feux d'artifice de nuit, les nuages de jour
                if note["pitch"] < 55 and sky.is_night:
                    fireworks.append(Fireworks(*Fireworks.get_random_params()))
                elif note["pitch"] > 75 and not sky.is_night:
                    params = list(Cloud.get_random_param())
                    params[2] = sky.tint((255, 255, 255), 0.45)  # nuages teintes par l'heure
                    clouds.append(Cloud(*params))

            target = SPEED * sync.speed_factor(t)
            train.speed += (target - train.speed) * min(1.0, dt * 0.8)

        sky.update(dt, t, started)
        sky.draw(screen)
                
       
        STATS["triangles"] = 0
        clouds_left = []
        #Test if the cloudas list is not empty
        if clouds:
            clouds_left = []
            for cloud in clouds:
                cloud.draw(screen)
                cloud.moving_cloud(train.speed/16)
                
                #Add to temp list the non valid clouds
                if not cloud.is_out_of_screen(SCREEN_WIDTH):
                    clouds_left.append(cloud)
            
            #Update clouds list 
            clouds = clouds_left


        #Draw the mountains, teintees par l'heure du jour
        for ridge, base_color in zip((mountains, ridge_mid, ridge_fore), MOUNTAIN_COLORS):
            ridge.color = sky.tint(base_color)
            ridge.draw(screen)
            ridge.update(dt, train.speed * 1.5)
        
        if fireworks:
            fireworks_left = []
            for fw in fireworks:
                fw.draw(screen)
                fw.update()

                if not fw.is_done():
                    fireworks_left.append(fw)

            fireworks = fireworks_left

        #Update clouds list
        clouds = clouds_left
        curveTrack.update(dt, train.speed * 1.5)
        train.update(dt)

        #Update the rain animation
        rain.update(dt)
        rain.draw(screen)

        y_center, angle = curveTrack.get_info_track(train_x, train.length)
        pivot = (train_x + train.length / 2, RAIL_Y)

        sx, sy = train.smoke_position(train_x, 0)
        smoke.update(dt, sx, sy, wind=train.speed)
        scroll -= train.speed * dt
        
        #draw_rails(screen, RAIL_Y, scroll)
        curveTrack.draw(screen)
        smoke.draw(screen, oy=y_center)
        train.draw(screen, ox=train_x, oy=0, angle=angle, pivot=pivot, track=curveTrack)
        ui.display.flip()

        frame += 1
        if frame % 30 == 0:
            ui.display.set_caption(
                f"RailBeat— {STATS['triangles']} triangles — "
                f"{clock.get_fps():.0f} fps")

    ui.quit()

def start_gui(isMidi: bool = False):
    file_dir = Path("output")
    filename = "transcription.mid" if isMidi else "bg.mp3"

    ui.mixer.pre_init(44100, -16, 2, 512)
    ui.init()
    if not ui.mixer.get_init():
        ui.mixer.init()
    screen = ui.display.set_mode((SCREEN_WIDTH, SCREEN_HEIGHT))

    arr, bpm = decode()
    sync = SyncMusic(arr)
    print(f"{len(sync.notes)} notes chargees")

    ui.mixer.music.load(file_dir / filename)
    ui.mixer.music.play()

    gui(screen, sync)

    try:
        os.remove(file_dir / filename)
        if not isMidi:
            os.remove(file_dir / "transcription.mid")
    except OSError as e:
        print(f"Suppression impossible : {e}")


if __name__ == "__main__":
    start_gui()