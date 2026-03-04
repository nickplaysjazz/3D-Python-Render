import ctypes
import math
import pygame as pg
import sys

from enum import Enum
from OpenGL.GL import *
from OpenGL.GLU import *
from pygame.locals import *
from pyglm import glm

from camera import Camera
from constants import Directions
from setting_utils import read_settings
from shader_utils import Shader


class newObject:
    def __init__(self):
        # fmt: off
        self.vertices = glm.array(
            glm.float32,
            0, 0, 0,  0.1, 0.1, 0.1,
            1, 0, 0,  0.0, 0.0, 1.0,
            1, 1, 0,  0.0, 0.0, 0.5,
            0, 1, 0,  0.0, 1.0, 0.0,
            0, 1, 1,  0.0, 0.5, 0.0,
            1, 1, 1,  1.0, 0.0, 0.0,
            1, 0, 1,  0.5, 0.0, 0.0,
            0, 0, 1,  0.3, 0.0, 0.3,
        )

        self.indices = glm.array(
            glm.uint32,
            2,0,3, 
            0,2,1, 
            5,1,2, 
            1,5,6, 
            4,6,5, 
            6,4,7, 
            3,7,4, 
            7,3,0, 
            3,5,2, 
            5,3,4, 
            7,1,6, 
            1,7,0, 
        )       
        # fmt: on

    def draw(self):
        pass


def main():
    settings = read_settings("settings.ini")
    display = (settings["DISPLAY_WIDTH"], settings["DISPLAY_HEIGHT"])

    # Pygame initialization
    pg.init()
    pg.display.set_mode(display, DOUBLEBUF | OPENGL)
    pg.mouse.set_visible(False)
    pg.event.set_grab(True)  # Lock mouse to window

    clock = pg.time.Clock()

    # Define geometry now
    my_object = newObject()
    my_vertices = my_object.vertices
    my_indices = my_object.indices

    cubePositions = (
        glm.vec3(2.0, 5.0, -15.0),
        glm.vec3(-1.5, -2.2, -2.5),
        glm.vec3(-3.8, -2.0, -12.3),
        glm.vec3(2.4, -0.4, -3.5),
        glm.vec3(-1.7, 3.0, -7.5),
        glm.vec3(1.3, -2.0, -2.5),
        glm.vec3(1.5, 2.0, -2.5),
        glm.vec3(1.5, 0.2, -1.5),
        glm.vec3(-1.3, 1.0, -1.5),
    )

    # Initialization code, should be done only once
    vao_ID = glGenVertexArrays(1)
    vbo_ID = glGenBuffers(1)
    ebo_ID = glGenBuffers(1)

    glBindVertexArray(vao_ID)
    glBindBuffer(GL_ARRAY_BUFFER, vbo_ID)
    glBufferData(
        GL_ARRAY_BUFFER,
        my_vertices.nbytes,
        my_vertices.ptr,
        GL_STATIC_DRAW,
    )
    glBindBuffer(GL_ELEMENT_ARRAY_BUFFER, ebo_ID)
    glBufferData(
        GL_ELEMENT_ARRAY_BUFFER, my_indices.nbytes, my_indices.ptr, GL_STATIC_DRAW
    )

    # position attribute
    glVertexAttribPointer(0, 3, GL_FLOAT, GL_FALSE, 6 * glm.sizeof(glm.float32), None)
    glEnableVertexAttribArray(0)
    # color attribute
    glVertexAttribPointer(
        1,
        3,
        GL_FLOAT,
        GL_FALSE,
        6 * glm.sizeof(glm.float32),
        ctypes.c_void_p(3 * sizeof(glm.float32)),
    )
    glEnableVertexAttribArray(1)

    ourShader = Shader("vertex_shader.vert", "fragment_shader.frag")

    # Defines camera "frustrum"
    glEnable(GL_DEPTH_TEST)
    glDepthFunc(GL_LESS)
    glEnable(GL_CULL_FACE)

    # Player starting position and camera variables
    camera = Camera(
        yaw=-90.0,
        pitch=0.0,
        speed=0.02,
        sensitivity=settings["MOUSE_SENSITIVITY"],
        fov=settings["FOV"],
        pos=glm.vec3(0.0, 0.0, 3.0),
        up=glm.vec3(0, 1, 0),
        front=glm.vec3(0, 0, -1),
    )

    # We will need to keep track of ticks
    current_ticks = 0
    last_ticks = 0

    while True:
        # Count frames rendered
        current_ticks = pg.time.get_ticks()
        delta_ticks = current_ticks - last_ticks
        last_ticks = current_ticks

        # handle events
        for event in pg.event.get():
            if event.type == pg.QUIT:
                pg.quit()
                sys.exit()
            if event.type == pg.KEYDOWN:
                if event.key == pg.K_ESCAPE:
                    pg.quit()
                    sys.exit()

        keys = pg.key.get_pressed()
        if keys[pg.K_w]:
            camera.process_keyboard(Directions.FORWARD, delta_ticks)
        if keys[pg.K_s]:
            camera.process_keyboard(Directions.BACKWARD, delta_ticks)
        if keys[pg.K_a]:
            camera.process_keyboard(Directions.LEFT, delta_ticks)
        if keys[pg.K_d]:
            camera.process_keyboard(Directions.RIGHT, delta_ticks)

        mouse_dx, mouse_dy = pg.mouse.get_rel()
        camera.process_mouse_movement(mouse_dx, mouse_dy, constrain_pitch=True)

        # clear previous screen
        glClearColor(0.2, 0.3, 0.3, 1)
        glClear(GL_COLOR_BUFFER_BIT | GL_DEPTH_BUFFER_BIT)

        # transformations and drawing
        # ===============================================
        ourShader.use()

        projection = glm.perspective(
            glm.radians(settings["FOV"]), (display[0] / display[1]), 0.1, 100.0
        )
        ourShader.setMat4("projection", glm.value_ptr(projection))

        view = camera.get_view_matrix()
        ourShader.setMat4("view", glm.value_ptr(view))

        glBindVertexArray(vao_ID)
        for i in range(len(cubePositions)):
            model = glm.mat4(1.0)
            model = glm.translate(model, cubePositions[i])

            ourShader.setMat4("model", glm.value_ptr(model))

            glDrawElements(GL_TRIANGLES, 36, GL_UNSIGNED_INT, None)
        # ===============================================

        # display to user
        pg.display.flip()

        # wait at 60 fps
        clock.tick(settings["FPS"])

        # Actual FPS
        # clock.get_fps()


if __name__ == "__main__":
    main()
