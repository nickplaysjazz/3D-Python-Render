import ctypes
import glm

from OpenGL.GL import *
from OpenGL.GLU import *


def create_aabb_vao():
    # 24 vertices defining the 12 lines of a unit cube
    vertices = [
        0,0,0,  1,0,0,
        1,0,0,  1,1,0,
        1,1,0,  0,1,0,
        0,1,0,  0,0,0,
        0,0,1,  1,0,1,
        1,0,1,  1,1,1,
        1,1,1,  0,1,1,
        0,1,1,  0,0,1,
        0,0,0,  0,0,1,
        1,0,0,  1,0,1,
        1,1,0,  1,1,1,
        0,1,0,  0,1,1
    ]
    
    vertices_array = glm.array(glm.float32, *vertices)

    vao = glGenVertexArrays(1)
    vbo = glGenBuffers(1)

    glBindVertexArray(vao)
    glBindBuffer(GL_ARRAY_BUFFER, vbo)
    glBufferData(GL_ARRAY_BUFFER, vertices_array.nbytes, vertices_array.ptr, GL_STATIC_DRAW)

    # Position attribute (location = 0)
    glEnableVertexAttribArray(0)
    glVertexAttribPointer(0, 3, GL_FLOAT, GL_FALSE, 3 * 4, ctypes.c_void_p(0))

    glBindBuffer(GL_ARRAY_BUFFER, 0)
    glBindVertexArray(0)

    return vao

def render_debug_aabbs(aabb_vao, debug_shader, object_list, view_matrix, projection_matrix):
    debug_shader.use()
    debug_shader.setMat4("view", glm.value_ptr(view_matrix))
    debug_shader.setMat4("projection", glm.value_ptr(projection_matrix))

    glBindVertexArray(aabb_vao)

    for obj in object_list:
        if not hasattr(obj, 'local_aabb'):
            continue
            
        box_min = obj.local_aabb["min"]
        box_max = obj.local_aabb["max"]
        size = box_max - box_min
        
        # 1. Apply object world transforms
        model = glm.mat4(1.0)
        model = glm.translate(model, obj.pos)
        if obj.rotation.y != 0.0:
            model = glm.rotate(model, glm.radians(obj.rotation.y), glm.vec3(0.0, 1.0, 0.0))
        if obj.rotation.x != 0.0:
            model = glm.rotate(model, glm.radians(obj.rotation.x), glm.vec3(1.0, 0.0, 0.0))
        if obj.rotation.z != 0.0:
            model = glm.rotate(model, glm.radians(obj.rotation.z), glm.vec3(0.0, 0.0, 1.0))
        
        # 2. Offset to local box bounds and scale
        model = glm.translate(model, box_min)
        model = glm.scale(model, size)
        
        debug_shader.setMat4("model", glm.value_ptr(model))
        glDrawArrays(GL_LINES, 0, 24)

    glBindVertexArray(0)