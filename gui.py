import pygame as ui
import random
from shapes import *
from cloud import Cloud
from fireworks import Fireworks
from train import Train
from rain import Rain
from moutains import Mountains
from season import Season
import random
from smokeemitter import SmokeEmitter
from particle import Particle
from config import *
from pathlib import Path
import os
from sync import SyncMusic
from midiDecoder import decode
from sky import Sky
from birds import *


NOTE_LOW = (255, 90, 170)
NOTE_HIGH = (110, 230, 255)
MAX_CLOUDS = 10
MAX_FIREWORKS = 10
NOTE_Y_LOW = 300
NOTE_Y_HIGH = 80
ACCENT = "trumpet"


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


def note_color(ratio):
    return tuple(int(a + (b - a) * ratio) for a, b in zip(NOTE_LOW, NOTE_HIGH))


def dim(color, k):
    return tuple(int(c * k) for c in color)


def spawn_note(note, sync, sky, fireworks, markers, clouds):
    r = sync.ratio(note)
    y = NOTE_Y_LOW - r * (NOTE_Y_LOW - NOTE_Y_HIGH)
    color = note_color(r)

    if note["instrument"] == ACCENT:
        x = random.uniform(90, SCREEN_WIDTH - 90)
        if len(fireworks) < MAX_FIREWORKS:
            fireworks.append(Fireworks(x, y, color, nb_rays=14,
                                       max_speed=5 + 5 * r,
                                       lifespan=int(30 + 40 * min(1.0, note["duration"]))))
            return
    else:
        x = random.uniform(60, SCREEN_WIDTH - 60)
        if r > 0.85 and not sky.is_night and len(clouds) < MAX_CLOUDS:
            params = list(Cloud.get_random_param())
            params[1] = (x, y)
            params[2] = sky.tint((255, 255, 255), 0.45)
            clouds.append(Cloud(*params))

    markers.append(Particle(x, y, color, fade_to=dim(color, 0.25),
                            lifetime=max(0.45, min(1.6, note["duration"])),
                            size=14 + 22 * (1 - r)))


def gui(screen: ui.Surface, sync):
    clouds = []
    fireworks = []
    markers = []
    RUNNING = True
    frame = 0
    clock = ui.time.Clock()
    train = Train(y=RAIL_Y, n_wagons=random.randint(2, 5))
    train.set_speed(SPEED, True)
    train_x = (SCREEN_WIDTH - train.length) / 2
    scroll = 0.0
    smoke = SmokeEmitter()

    curveTrack = CurvesTrack(500, sync, span=380)

    sky = Sky(sync)
    birds = Birds(sync)

    mg_season = Season(SKY_CYCLES_PER_TRACK)

    MOUNTAIN_COLORS = ((60, 70, 90), (45, 55, 75), (30, 40, 60))

    mountains = Mountains((0, 300), (SCREEN_WIDTH, 300), width=8, color=(60, 70, 90), type_curve=1, a=1.5, b=2.0, amplitude=60, reactivity=32)
    ridge_mid = Mountains((0, 380),(SCREEN_WIDTH, 380), width=8,color=(45, 55, 75),type_curve=1,a=2.0,b=3.5,amplitude=40,bottom_y=SCREEN_HEIGHT, reactivity=52)
    ridge_fore = Mountains((0, 460),(SCREEN_WIDTH, 460), width=8,color=(30, 40, 60),type_curve=1,a=1.0,b=5.0,amplitude=25,bottom_y=SCREEN_HEIGHT, reactivity=78)

    mountain_chains = [mountains, ridge_mid, ridge_fore]

    while RUNNING:
        dt = clock.tick(60) / 1000.0
        STATS["triangles"] = 0
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
                elif event.key == ui.K_LEFTBRACKET:
                    sync.latency -= 0.010
                    print(f"latence {1000 * sync.latency:+.0f} ms")
                elif event.key == ui.K_RIGHTBRACKET:
                    sync.latency += 0.010
                    print(f"latence {1000 * sync.latency:+.0f} ms")
                elif event.key == ui.K_f:
                    params = Fireworks.get_random_params()
                    fw = Fireworks(*params)
                    fireworks.append(fw)

        t = ui.mixer.music.get_pos() / 1000.0
        started = sync.update(t) if t >= 0 else []

        if t >= 0:
            for note in started:
                spawn_note(note, sync, sky, fireworks, markers, clouds)

            # Vitesse du train pilotee par la densite globale
            target = SPEED * sync.speed_factor(t)
            train.speed += (target - train.speed) * min(1.0, dt * 0.8)

        sky.update(dt, t, started)
        birds.update(dt, t, started, sky, train.speed)

        sky.draw(screen)
        birds.draw(screen, PLANE_FAR)

        clouds_left = []
        #Test if the cloudas list is not empty
        if clouds:
            for cloud in clouds:
                cloud.draw(screen)
                cloud.moving_cloud(train.speed/16)

                #Add to temp list the non valid clouds
                if not cloud.is_out_of_screen(SCREEN_WIDTH):
                    clouds_left.append(cloud)

        clouds = clouds_left

        for marker in markers:
            marker.update(dt, wind=train.speed * 0.15)
            marker.draw(screen)
        markers = [m for m in markers if not m.dead]

        mountains.update(dt, train.speed * 0.2, sync.band(t, 0) if t >= 0 else 0.0)
        ridge_mid.update(dt, train.speed * 0.5, sync.band(t, 1) if t >= 0 else 0.0)
        ridge_fore.update(dt, train.speed * 0.8, sync.band(t, 2) if t >= 0 else 0.0)

        for ridge in mountain_chains:
            ridge.draw(screen, sky=sky)

        birds.draw(screen, PLANE_MID)

        mg_season.update(dt, sky.total_phases, screen, mountain_chains)

        if fireworks:
            fireworks_left = []
            for fw in fireworks:
                fw.draw(screen)
                fw.update()

                if not fw.is_done():
                    fireworks_left.append(fw)

            fireworks = fireworks_left

        curveTrack.update(dt, t)
        train.update(dt)

        y_center, angle = curveTrack.get_info_track(train_x, train.length)
        pivot = (train_x + train.length / 2, RAIL_Y)

        sx, sy = train.smoke_position(train_x, 0)
        smoke.update(dt, sx, sy, wind=train.speed)
        scroll -= train.speed * dt

        curveTrack.draw(screen)
        smoke.draw(screen, oy=y_center)
        train.draw(screen, ox=train_x, oy=0, angle=angle, pivot=pivot, track=curveTrack)
        birds.draw(screen, PLANE_NEAR)
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
