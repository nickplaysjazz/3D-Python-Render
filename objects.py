import array
import glm
import pygame as pg

from OpenGL.GL import *
from OpenGL.GLU import *
from pathlib import Path

from error_handling import raise_error


class Object:
    def __init__(
        self,
        pos,
        filename=None,
        lighting_shader=None,
        rotation=None,
        texture_filename=None,
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
            glTexParameteri(
                GL_TEXTURE_2D, GL_TEXTURE_MIN_FILTER, GL_LINEAR_MIPMAP_LINEAR
            )
            glTexParameteri(GL_TEXTURE_2D, GL_TEXTURE_MAG_FILTER, GL_LINEAR)

            # Generate texture and mipmaps
            glTexImage2D(
                GL_TEXTURE_2D,
                0,
                GL_RGBA,
                width,
                height,
                0,
                GL_RGBA,
                GL_UNSIGNED_BYTE,
                image_data,
            )
            glGenerateMipmap(GL_TEXTURE_2D)

            return texture_id
        except Exception as e:
            print(f"Failed to load texture {texture_path}: {e}")
            return 0

    @staticmethod
    def compute_local_aabb(local_vertices):
        """
        Computes the static local min/max bounds directly from the un-transformed vertices.
        """
        min_x = min_y = min_z = float("inf")
        max_x = max_y = max_z = float("-inf")

        for i in range(0, len(local_vertices), 8):
            vx, vy, vz = local_vertices[i], local_vertices[i + 1], local_vertices[i + 2]

            if vx < min_x:
                min_x = vx
            if vx > max_x:
                max_x = vx
            if vy < min_y:
                min_y = vy
            if vy > max_y:
                max_y = vy
            if vz < min_z:
                min_z = vz
            if vz > max_z:
                max_z = vz

        return {
            "min": glm.vec3(min_x, min_y, min_z),
            "max": glm.vec3(max_x, max_y, max_z),
        }


class NetworkPlayer(Object):
    """Renderable remote player whose transform is driven by network snapshots."""

    def __init__(self, pos, lighting_shader=None, filename="sphere.obj"):
        super().__init__(pos, filename, lighting_shader)
        self.player_id = None
        self.active = False
        self.target_pos = glm.vec3(pos)
        self.target_rotation = glm.vec3(0.0)

    def assign(self, player_id, pos, rotation):
        self.player_id = player_id
        self.active = True
        self.pos = glm.vec3(pos)
        self.target_pos = glm.vec3(pos)
        self.rotation = glm.vec3(rotation)
        self.target_rotation = glm.vec3(rotation)

    def release(self):
        self.active = False
        self.player_id = None
        self.pos = glm.vec3(0.0, -1000.0, 0.0)
        self.target_pos = glm.vec3(self.pos)

    def update_interpolation(self, factor):
        self.pos = glm.mix(self.pos, self.target_pos, min(1.0, max(0.0, factor)))
        self.rotation = glm.mix(
            self.rotation, self.target_rotation, min(1.0, max(0.0, factor))
        )
