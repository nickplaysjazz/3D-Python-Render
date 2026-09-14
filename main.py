import ctypes
import glm
import json
import pygame as pg
import sys

from OpenGL.GL import *
from OpenGL.GLU import *
from pathlib import Path
from pygame.locals import *

from camera import Camera
from collision import check_collision
from constants import Directions
from debug import create_aabb_vao, render_debug_aabbs
from error_handling import raise_error
from levels import Level
from objects import Object
from setting_utils import read_settings
from skybox import create_skybox_vao, draw_skybox
from shader_utils import Shader


def draw_objects(current_vao, objects, current_shader, projection, view):
    # Enable the configuration (VAO) that we want to use
    glBindVertexArray(current_vao)

    # Draw elements of VAO
    current_shader.use()
    current_shader.setMat4("projection", glm.value_ptr(projection))
    current_shader.setMat4("view", glm.value_ptr(view))
    
    for i in objects:
        model = glm.mat4(1.0)
        model = glm.translate(model, i.pos)
        if i.rotation.y != 0.0:
            model = glm.rotate(model, glm.radians(i.rotation.y), glm.vec3(0.0, 1.0, 0.0))
        if i.rotation.x != 0.0:
            model = glm.rotate(model, glm.radians(i.rotation.x), glm.vec3(1.0, 0.0, 0.0))
        if i.rotation.z != 0.0:
            model = glm.rotate(model, glm.radians(i.rotation.z), glm.vec3(0.0, 0.0, 1.0))
        current_shader.setMat4("model", glm.value_ptr(model))

        # bind texture if present
        if i.texture_id:
            glActiveTexture(GL_TEXTURE0)
            glBindTexture(GL_TEXTURE_2D, i.texture_id)
            current_shader.setInt("useTexture", 1)
        else:
            glActiveTexture(GL_TEXTURE0)
            glBindTexture(GL_TEXTURE_2D, 0)
            current_shader.setInt("useTexture", 0)

        glDrawElements(
            GL_TRIANGLES, i.index_count, GL_UNSIGNED_INT, ctypes.c_void_p(i.byte_offset)
        )

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

def load_level_from_json(filepath, main_shader, light_shader):
    cubemap_texture = 0
    scene_objects = []
    light_objects = []

    try: 
        with open(filepath, 'r') as f:
            level_data = json.load(f)

        # scene objects 
        for obj_data in level_data.get("scene_objects", []):
            pos = glm.vec3(*obj_data["position"])
            rot = glm.vec3(*obj_data.get("rotation", [0.0, 0.0, 0.0]))
            filename = obj_data["filename"]
            tex_filename = obj_data.get("texture_filename")
            
            # 1. Instantiate the object
            new_obj = Object(pos, filename, main_shader, rotation=rot, texture_filename=tex_filename)
            
            # 2. Extract collision data from JSON and set it
            new_obj.collision = obj_data.get("collision", False)
            
            # 3. If collision is enabled, compute and store the AABB
            if new_obj.collision:
                new_obj.local_aabb = Object.compute_local_aabb(new_obj.vertices)
                
            scene_objects.append(new_obj)

        # lighting objects
        for obj_data in level_data.get("lighting_objects", []):
            pos = glm.vec3(*obj_data["position"])
            rot = glm.vec3(*obj_data.get("rotation", [0.0, 0.0, 0.0]))
            filename = obj_data["filename"]
            tex_filename = obj_data.get("texture_filename")
            
            light_objects.append(
                Object(pos, filename, light_shader, rotation=rot, texture_filename=tex_filename)
            )

        # skybox
        skybox_dir = level_data.get("skybox")
        if skybox_dir:
            face_filenames = ["right.png", "left.png", "top.png", "bottom.png", "front.png", "back.png"]

            cubemap_texture = glGenTextures(1)
            glBindTexture(GL_TEXTURE_CUBE_MAP, cubemap_texture)

            ASSET_DIR = Path(__file__).resolve().parent / "assets"
            for i, filename in enumerate(face_filenames):
                face_path = ASSET_DIR / skybox_dir / filename
                
                surface = pg.image.load(face_path)
                image_data = pg.image.tostring(surface, "RGB", False)
                width = surface.get_width()
                height = surface.get_height()

                # Upload face pixel data to corresponding OpenGL Cubemap target
                target = GL_TEXTURE_CUBE_MAP_POSITIVE_X + i
                glTexImage2D(
                    target, 0, GL_RGB, width, height, 0,
                    GL_RGB, GL_UNSIGNED_BYTE, image_data
                )

            # Set cubemap filtering and wrapping rules
            glTexParameteri(GL_TEXTURE_CUBE_MAP, GL_TEXTURE_MIN_FILTER, GL_LINEAR)
            glTexParameteri(GL_TEXTURE_CUBE_MAP, GL_TEXTURE_MAG_FILTER, GL_LINEAR)
            glTexParameteri(GL_TEXTURE_CUBE_MAP, GL_TEXTURE_WRAP_S, GL_CLAMP_TO_EDGE)
            glTexParameteri(GL_TEXTURE_CUBE_MAP, GL_TEXTURE_WRAP_T, GL_CLAMP_TO_EDGE)
            glTexParameteri(GL_TEXTURE_CUBE_MAP, GL_TEXTURE_WRAP_R, GL_CLAMP_TO_EDGE)

            glBindTexture(GL_TEXTURE_CUBE_MAP, 0)
        
    except Exception as e:
            raise_error(Path(__file__).name, "Level loading failed", e)

    return scene_objects, light_objects, cubemap_texture


def main():
    settings = read_settings("settings.ini")
    display = (settings["DISPLAY_WIDTH"], settings["DISPLAY_HEIGHT"])

    init_pg(display)

    # Define things for shaders
    lighting_shader = Shader("vertex_shader.vert", "fragment_shader.frag")
    lighting_shader.use()
    lighting_shader.setVec3("objectColor", 1.0, 0.5, 0.31)
    lighting_shader.setVec3("lightColor", 1.0, 1.0, 1.0)

    lighting_shader.setVec3("lightPos", 0.0, 10.0, 0.0)

    light_object_shader = Shader(
        "vertex_shader.vert", "light_object_fragment_shader.frag"
    )

    skybox_shader = Shader("skybox.vert", "skybox.frag")

    # load geometry from level json file
    my_objects_list, my_lighting_object_list, skybox_texture = load_level_from_json(
        "levels/texture_land.json", 
        lighting_shader, 
        light_object_shader
    )

    my_level = Level(my_objects_list, my_lighting_object_list)
    skybox_vao = create_skybox_vao()
    aabb_vao = create_aabb_vao()

    # Enable depth testing for drawing objects in correct order
    glEnable(GL_DEPTH_TEST)
    glDepthFunc(GL_LESS)
    # Also do not render backfaces to save render time
    glEnable(GL_CULL_FACE)

    clock = pg.time.Clock()

    camera = Camera(
        yaw=-90.0,
        pitch=0.0,
        speed=0.01,
        sensitivity=settings["MOUSE_SENSITIVITY"],
        fov=settings["FOV"],
        pos=glm.vec3(0.0, 5.0, 0.0),
        up=glm.vec3(0, 1, 0),
        front=glm.vec3(0, 0, -1),
        world_up=glm.vec3(0, 1, 0),
    )

    current_ticks = 0
    last_ticks = 0

    show_collision_boxes = False
    
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
                # Toggled in keydown loop to prevent strobing true/false
                if event.key == pg.K_BACKQUOTE:
                    show_collision_boxes = not show_collision_boxes

        moved = False

        keys = pg.key.get_pressed()
        if keys[pg.K_w]:
            camera.process_keyboard(Directions.FORWARD, delta_ticks)
            moved = True
        if keys[pg.K_s]:
            camera.process_keyboard(Directions.BACKWARD, delta_ticks)
            moved = True
        if keys[pg.K_a]:
            camera.process_keyboard(Directions.LEFT, delta_ticks)
            moved = True
        if keys[pg.K_d]:
            camera.process_keyboard(Directions.RIGHT, delta_ticks)
            moved = True

        # check for collisions
        if moved:
            # Iteratively push the player out of any intersecting objects
            # using the local-space surface normal calculated in check_collision
            for obj in my_level.object_list:
                if getattr(obj, "collision", False):
                    is_colliding, push_vector = check_collision(camera.pos, obj)
                    if is_colliding:
                        camera.pos += push_vector

        mouse_dx, mouse_dy = pg.mouse.get_rel()
        camera.process_mouse_movement(mouse_dx, -mouse_dy, constrain_pitch=True)

        # clear previous screen
        glClearColor(0.0, 0.0, 0.0, 1.0)
        glClear(GL_COLOR_BUFFER_BIT | GL_DEPTH_BUFFER_BIT)

        # compute/update values for animated objects
        rad = pg.time.get_ticks() / 1000
        light_object_pos = glm.vec3(3 * glm.cos(rad), 10.0, 3 * glm.sin(rad))
        my_level.light_object_list[0].pos = light_object_pos
        lighting_shader.use()
        lighting_shader.setVec3(
            "lightPos", light_object_pos.x, light_object_pos.y, light_object_pos.z
        )

        projection = glm.perspective(
            glm.radians(settings["FOV"]), (display[0] / display[1]), 0.1, 100.0
        )

        view = camera.get_view_matrix()

        # Draw objects within level: geometries and lighting objects
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

        # Draw AABB collision boxes if toggled
        if show_collision_boxes:
            render_debug_aabbs(
                aabb_vao, 
                light_object_shader,  # Using the light shader as a basic fallback uniform color 
                my_level.object_list, 
                view, 
                projection
            )

        # Render skybox last
        if skybox_texture:
            draw_skybox(
                skybox_vao,
                skybox_shader,
                skybox_texture,
                projection,
                view
            )

        # display to user
        pg.display.flip()

        # wait at 60 fps
        clock.tick(settings["FPS"])

if __name__ == "__main__":
    main()