#!/usr/bin/env python3

import random
import math
from typing import Union

import pygame
from pygame import Surface, time
from pygame.display import Info
from pygame.locals import *
from pygame.math import *


def size_from_ratio(w, h, r):
    rh = w/h
    if rh >= 1:
        return int(h * r), h
    else:
        return w, int(w / r)


WIDTH = 640
HEIGHT = 480
RATIO = 4/3
FPS = 60
# FPS = 0
SPEED = 3
CAMERA_SPEED = 1

# Define Colors 
WHITE = (255, 255, 255)
BLACK = (0, 0, 0)
RED = (255, 0, 0)
GREEN = (0, 255, 0)
BLUE = (0, 0, 255)

## initialize pygame and create window
pygame.init()
# pygame.mixer.init()  ## For sound
info = Info()
size = size_from_ratio(info.current_w, info.current_h, RATIO)
screen = pygame.display.set_mode(size, FULLSCREEN)
scale_direct = size[0] / WIDTH
growness = 50
scale = scale_direct * growness
offset = Vector2(640/2/growness, 480/2/growness)
print('Scale:', scale_direct, scale)
pygame.display.set_caption("<Your game>")
clock = pygame.time.Clock()     ## For syncing the FPS


## group all the sprites together for ease of update
foreground_sprites = pygame.sprite.Group()


def clamp(x, mi, ma):
    return max(mi, min(ma, x))


def clamp01(x):
    return clamp(x, 0, 1)


def rot_center(image, angle):

    center = image.get_rect().center
    rotated_image = pygame.transform.rotate(image, angle)
    new_rect = rotated_image.get_rect(center = center)

    return rotated_image, new_rect


class Camera:
    def __init__(self):
        self.position = Vector2()

    def update(self, player):
        value = clamp01(CAMERA_SPEED * delta_time)
        newpos = self.position.lerp(player.position, value)
        if newpos.distance_squared_to(player.position) > 1:
            self.position.update(newpos)

camera = Camera()


def floor_vector(vec: Union[Vector2, Vector3]):
    return type(vec)([math.floor(part) for part in vec])


class PositionBasedSprite(pygame.sprite.Sprite):
    base_image: Surface

    def __init__(self, size=None):
        super().__init__()
        self.position = Vector2()
        self.rotation = 0
        self.size = size
        self._last_position_pos = [None, None]
        self._last_position_image = [None, None]

    def _get_image(self):
        if self._last_position_image[0] == ((self.position, self.rotation), camera.position):
            return self._last_position_image[1]
        self._last_position_image[0] = ((Vector2(self.position), self.rotation), Vector2(camera.position))
        scaled_size = math.floor(self.size * scale)
        result = pygame.transform.scale(self.base_image, (scaled_size, scaled_size))
        result = rot_center(result, self.rotation)
        self._last_position_image[1] = result
        return result

    @property
    def image(self):
        if self._pos_on_screen() is None:
            return Surface((0, 0))
        return self._get_image()[0]

    @property
    def radius(self):
        return self.size // 2 * scale

    def _pos_on_screen(self):
        if self._last_position_pos[0] == (self.position, camera.position):
            return self._last_position_pos[1]
        self._last_position_pos[0] = (Vector2(self.position), Vector2(camera.position))
        base_vector = Vector2(self.position)
        base_vector += offset
        base_vector -= camera.position
        if (
               base_vector.x < -1
            or base_vector.y < -1
            or base_vector.x > growness * 4 / 3 + 1
            or base_vector.y > growness + 1
        ):
            self._last_position_pos[1] = None
            return None
        self._last_position_pos[1] = base_vector
        return base_vector

    @property
    def rect(self):
        # scaled_size = math.floor(self.size * scale)
        base_vector = self._pos_on_screen()
        # base_vector = Vector2(self.position)
        # base_vector += offset
        # base_vector -= camera.position
        if base_vector is None:
            return Rect(-1920, -1080, 0, 0)
        base_vector = floor_vector(base_vector * scale)
        base_vector.y = HEIGHT * scale_direct - base_vector.y
        rect = Rect(self._get_image()[1])
        rect.x += int(base_vector[0])
        rect.y += int(base_vector[1])
        return rect


class Player(PositionBasedSprite):
    base_image = pygame.image.load('smile.png').convert_alpha()

    def __init__(self):
        super().__init__(1)

    def update(self, *args, **kwargs):
        mouse_pos = pygame.mouse.get_pos()
        mouse_rel = Vector2(mouse_pos) - Vector2(self.rect.center)
        mouse_direction = -mouse_rel.as_polar()[1] - 90
        self.rotation = mouse_direction
        if movement:
            self.position += movement.normalize() * delta_time * SPEED
            self.position.update(clamp(self.position.x, -32, 32), clamp(self.position.y, -24, 24))

player = Player()
# player.position += (16, 12)


class Tile(PositionBasedSprite):
    base_image = pygame.image.load('ground.png')


background_sprites = pygame.sprite.Group()
tiles = []
for x in range(-32, 33):
    tiles.append([])
    for y in range(-24, 25):
        tile = Tile(1)
        tile.position.update(Vector2(x, y))
        tiles[-1].append(tile)
        background_sprites.add(tile)


foreground_sprites.add(player)


ui_group = pygame.sprite.Group()


def inverted_colors(img):
    inv = Surface(img.get_rect().size, SRCALPHA)
    inv.fill((255, 255, 255, 255))
    inv.blit(img, (0, 0), None, pygame.constants.BLEND_RGB_SUB)
    return inv


class UIButton(pygame.sprite.Sprite):
    bgleft = pygame.image.load('button-bg-left.png').convert_alpha()
    bgmiddle = pygame.image.load('button-bg-middle.png').convert_alpha()
    bgright = pygame.image.load('button-bg-right.png').convert_alpha()

    def __init__(self, content: Surface, rect: Rect, include_background=True):
        super().__init__()
        self.background = Surface(rect.size, pygame.SRCALPHA, 32).convert_alpha()
        self.content = content
        self.rect = rect
        self.include_background = include_background
        self.background_elements = [
            pygame.transform.scale(element, (11, rect.height))
            for element in (self.bgleft, self.bgmiddle, self.bgright)
        ]
        self.inverted_background_elements = [
            # inverted_colors(element)
            element.copy()
            for element in self.background_elements
        ]
        for elem in self.inverted_background_elements:
            array = pygame.surfarray.pixels2d(elem)
            # array ^= 2 ** 32 - 1
            LIGHT_BLUE = 0xFF0094FF
            DARK_BLUE = 0xFF0026FF
            array[array == LIGHT_BLUE] = DARK_BLUE
            array[array == DARK_BLUE] = LIGHT_BLUE
            del array

    def update(self, *args, **kwargs):
        if self.include_background:
            self.background.fill((0, 0, 0, 0))
            if self.rect.collidepoint(pygame.mouse.get_pos()):
                elements = self.inverted_background_elements
            else:
                elements = self.background_elements
            self.background.blit(
                elements[0],
                Rect(0, 0, 11, self.rect.height)
            )
            for i in range(1, self.rect.width // 11):
                self.background.blit(
                    elements[1],
                    Rect(i * 11, 0, 11, self.rect.height)
                )
            self.background.blit(
                elements[2],
                Rect(self.rect.width - 11, 0, 11, self.rect.height)
            )

    @property
    def image(self):
        result = self.background.copy()
        result.blit(self.content, Rect((0, 0), self.rect.size))
        return result

quit_button = UIButton(
    pygame.transform.scale(
        pygame.image.load('exit.png').convert_alpha(), (50, 50)),
    Rect(size[0] - 60, 10, 50, 50)
)
ui_group.add(quit_button)


movement = Vector2()
## Game loop
running = True
smoothfps = FPS if FPS > 0 else 1000
fps_smoothing = 0.9

while running:

    delta_time = clock.tick(FPS) / 1000     ## will make the loop run at the same speed all the time
    if delta_time > 0:
        thisfps = 1 / delta_time
    else:
        thisfps = 1000
    smoothfps = (smoothfps * fps_smoothing) + (thisfps * (1 - fps_smoothing))
    # if delta_time > 0:
    #     print('FPS:', 1/delta_time, ' '*24, end='\r')
    # else:
    #     print('FPS:', '>1000', ' '*24, end='\r')
    print('FPS:', int(smoothfps), ' '*24, end='\r')
    
    #1 Process input/events
    for event in pygame.event.get():        # gets all the events which have occured till now and keeps tab of them.
        ## listening for the the X button at the top
        if event.type == pygame.QUIT:
            running = False
        elif event.type == KEYDOWN:
            if event.key == K_a:
                movement.x -= 1
            elif event.key == K_d:
                movement.x += 1
            elif event.key == K_w:
                movement.y += 1
            elif event.key == K_s:
                movement.y -= 1
        elif event.type == KEYUP:
            if event.key == K_a:
                movement.x += 1
            elif event.key == K_d:
                movement.x -= 1
            elif event.key == K_w:
                movement.y -= 1
            elif event.key == K_s:
                movement.y += 1


    #2 Update
    background_sprites.update()
    foreground_sprites.update()
    camera.update(player)


    #3 Draw/render
    screen.fill(BLACK)

    

    background_sprites.draw(screen)
    foreground_sprites.draw(screen)
    ########################

    ### Your code comes here

    ########################

    ## Done after drawing everything to the screen
    ui_group.update()
    ui_group.draw(screen)
    pygame.display.flip()       

pygame.quit()
