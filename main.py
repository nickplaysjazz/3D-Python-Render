import ctypes
import itertools
import pygame as pg
import sys

from OpenGL.GL import *
from OpenGL.GLU import *
from pathlib import Path
from pygame.locals import *
from pyglm import glm

from camera import Camera
from constants import Directions
from error_handling import raise_error
from setting_utils import read_settings
from shader_utils import Shader


class Object:
    def __init__(self, pos, lighting_shader):
        # fmt: off
        # vertices, colors, normals
        self.vertices = glm.array(
            glm.float32,
            # Position          # Normal
            # Back Face (z=0)
            0.0, 0.0, 0.0,      0.0,  0.0, -1.0,
            1.0, 0.0, 0.0,      0.0,  0.0, -1.0,
            1.0, 1.0, 0.0,      0.0,  0.0, -1.0,
            0.0, 1.0, 0.0,      0.0,  0.0, -1.0,

            # Front Face (z=1)
            0.0, 0.0, 1.0,      0.0,  0.0,  1.0,
            1.0, 0.0, 1.0,      0.0,  0.0,  1.0,
            1.0, 1.0, 1.0,      0.0,  0.0,  1.0,
            0.0, 1.0, 1.0,      0.0,  0.0,  1.0,

            # Left Face (x=0)
            0.0, 1.0, 1.0,     -1.0,  0.0,  0.0,
            0.0, 1.0, 0.0,     -1.0,  0.0,  0.0,
            0.0, 0.0, 0.0,     -1.0,  0.0,  0.0,
            0.0, 0.0, 1.0,     -1.0,  0.0,  0.0,

            # Right Face (x=1)
            1.0, 1.0, 1.0,      1.0,  0.0,  0.0,
            1.0, 1.0, 0.0,      1.0,  0.0,  0.0,
            1.0, 0.0, 0.0,      1.0,  0.0,  0.0,
            1.0, 0.0, 1.0,      1.0,  0.0,  0.0,

            # Bottom Face (y=0)
            0.0, 0.0, 0.0,      0.0, -1.0,  0.0,
            1.0, 0.0, 0.0,      0.0, -1.0,  0.0,
            1.0, 0.0, 1.0,      0.0, -1.0,  0.0,
            0.0, 0.0, 1.0,      0.0, -1.0,  0.0,

            # Top Face (y=1)
            0.0, 1.0, 0.0,      0.0,  1.0,  0.0,
            1.0, 1.0, 0.0,      0.0,  1.0,  0.0,
            1.0, 1.0, 1.0,      0.0,  1.0,  0.0,
            0.0, 1.0, 1.0,      0.0,  1.0,  0.0
        )

        self.indices = glm.array(
            glm.uint32,
            0,  1,  2,   2,  3,  0,   # Back
            4,  5,  6,   6,  7,  4,   # Front
            8,  9,  10,  10, 11, 8,   # Left
            12, 13, 14,  14, 15, 12,  # Right
            16, 17, 18,  18, 19, 16,  # Bottom
            20, 21, 22,  22, 23, 20   # Top
        )       
        # fmt: on

        self.pos = pos
        self.lighting_shader = lighting_shader


class Level:
    def __init__(self, object_list, light_object_list):
        self.vao = glGenVertexArrays(1)
        self.vbo = glGenBuffers(1)
        self.ebo = glGenBuffers(1)

        self.vao_lighting_obj = glGenVertexArrays(1)

        self.object_list = object_list

        chained_all_vertices = itertools.chain.from_iterable(
            [o.vertices for o in object_list]
        )
        chained_all_indices = itertools.chain.from_iterable(
            [o.indices for o in object_list]
        )

        self.all_vertices = glm.array(glm.float32, *list(chained_all_vertices))
        self.all_indices = glm.array(glm.uint32, *list(chained_all_indices))

        self.light_object_list = light_object_list

        # Some OpenGL initialization
        # 1. Generate OpenGL components
        # 2. Start recording into a VAO by binding it
        # 3. Bind VBO, which stores vertices
        # 4. Bind EBO, which stores indices to create faces
        # 5. Now tell the system how to handle data input. Position, color, textures, normals, etc
        # 6. Optionally, we now stop recording VAO by unbinding it. It is not necessary to unbind VBO/EBO separately

        glBindVertexArray(self.vao)
        glBindBuffer(GL_ARRAY_BUFFER, self.vbo)
        glBufferData(
            GL_ARRAY_BUFFER,
            self.all_vertices.nbytes,
            self.all_vertices.ptr,
            GL_STATIC_DRAW,
        )
        glBindBuffer(GL_ELEMENT_ARRAY_BUFFER, self.ebo)
        glBufferData(
            GL_ELEMENT_ARRAY_BUFFER,
            self.all_indices.nbytes,
            self.all_indices.ptr,
            GL_STATIC_DRAW,
        )
        # position attribute: x, y, z
        glVertexAttribPointer(
            0, 3, GL_FLOAT, GL_FALSE, 6 * glm.sizeof(glm.float32), None
        )
        glEnableVertexAttribArray(0)
        # normals
        glVertexAttribPointer(
            1,
            3,
            GL_FLOAT,
            GL_FALSE,
            6 * glm.sizeof(glm.float32),
            ctypes.c_void_p(3 * glm.sizeof(glm.float32)),
        )
        glEnableVertexAttribArray(1)
        glBindVertexArray(0)

        # Light VAO
        glBindVertexArray(self.vao_lighting_obj)
        glBindBuffer(GL_ARRAY_BUFFER, self.vbo)
        glBindBuffer(GL_ELEMENT_ARRAY_BUFFER, self.ebo)
        glVertexAttribPointer(
            0, 3, GL_FLOAT, GL_FALSE, 6 * glm.sizeof(glm.float32), None
        )
        glEnableVertexAttribArray(0)
        glVertexAttribPointer(
            1,
            3,
            GL_FLOAT,
            GL_FALSE,
            6 * glm.sizeof(glm.float32),
            ctypes.c_void_p(3 * glm.sizeof(glm.float32)),
        )
        glEnableVertexAttribArray(1)
        glBindVertexArray(0)


def draw_objects(current_vao, objects, current_shader, projection, view):
    # Enable the configuration (VAO) that we want to use
    glBindVertexArray(current_vao)

    # Draw elements of VAO
    # Assume one shader for simplicity
    current_shader.use()
    current_shader.setMat4("projection", glm.value_ptr(projection))
    current_shader.setMat4("view", glm.value_ptr(view))
    for i in objects:
        model = glm.mat4(1.0)
        model = glm.translate(model, i.pos)
        current_shader.setMat4("model", glm.value_ptr(model))
        glDrawElements(GL_TRIANGLES, len(i.indices), GL_UNSIGNED_INT, None)


def init_pg(display):
    # Pygame initialization
    pg.init()
    # Request OpenGL 3.3 context, fixes opengl error on Mac
    try:
        pg.display.gl_set_attribute(pg.GL_CONTEXT_MAJOR_VERSION, 3)
        pg.display.gl_set_attribute(pg.GL_CONTEXT_MINOR_VERSION, 3)
        pg.display.gl_set_attribute(
            pg.GL_CONTEXT_PROFILE_MASK, pg.GL_CONTEXT_PROFILE_CORE
        )
        # Might not need forward compatability, but it seems to work
        pg.display.gl_set_attribute(
            pg.GL_CONTEXT_FLAGS, pg.GL_CONTEXT_FORWARD_COMPATIBLE_FLAG
        )
    except Exception as e:
        raise_error(
            Path(__file__).name, "Failed to initialize OpenGL context with PyGame", e
        )

    pg.display.set_mode(display, DOUBLEBUF | OPENGL)
    pg.mouse.set_visible(False)
    pg.event.set_grab(True)  # Lock mouse to window


def main():
    settings = read_settings("settings.ini")
    display = (settings["DISPLAY_WIDTH"], settings["DISPLAY_HEIGHT"])

    init_pg(display)

    lighting_shader = Shader("vertex_shader.vert", "fragment_shader.frag")
    lighting_shader.use()
    lighting_shader.setVec3("objectColor", 1.0, 0.5, 0.31)
    lighting_shader.setVec3("lightColor", 1.0, 1.0, 1.0)

    light_object_shader = Shader(
        "vertex_shader.vert", "light_object_fragment_shader.frag"
    )

    # Define geometry now
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
    light_object_pos = glm.vec3(5, 3.0, 0)

    my_objects_list = [Object(c, lighting_shader) for c in cubePositions]
    my_lighting_object_list = [Object(light_object_pos, light_object_shader)]

    my_level = Level(my_objects_list, my_lighting_object_list)

    # Enable depth testing for drawing objects in correct order
    glEnable(GL_DEPTH_TEST)
    glDepthFunc(GL_LESS)
    # Also do not render backfaces to save render time
    # glEnable(GL_CULL_FACE)

    clock = pg.time.Clock()

    camera = Camera(
        yaw=-90.0,
        pitch=0.0,
        speed=0.01,
        sensitivity=settings["MOUSE_SENSITIVITY"],
        fov=settings["FOV"],
        pos=glm.vec3(0.0, 0.0, 3.0),
        up=glm.vec3(0, 1, 0),
        front=glm.vec3(0, 0, -1),
        world_up=glm.vec3(0, 1, 0),
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
        camera.process_mouse_movement(mouse_dx, -mouse_dy, constrain_pitch=True)

        # clear previous screen
        glClearColor(0.0, 0.0, 0.0, 1.0)
        glClear(GL_COLOR_BUFFER_BIT | GL_DEPTH_BUFFER_BIT)

        rad = pg.time.get_ticks() / 1000
        light_object_pos = glm.vec3(5 * glm.cos(rad), 3.0, 5 * glm.sin(rad))

        my_level.light_object_list[0].pos = light_object_pos

        lighting_shader.use()
        lighting_shader.setVec3(
            "lightPos", light_object_pos.x, light_object_pos.y, light_object_pos.z
        )

        # We could've defined this outside the game loop since it stays static
        projection = glm.perspective(
            glm.radians(settings["FOV"]), (display[0] / display[1]), 0.1, 100.0
        )

        view = camera.get_view_matrix()

        draw_objects(
            my_level.vao, my_level.object_list, lighting_shader, projection, view
        )
        draw_objects(
            my_level.vao_lighting_obj,
            my_level.light_object_list,
            light_object_shader,
            projection,
            view,
        )

        # display to user
        pg.display.flip()

        # wait at 60 fps
        clock.tick(settings["FPS"])

        # Actual FPS
    # print(clock.get_fps())


if __name__ == "__main__":
    main()
