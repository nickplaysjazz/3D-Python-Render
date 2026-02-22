import math
import numpy as np
import pygame as pg 
import sys

from pygame.locals import *
from OpenGL.GL import *
from OpenGL.GLU import *

MAP_WIDTH = 20
MAP_HEIGHT = 20

cubeVertices = ((1,1,1),(1,1,-1),(1,-1,-1),(1,-1,1),(-1,1,1),(-1,-1,-1),(-1,-1,1),(-1, 1,-1))
cubeEdges = ((0,1),(0,3),(0,4),(1,2),(1,7),(2,5),(2,3),(3,6),(4,6),(4,7),(5,6),(5,7))
cubeQuads = ((0,3,6,4),(2,5,6,3),(1,2,5,7),(1,0,4,7),(7,4,6,5),(2,3,0,1))
colors = (
    (0.0, 0.8, 0.0),
    (0.0, 0.6, 0.0),
    (0.0, 0.7, 0.0),
    (0.0, 0.5, 0.0),
    (0.0, 0.9, 0.0),
    (0.0, 0.4, 0.0)
)

FLOOR_HEIGHT = -2
floorVertices = ((MAP_WIDTH//2,FLOOR_HEIGHT,MAP_HEIGHT//2),(-MAP_WIDTH//2,FLOOR_HEIGHT,-MAP_HEIGHT//2),(MAP_WIDTH//2,FLOOR_HEIGHT,-MAP_HEIGHT//2),(-MAP_WIDTH//2,FLOOR_HEIGHT,MAP_HEIGHT//2))
floorQuads = ((0,2,1,3),)

WALL_HEIGHT = FLOOR_HEIGHT + 2
wallVertices = (
    (MAP_WIDTH//2,FLOOR_HEIGHT,MAP_HEIGHT//2),(MAP_WIDTH//2,FLOOR_HEIGHT,-MAP_HEIGHT//2),(-MAP_WIDTH//2,FLOOR_HEIGHT,-MAP_HEIGHT//2),(-MAP_WIDTH//2,FLOOR_HEIGHT,MAP_HEIGHT//2),
    (MAP_WIDTH//2,WALL_HEIGHT,MAP_HEIGHT//2),(MAP_WIDTH//2,WALL_HEIGHT,-MAP_HEIGHT//2),(-MAP_WIDTH//2,WALL_HEIGHT,-MAP_HEIGHT//2),(-MAP_WIDTH//2,WALL_HEIGHT,MAP_HEIGHT//2)
)
wallQuads = ((0,1,5,4),(1,2,6,5),(2,3,7,6),(3,0,4,7))

def draw_wire_cube():
    glBegin(GL_LINES)
    glColor3fv((1,1,1))
    for cubeEdge in cubeEdges:
        for cubeVertex in cubeEdge:
            glVertex3fv(cubeVertices[cubeVertex])
    glEnd()

def draw_solid_cube():
    glBegin(GL_QUADS)
    for i, cubeQuad in enumerate(cubeQuads):
        glColor3fv(colors[i])
        for cubeVertex in cubeQuad:
            glVertex3fv(cubeVertices[cubeVertex])
    glEnd()

def draw_floor():
    glBegin(GL_QUADS)
    glColor3fv((0.2,0.2,0.2))
    for floorQuad in floorQuads:
        for floorVertex in floorQuad:
            glVertex3fv(floorVertices[floorVertex])
    glEnd()

def draw_walls():
    glBegin(GL_QUADS)
    glColor3fv((0.1,0.1,0.1))
    for wallQuad in wallQuads:
        for wallVertex in wallQuad:
            glVertex3fv(wallVertices[wallVertex])
    glEnd()

def is_wall(x, z):
    padding = 0.3

    if x < -MAP_WIDTH/2 + padding or x > MAP_WIDTH/2 - padding:
        return True
    elif z < -MAP_HEIGHT/2 + padding or z > MAP_HEIGHT/2 - padding:
        return True
    else:
        return False
            
def main():
    pg.init()
    display = (800, 600)

    # Double buffering means we can transform one buffer while leaving the visible one untouched
    pg.display.set_mode(display, DOUBLEBUF | OPENGL)
    pg.mouse.set_visible(False)
    pg.event.set_grab(True) # Lock mouse to window

    # Defines camera "frustrum"
    CAMERA_FOV = 60
    gluPerspective(CAMERA_FOV, (display[0]/display[1]), 0.1, 100.0)
    glEnable(GL_DEPTH_TEST)
    #glEnable(GL_CULL_FACE)

    clock = pg.time.Clock()

    # Player Starting Position & Camera
    cam_x, cam_y, cam_z = 0, 0, 0
    cube_rotation = 0
    yaw, pitch = 0.0, 0.0
    move_speed = 0.1
    mouse_sensitivity = 0.2

    glTranslatef(cam_x, cam_y, cam_z)

    while True:
        # handle events
        for event in pg.event.get():
            if event.type == pg.QUIT:
                pg.quit()
                sys.exit()
            if event.type == pg.KEYDOWN:
                if event.key == pg.K_ESCAPE: 
                    pg.quit()
                    sys.exit()

        mouse_dx, mouse_dy = pg.mouse.get_rel()
        yaw += mouse_dx * mouse_sensitivity
        yaw = np.mod(yaw, 360)
        pitch += mouse_dy * mouse_sensitivity
        pitch = max(-89.0, min(89.0, pitch))

        keys = pg.key.get_pressed()
        yaw_rad = math.radians(yaw)

        # Calculate forward and right vectors based on yaw
        forward_x = math.sin(yaw_rad)
        forward_z = -math.cos(yaw_rad)
        right_x = math.cos(yaw_rad)
        right_z = math.sin(yaw_rad)

        dx, dz = 0, 0
        if keys[pg.K_w]:
            dx += forward_x * move_speed
            dz += forward_z * move_speed
        if keys[pg.K_s]:
            dx -= forward_x * move_speed
            dz -= forward_z * move_speed
        if keys[pg.K_a]:
            dx -= right_x * move_speed
            dz -= right_z * move_speed
        if keys[pg.K_d]:
            dx += right_x * move_speed
            dz += right_z * move_speed

        if not is_wall(cam_x + dx, cam_z):
            cam_x += dx

        if not is_wall(cam_x, cam_z + dz):
            cam_z += dz
                
        # clear previous screen
        glClear(GL_COLOR_BUFFER_BIT|GL_DEPTH_BUFFER_BIT)

        # transformations and drawing 
        # ===============================================
        glPushMatrix()

        # Camera
        glRotatef(pitch, 1, 0, 0)
        glRotatef(yaw, 0, 1, 0)
        glTranslatef(-cam_x, -cam_y, -cam_z)

        # Static objects
        draw_floor()
        draw_walls()

        # Moving objects should be handled with individual matrices
        glPushMatrix()
        glRotatef(cube_rotation, 1, 1, 1)
        draw_wire_cube()
        glPopMatrix()

        glPopMatrix()
        # ===============================================

        cube_rotation += 1
        
        # display to user       
        pg.display.flip()

        # wait at 60 fps
        clock.tick(60)

if __name__ == "__main__":
    main()