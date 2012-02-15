"""
Coded by Matthew Nebel for the CogWorks IFF experiment

The Picture class is used to easily store information about and manipulate the art assets of the experiment.
    Variables:
        image - stores the picture itself, scaled by the given number
        loc - a tuple storing the x and y coordinate of the image
    Functions:
        init - takes the filename of an image on the computer, a tuple containing the x and y coordinates of
            where the image should be drawn on the screen, and a float value to scale the image by.
        shade - takes a tuple of RGB values between 0 and 1 to shade the entire image with
"""

import pygame, sys, math, numpy
from pygame.locals import *

class Picture:
    def __init__(self, filename, location, scale):
        self.image = pygame.image.load("looming_art/"+filename).convert_alpha()
        self.image = pygame.transform.smoothscale(self.image, (int(self.image.get_width()*scale), int(self.image.get_height()*scale)))
        self.loc = location
        
    def shade(self, color):
        copy1 = self.image.copy()
        copy2 = self.image.copy()
        
        alphaCopy = pygame.surfarray.array_alpha(copy1)
        alphaRef = pygame.surfarray.pixels_alpha(copy1)
        RGBarray = pygame.surfarray.pixels3d(copy2)
        
        RGBarray[:,:,0] *= color[0]/255.0
        RGBarray[:,:,1] *= color[1]/255.0
        RGBarray[:,:,2] *= color[2]/255.0
            
        pygame.surfarray.blit_array(copy1, RGBarray)
        alphaRef[:] = alphaCopy
        
        return copy1