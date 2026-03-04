from pathlib import Path
from OpenGL.GL import *

from error_handling import raise_error


class Shader:
    def __init__(self, vertex_shader_filename, fragment_shader_filename):
        # 1. Read in shader files
        SHADER_DIR = Path(__file__).resolve().parent / "shaders"
        vertex_shader_filepath = SHADER_DIR / vertex_shader_filename
        fragment_shader_filepath = SHADER_DIR / fragment_shader_filename

        try:
            vertex_shader_file = open(vertex_shader_filepath, "r")
            fragment_shader_file = open(fragment_shader_filepath, "r")
        except Exception as e:
            raise_error(Path(__file__).name, "Shader file loading failed", e)

        # 2. Compile shaders
        vertex_shader = glCreateShader(GL_VERTEX_SHADER)
        glShaderSource(vertex_shader, vertex_shader_file)
        glCompileShader(vertex_shader)
        success = True
        glGetShaderiv(vertex_shader, GL_COMPILE_STATUS, success)
        if not success:
            info_log = ""
            glGetShaderInfoLog(vertex_shader, info_log)
            raise_error(
                Path(__file__).name, "Vertex shader compilation failed", info_log
            )

        fragment_shader = glCreateShader(GL_FRAGMENT_SHADER)
        glShaderSource(fragment_shader, fragment_shader_file)
        glCompileShader(fragment_shader)
        success = True
        glGetShaderiv(fragment_shader, GL_COMPILE_STATUS, success)
        if not success:
            info_log = ""
            glGetShaderInfoLog(fragment_shader, info_log)
            raise_error(
                Path(__file__).name, "Fragment shader compilation failed", info_log
            )

        # 3. Link shader program
        self.ID = glCreateProgram()
        glAttachShader(self.ID, vertex_shader)
        glAttachShader(self.ID, fragment_shader)
        glLinkProgram(self.ID)

        glGetProgramiv(self.ID, GL_LINK_STATUS, success)
        if not success:
            glGetProgramInfoLog(self.ID, info_log)
            raise_error(Path(__file__).name, "Shader program linking failed", info_log)

        # 4. Delete unnecessary shaders
        glDeleteShader(vertex_shader)
        glDeleteShader(fragment_shader)

    def use(self):
        glUseProgram(self.ID)

    def setBool(self, name, value):
        glUniform1i(glGetUniformLocation(self.ID, name), value)

    def setInt(self, name, value):
        self.setBool(name, value)

    def setFloat(self, name, value):
        glUniform1f(glGetUniformLocation(self.ID, name), value)

    def setMat4(self, name, value):
        glUniformMatrix4fv(glGetUniformLocation(self.ID, name), 1, GL_FALSE, value)
