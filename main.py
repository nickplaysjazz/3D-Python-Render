import array
import ctypes
import json
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
    def __init__(
        self,
        pos,
        filename=None,
        lighting_shader=None,
        rotation=None,
        texture_filename=None
    ):
        self.pos = pos
        self.rotation = rotation if rotation is not None else glm.vec3(0.0, 0.0, 0.0)
        self.filename = filename
        self.lighting_shader = lighting_shader
        self.texture_filename = texture_filename

        self.vertices = None
        self.indices = None
        self.texture_id = 0

        # Tracking for global buffers
        self.index_count = 0
        self.byte_offset = 0

        ASSET_DIR = Path(__file__).resolve().parent / "assets"
        self.filepath = ASSET_DIR / self.filename if self.filename else None

        if self.texture_filename:
            # FIXME
            self.texture_id = self.load_texture(ASSET_DIR / self.texture_filename)

        if self.filepath and self.filepath.exists():
            self.load_obj()
            self.index_count = len(self.indices)

    def load_obj(self):
        raw_v = []
        raw_vn = []
        raw_vt = []

        # Unique (Position, Normal, TexCoord) tuples as keys and their assigned index as values
        vertex_cache = {}

        # quick double check for cross-compatability
        if array.array("I").itemsize != 4:
            raise_error(
                Path(__file__).name,
                "Expected 32-bit unsigned integers. Change type code in load_obj()?",
            )
        if array.array("f").itemsize != 4:
            raise_error(
                Path(__file__).name,
                "Expected 32-bit floats. Change type code in load_obj()?",
            )

        # float is 4 byte = 32 bits
        self.vertices = array.array("f")
        # unsigned 4 byte = 32-bit integers
        self.indices = array.array("I")
        current_index = 0

        with open(self.filepath, "r") as f:
            for line in f:
                if line.startswith("v "):
                    raw_v.append([float(x) for x in line.split()[1:4]])
                elif line.startswith("vn "):
                    raw_vn.append([float(x) for x in line.split()[1:4]])
                elif line.startswith("vt "):
                    # uv coords have only 2 components
                    raw_vt.append([float(x) for x in line.split()[1:3]])
                elif line.startswith("f "):
                    parts = line.split()[1:]
                    for part in parts:
                        # Extract indices from string (v/vt/vn)
                        idx_parts = part.split("/")
                        v_idx = int(idx_parts[0]) - 1 if idx_parts[0] else None
                        vt_idx = (
                            int(idx_parts[1]) - 1
                            if (len(idx_parts) >= 2 and idx_parts[1])
                            else None
                        )
                        vn_idx = (
                            int(idx_parts[2]) - 1
                            if (len(idx_parts) >= 3 and idx_parts[2])
                            else None
                        )

                        # fallback values here
                        pos = (
                            tuple(raw_v[v_idx])
                            if (v_idx is not None and 0 <= v_idx < len(raw_v))
                            else (0.0, 0.0, 0.0)
                        )
                        norm = (
                            tuple(raw_vn[vn_idx])
                            if (vn_idx is not None and 0 <= vn_idx < len(raw_vn))
                            else (0.0, 1.0, 0.0)
                        )
                        tex = (
                            tuple(raw_vt[vt_idx])
                            if (vt_idx is not None and 0 <= vt_idx < len(raw_vt))
                            else (0.0, 0.0)
                        )
                        vertex_package = (pos, norm, tex)

                        # Check if vertex has already been seen
                        if vertex_package in vertex_cache:
                            self.indices.append(vertex_cache[vertex_package])
                        else:
                            vertex_cache[vertex_package] = current_index
                            self.indices.append(current_index)

                            self.vertices.extend(pos)
                            self.vertices.extend(norm)
                            self.vertices.extend(tex)
                            current_index += 1

    def load_texture(self, texture_path):
        if not texture_path or not texture_path.exists():
            return 0
        try:
            # Load image and convert to alpha for consistent RGBA format
            image = pg.image.load(str(texture_path)).convert_alpha()
            
            if hasattr(pg.image, "tobytes"):
                image_data = pg.image.tobytes(image, "RGBA", True)
            else:
                image_data = pg.image.tostring(image, "RGBA", True)
            width, height = image.get_size()

            texture_id = glGenTextures(1)
            glBindTexture(GL_TEXTURE_2D, texture_id)

            # Set texture wrapping and filtering options
            glTexParameteri(GL_TEXTURE_2D, GL_TEXTURE_WRAP_S, GL_REPEAT)
            glTexParameteri(GL_TEXTURE_2D, GL_TEXTURE_WRAP_T, GL_REPEAT)
            glTexParameteri(GL_TEXTURE_2D, GL_TEXTURE_MIN_FILTER, GL_LINEAR_MIPMAP_LINEAR)
            glTexParameteri(GL_TEXTURE_2D, GL_TEXTURE_MAG_FILTER, GL_LINEAR)

            # Generate texture and mipmaps
            glTexImage2D(GL_TEXTURE_2D, 0, GL_RGBA, width, height, 0, GL_RGBA, GL_UNSIGNED_BYTE, image_data)
            glGenerateMipmap(GL_TEXTURE_2D)

            return texture_id
        except Exception as e:
            print(f"Failed to load texture {texture_path}: {e}")
            return 0


class Level:
    def __init__(self, object_list, light_object_list):
        self.vao = glGenVertexArrays(1)
        self.vbo = glGenBuffers(1)
        self.ebo = glGenBuffers(1)

        self.vao_lighting_obj = glGenVertexArrays(1)

        self.object_list = object_list
        self.light_object_list = light_object_list

        all_objs = object_list + light_object_list

        current_v_offset = 0
        current_i_offset = 0

        processed_vertices = []
        processed_indices = []

        for obj in all_objs:
            # Store the byte offset for glDrawElements
            # (Index count so far * size of uint32)
            obj.byte_offset = current_i_offset * sizeof(int32_t)

            # offset the indices themselves so they point to the correct vertices in the combined VBO
            offset_indices = [i + current_v_offset for i in obj.indices]

            processed_vertices.extend(obj.vertices)
            processed_indices.extend(offset_indices)

            # Increment offsets for the NEXT object
            # vertices are stored as [x,y,z,nx,ny,nz, u, v], so divide by 8 for count
            current_v_offset += len(obj.vertices) // 8
            current_i_offset += len(obj.indices)

        self.all_vertices = glm.array(glm.float32, *processed_vertices)
        self.all_indices = glm.array(glm.uint32, *processed_indices)

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
            0, 3, GL_FLOAT, GL_FALSE, 8 * glm.sizeof(glm.float32), None
        )
        glEnableVertexAttribArray(0)

        # normals nx, ny, nz
        glVertexAttribPointer(
            1,
            3,
            GL_FLOAT,
            GL_FALSE,
            8 * glm.sizeof(glm.float32),
            ctypes.c_void_p(3 * glm.sizeof(glm.float32)),
        )
        glEnableVertexAttribArray(1)
        # texture coords attribute (u, v)
        glVertexAttribPointer(
            2,
            2,
            GL_FLOAT,
            GL_FALSE,
            8 * glm.sizeof(glm.float32),
            ctypes.c_void_p(6 * glm.sizeof(glm.float32)),
        )
        glEnableVertexAttribArray(2)
        glBindVertexArray(0)

        # Light VAO
        # probably doesn't need textures, but keep the stride anyway
        glBindVertexArray(self.vao_lighting_obj)
        glBindBuffer(GL_ARRAY_BUFFER, self.vbo)
        glBindBuffer(GL_ELEMENT_ARRAY_BUFFER, self.ebo)
        glVertexAttribPointer(
            0, 3, GL_FLOAT, GL_FALSE, 8 * glm.sizeof(glm.float32), None
        )
        glEnableVertexAttribArray(0)
        glVertexAttribPointer(
            1,
            3,
            GL_FLOAT,
            GL_FALSE,
            8 * glm.sizeof(glm.float32),
            ctypes.c_void_p(3 * glm.sizeof(glm.float32)),
        )
        glEnableVertexAttribArray(1)
        glVertexAttribPointer(
            2,
            2,
            GL_FLOAT,
            GL_FALSE,
            8 * glm.sizeof(glm.float32),
            ctypes.c_void_p(6 * glm.sizeof(glm.float32)),
        )
        glEnableVertexAttribArray(2)
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

def load_level_from_json(filepath, main_shader, light_shader):
    try: 
        with open(filepath, 'r') as f:
            level_data = json.load(f)

        scene_objects = []
        light_objects = []

        # scene objects 
        for obj_data in level_data.get("scene_objects", []):
            pos = glm.vec3(*obj_data["position"])
            rot = glm.vec3(*obj_data.get("rotation", [0.0, 0.0, 0.0]))
            filename = obj_data["filename"]
            tex_filename = obj_data.get("texture_filename")
            
            scene_objects.append(
                Object(pos, filename, main_shader, rotation=rot, texture_filename=tex_filename)
            )

        # lighting objects
        for obj_data in level_data.get("lighting_objects", []):
            pos = glm.vec3(*obj_data["position"])
            rot = glm.vec3(*obj_data.get("rotation", [0.0, 0.0, 0.0]))
            filename = obj_data["filename"]
            tex_filename = obj_data.get("texture_filename")
            
            light_objects.append(
                Object(pos, filename, light_shader, rotation=rot, texture_filename=tex_filename)
            )
    except Exception as e:
            raise_error(Path(__file__).name, "Level loading failed", e)

    return scene_objects, light_objects


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

    # load geometry from level json file
    my_objects_list, my_lighting_object_list = load_level_from_json(
        "levels/texture_land.json", 
        lighting_shader, 
        light_object_shader
    )

    my_level = Level(my_objects_list, my_lighting_object_list)

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

        # compute/update values for animated objects
        # rad = pg.time.get_ticks() / 1000
        # light_object_pos = glm.vec3(1 * glm.cos(rad), 1.0, 1 * glm.sin(rad))
        # my_level.light_object_list[0].pos = light_object_pos
        # lighting_shader.use()
        # lighting_shader.setVec3(
            # "lightPos", light_object_pos.x, light_object_pos.y, light_object_pos.z
        # )

        # Now get projection & view matrices
        # We could've defined projection outside the game loop since it stays static
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

        # display to user
        pg.display.flip()

        # wait at 60 fps
        clock.tick(settings["FPS"])

        # Actual FPS
        # print(clock.get_fps())


if __name__ == "__main__":
    main()
