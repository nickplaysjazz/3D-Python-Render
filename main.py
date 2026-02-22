import configparser
import math
import numpy as np
import pygame as pg 
import sys

from pathlib import Path
from pygame.locals import *
from OpenGL.GL import *
from OpenGL.GLU import *

class RectangleObject:
    def __init__(
            self, 
            pos1, 
            pos2,
            body_color=(0.1,0.1,0.1),
            edge_color=(1,1,1),
            draw_body=True,
            draw_edges=False
        ):
        self.x1, self.y1, self.z1 = pos1
        self.x2, self.y2, self.z2 = pos2

        self.width = self.x2 - self.x1
        self.height = self.y2 - self.y1
        self.depth = self.z2 - self.z1

        self.body_color = body_color
        self.edge_color = edge_color
        
        unscaled_vertices = ((0,0,0),(1,0,0),(1,1,0),(0,1,0),(0,1,1),(1,1,1),(1,0,1),(0,0,1))
        self.vertices = tuple(
            tuple((val * s) + shift for val, s, shift in zip(vertex, (self.width, self.height, self.depth), pos1))
            for vertex in unscaled_vertices
        )
    
        self.edges = ((0,1),(1,2),(2,3),(3,0),(4,5),(5,6),(6,7),(7,4),(3,4),(0,7),(1,6),(5,2))
        self.quads = ((0,1,2,3),(4,5,6,7),(1,2,5,6),(0,3,4,7),(2,3,4,5),(0,1,6,7))

        self.draw_body = draw_body
        self.draw_edges = draw_edges

    def draw(self):
        if self.draw_body:
            glBegin(GL_QUADS)
            glColor3fv(self.body_color)
            for q in self.quads:
                for v in q:
                    glVertex3fv(self.vertices[v])
            glEnd()

        if self.draw_edges:
            glBegin(GL_LINES)
            glColor3fv(self.edge_color)
            for edge in self.edges:
                for vertex in edge:
                    glVertex3fv(self.vertices[vertex])
            glEnd()
            

# floorVertices = ((1,1,1),(-1,1,-1),(1,1,-1),(-1,1,1))
# floorQuads = ((0,2,1,3),)

# wallVertices = (
#     (1,1,1),(1,1,-1),(-1,1,-1),(-1,1,1),
#     (1,1,1),(1,1,-1),(-1,1,-1),(-1,1,1)
# )
# wallQuads = ((0,1,5,4),(1,2,6,5),(2,3,7,6),(3,0,4,7))

# def draw_wire_cube():
#     glBegin(GL_LINES)
#     glColor3fv((1,1,1))
#     for cubeEdge in cubeEdges:
#         for cubeVertex in cubeEdge:
#             glVertex3fv(cubeVertices[cubeVertex])
#     glEnd()

# def draw_solid_cube():
#     glBegin(GL_QUADS)
#     for i, cubeQuad in enumerate(cubeQuads):
#         glColor3fv(colors[i])
#         for cubeVertex in cubeQuad:
#             glVertex3fv(cubeVertices[cubeVertex])
#     glEnd()

# def draw_floor():
#     glBegin(GL_QUADS)
#     glColor3fv((0.2,0.2,0.2))
#     for floorQuad in floorQuads:
#         for floorVertex in floorQuad:
#             glVertex3fv(floorVertices[floorVertex])
#     glEnd()

# def draw_walls():
#     glBegin(GL_QUADS)
#     glColor3fv((0.1,0.1,0.1))
#     for wallQuad in wallQuads:
#         for wallVertex in wallQuad:
#             glVertex3fv(wallVertices[wallVertex])
#     glEnd()

# def is_wall(x, z):
#     padding = 0.3

#     if x < -MAP_WIDTH/2 + padding or x > MAP_WIDTH/2 - padding:
#         return True
#     elif z < -MAP_HEIGHT/2 + padding or z > MAP_HEIGHT/2 - padding:
#         return True
#     else:
#         return False

def parse_ini():
    BASE_DIR = Path(__file__).resolve().parent
    config_path = BASE_DIR / "settings.ini"
    config = configparser.ConfigParser()
    config.read(config_path)
    return config
            
def main():
    RED_TEXT = "\033[31m"
    RESET_TEXT = "\033[0m"
    try:
        settings = parse_ini()
    except configparser.ParsingError as e:
        print(f"{RED_TEXT}!! ERROR !! Configuration file does not follow legal syntax:\n{e}{RESET_TEXT}")
        sys.exit(1)

    try:
        DISPLAY_WIDTH = settings.getint('Options', 'DISPLAY_WIDTH')
        DISPLAY_HEIGHT = settings.getint('Options', 'DISPLAY_HEIGHT')
        FOV = settings.getfloat('Options', 'FOV')
        MOUSE_SENSITIVITY = settings.getfloat('Options','MOUSE_SENSITIVITY')
    except ValueError as e:
        print(f"{RED_TEXT}!! ERROR !! Type mismatch error:\n{e}{RESET_TEXT}")
        sys.exit(1)

    pg.init()
    display = (DISPLAY_WIDTH, DISPLAY_HEIGHT)

    # Double buffering means we can transform one buffer while leaving the visible one untouched
    pg.display.set_mode(display, DOUBLEBUF | OPENGL)
    pg.mouse.set_visible(False)
    pg.event.set_grab(True) # Lock mouse to window

    # Define system geometry
    level_geometry = [
        RectangleObject((-5, -2, -5), (5, -1, 5))
    ]

    # Defines camera "frustrum"
    gluPerspective(FOV, (display[0]/display[1]), 0.1, 100.0)
    glEnable(GL_DEPTH_TEST)
    # glEnable(GL_CULL_FACE)

    clock = pg.time.Clock()

    # Player Starting Position & Camera
    cam_x, cam_y, cam_z = 0, 0, 0
    cube_rotation = 0
    yaw, pitch = 0.0, 0.0
    move_speed = 0.1
    mouse_sensitivity = MOUSE_SENSITIVITY

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

        #if not is_wall(cam_x + dx, cam_z):
        cam_x += dx

        #if not is_wall(cam_x, cam_z + dz):
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
        for obj in level_geometry:
            obj.draw()

        # Moving objects should be handled with individual matrices
        #glPushMatrix()
        #glRotatef(cube_rotation, 1, 1, 1)
        #draw_wire_cube()
        #glPopMatrix()

        glPopMatrix()
        # ===============================================

        # Update any states here for e.g. animations
        cube_rotation += 1
        
        # display to user       
        pg.display.flip()

        # wait at 60 fps
        clock.tick(60)

if __name__ == "__main__":
    main()