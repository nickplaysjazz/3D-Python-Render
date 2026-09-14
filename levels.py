import ctypes
import glm

from OpenGL.GL import *
from OpenGL.GLU import *

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
            # (Index count so far * 4 bytes per 32-bit uint)
            obj.byte_offset = current_i_offset * 4 

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