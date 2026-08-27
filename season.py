import pygame
import math
import random
from rain import Rain
from snows import *
from leaves import *
from shapes import *
from config import *

class Season():
    '''
    Manages the season of the game
    '''
    def __init__(self, nb_cycle):
        '''
        '''

        autumn_colors = [(200, 75, 25), (220, 120, 30), (160, 60, 20), (210, 160, 40)]
        spring_colors = [(255, 183, 197), (255, 145, 164), (255, 230, 240)]

        self.nb_cycle = nb_cycle #the nb of the current cycle
        self.season_type = 0

        self.rain = Rain(SCREEN_WIDTH, SCREEN_HEIGHT, nb_drops=100)
        self.autumn_leaves = LeavesManager(SCREEN_WIDTH, SCREEN_HEIGHT, autumn_colors)
        self.spring_leaves = LeavesManager(SCREEN_WIDTH, SCREEN_HEIGHT, spring_colors)
        self.snows = SnowsManager(SCREEN_WIDTH, SCREEN_HEIGHT, (255, 255, 255))

        #Manage opacity of season
        self.opacity_layer = pygame.Surface((SCREEN_WIDTH, SCREEN_HEIGHT), pygame.SRCALPHA)
        self.alpha = 255

    def update(self, dt, total_phase, screen):
        '''
        Manage the switch between the season
        '''
        self.season_type = (int(total_phase) % 4)

        #actual time in the season
        progression = total_phase % 1.0
        fade_duration = 0.1

        if progression < fade_duration:
            #Fade in
            self.alpha = int((progression / fade_duration) * 255)
        elif progression > (1.0 - fade_duration):
            #Fade out
            self.alpha = int(((1.0 - progression) / fade_duration) * 255)
        else:
            #Full opacity
            self.alpha = 255

        self.opacity_layer.fill((0,0,0,0))

        match self.season_type:
            case 0:
                self.summer(dt, self.opacity_layer)
            case 1:
                self.autumn(dt, self.opacity_layer)
            case 2:
                self.winter(dt, self.opacity_layer)
            case 3:
                self.spring(dt, self.opacity_layer)

        #set the alpha of the second screen
        self.opacity_layer.set_alpha(self.alpha)

        #set the new screen on the actual one
        screen.blit(self.opacity_layer, (0,0))
        


    def summer(self, dt, screen):
        '''
        TODO add the fougère
        '''

    def autumn(self, dt, screen):
        '''
        TODO add the fall of orange leafs
        '''
        self.rain.update(dt)
        self.rain.draw(screen)

        self.autumn_leaves.update(dt)
        self.autumn_leaves.draw(screen)

    def winter(self, dt, screen):
        '''
        TODO Add the fall of the snow
        '''
        self.snows.update(dt)
        self.snows.draw(screen)


    def spring(self, dt, screen):
        '''
        TODO add the fall of sakura's 
        '''

        self.spring_leaves.update(dt)
        self.spring_leaves.draw(screen)