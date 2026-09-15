import glm

from OpenGL.GL import *
from OpenGL.GLU import *

from constants import skybox_vertices


def draw_skybox(skybox_vao, skybox_shader, cubemap_texture, projection, view):
    glBindVertexArray(skybox_vao)

    # Skybox must always be behind
    glDepthFunc(GL_LEQUAL)

    skybox_shader.use()

    view_no_translation = glm.mat4(glm.mat3(view))

    skybox_shader.setMat4("projection", glm.value_ptr(projection))
    skybox_shader.setMat4("view", glm.value_ptr(view_no_translation))

    glBindVertexArray(skybox_vao)
    glActiveTexture(GL_TEXTURE0)
    glBindTexture(GL_TEXTURE_CUBE_MAP, cubemap_texture)
    skybox_shader.setInt("skybox", 0)

    glDrawArrays(GL_TRIANGLES, 0, 36)

    # Reset depth function
    glBindVertexArray(0)
    glDepthFunc(GL_LESS)


def create_skybox_vao(): 
    skybox_data = glm.array(glm.float32, *skybox_vertices)

    skybox_vao = glGenVertexArrays(1)
    skybox_vbo = glGenBuffers(1)

    glBindVertexArray(skybox_vao)
    glBindBuffer(GL_ARRAY_BUFFER, skybox_vbo)
    glBufferData(GL_ARRAY_BUFFER, skybox_data.nbytes, skybox_data.ptr, GL_STATIC_DRAW)

    glEnableVertexAttribArray(0)
    glVertexAttribPointer(0, 3, GL_FLOAT, GL_FALSE, 3 * glm.sizeof(glm.float32), None)

    glBindVertexArray(0)
    return skybox_vao
