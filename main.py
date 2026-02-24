import configparser
import math
import numpy as np
import pygame as pg
import sys

from pathlib import Path
from pygame.locals import *
from OpenGL.GL import *
from OpenGL.GLU import *


class Level:
    def __init__(self, objects):
        self.objects = objects
        self.navmesh = self.update_navmesh()
        self.navmesh_padding = 0.3

    def update_navmesh(self):
        xz_vertices = [
            (obj.x1, obj.z1, obj.x2, obj.z2)
            for obj in self.objects
            if obj.clipping == True
        ]
        navmesh = self.union_of_rectangles(xz_vertices)
        return navmesh

    def is_in_navmesh(self, x, z):
        for n in self.navmesh:
            if (
                (x > n[0] - self.navmesh_padding)
                and (x < n[2] + self.navmesh_padding)
                and (z > n[1] - self.navmesh_padding)
                and (z < n[3] + self.navmesh_padding)
            ):
                return True
        return False

    def merge_intervals(self, intervals):
        if not intervals:
            return []
        sorted_intervals = sorted(intervals, key=lambda x: x[0])
        merged = []
        curr_start, curr_end = sorted_intervals[0]
        for nxt_start, nxt_end in sorted_intervals[1:]:
            if nxt_start <= curr_end:
                curr_end = max(curr_end, nxt_end)
            else:
                merged.append((curr_start, curr_end))
                curr_start, curr_end = nxt_start, nxt_end
        merged.append((curr_start, curr_end))
        return merged

    def union_of_rectangles(self, rects):
        """
        rects: List of (x1, z1, x2, z2)
        Returns: List of disjoint (x1, z1, x2, z2) representing the union.
        """
        x_coords = sorted(list(set([r[0] for r in rects] + [r[2] for r in rects])))

        disjoint_rects = []

        for i in range(len(x_coords) - 1):
            x_start = min(x_coords[i], x_coords[i + 1])
            x_end = max(x_coords[i], x_coords[i + 1])

            active_z_ranges = []
            for x1, z1, x2, z2 in rects:
                if min(x1, x2) <= x_start and max(x1, x2) >= x_end:
                    active_z_ranges.append((z1, z2))

            merged_z = self.merge_intervals(active_z_ranges)

            for z_start, z_end in merged_z:
                disjoint_rects.append((x_start, z_start, x_end, z_end))

        return disjoint_rects


class RectangleObject:
    def __init__(
        self,
        pos1,
        pos2,
        body_color=(0.1, 0.1, 0.1),
        edge_color=(1, 1, 1),
        draw_body=True,
        draw_edges=False,
        clipping=True,
    ):
        self.x1, self.y1, self.z1 = pos1
        self.x2, self.y2, self.z2 = pos2

        self.width = self.x2 - self.x1
        self.height = self.y2 - self.y1
        self.depth = self.z2 - self.z1

        self.body_color = body_color
        self.edge_color = edge_color

        unscaled_vertices = (
            (0, 0, 0),
            (1, 0, 0),
            (1, 1, 0),
            (0, 1, 0),
            (0, 1, 1),
            (1, 1, 1),
            (1, 0, 1),
            (0, 0, 1),
        )
        self.vertices = tuple(
            tuple(
                (val * s) + shift
                for val, s, shift in zip(
                    vertex, (self.width, self.height, self.depth), pos1
                )
            )
            for vertex in unscaled_vertices
        )

        self.edges = (
            (0, 1),
            (1, 2),
            (2, 3),
            (3, 0),
            (4, 5),
            (5, 6),
            (6, 7),
            (7, 4),
            (3, 4),
            (0, 7),
            (1, 6),
            (5, 2),
        )
        self.quads = (
            (2, 3, 0, 1),
            (5, 2, 1, 6),
            (4, 5, 6, 7),
            (3, 4, 7, 0),
            (3, 2, 5, 4),
            (7, 6, 1, 0),
        )

        self.draw_body = draw_body
        self.draw_edges = draw_edges

        self.clipping = clipping

    def draw(self):
        if self.draw_edges:
            glBegin(GL_LINES)
            glColor3fv(self.edge_color)
            for edge in self.edges:
                for vertex in edge:
                    glVertex3fv(self.vertices[vertex])
            glEnd()

        if self.draw_body:
            glBegin(GL_QUADS)
            glColor3fv(self.body_color)
            for q in self.quads:
                for v in q:
                    glVertex3fv(self.vertices[v])
            glEnd()


class OBJModel:
    def __init__(self, filename):
        self.vertices = []
        self.faces = []

        with open(filename, "r") as f:
            for line in f:
                # lines with v are vertices
                if line.startswith("v "):
                    parts = line.split()
                    v = (float(parts[1]), float(parts[2]), float(parts[3]))
                    self.vertices.append(v)

                # lines with f are faces
                elif line.startswith("f "):
                    parts = line.split()
                    face = []
                    for part in parts[1:]:
                        indices = part.split("/")
                        # OBJ indices are 1-based, Python is 0-based, so subtract 1
                        face.append(int(indices[0]) - 1)
                    self.faces.append(face)

    def draw(self):
        glBegin(GL_TRIANGLES)
        for face in self.faces:
            for vertex_index in face:
                glVertex3fv(self.vertices[vertex_index])
        glEnd()


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
        print(
            f"{RED_TEXT}!! ERROR !! Configuration file does not follow legal syntax:\n{e}{RESET_TEXT}"
        )
        sys.exit(1)

    try:
        DISPLAY_WIDTH = settings.getint("Options", "DISPLAY_WIDTH")
        DISPLAY_HEIGHT = settings.getint("Options", "DISPLAY_HEIGHT")
        FOV = settings.getfloat("Options", "FOV")
        MOUSE_SENSITIVITY = settings.getfloat("Options", "MOUSE_SENSITIVITY")
        FPS = settings.getint("Options", "FPS")
    except ValueError as e:
        print(f"{RED_TEXT}!! ERROR !! Type mismatch error:\n{e}{RESET_TEXT}")
        sys.exit(1)

    pg.init()

    display = (DISPLAY_WIDTH, DISPLAY_HEIGHT)

    # Double buffering means we can transform one buffer while leaving the visible one untouched
    pg.display.set_mode(display, DOUBLEBUF | OPENGL)
    pg.mouse.set_visible(False)
    pg.event.set_grab(True)  # Lock mouse to window

    # Define system geometry
    levelMap = Level(
        objects=[
            RectangleObject((-15, -1.1, -15), (15, -1, 15), clipping=False),
            RectangleObject(
                (-7, -0.9, 5),
                (-6, 1, 8),
                body_color=(0, 0.2, 0),
                draw_edges=True,
                clipping=True,
            ),
        ]
    )

    # Defines camera "frustrum"
    gluPerspective(FOV, (display[0] / display[1]), 0.1, 100.0)
    glEnable(GL_DEPTH_TEST)
    glDepthFunc(GL_LESS)
    # glEnable(GL_CULL_FACE)
    glEnable(GL_LINE_SMOOTH)

    clock = pg.time.Clock()

    # Player Starting Position & Camera
    cam_x, cam_y, cam_z = 0, 0, 0
    # cube_rotation = 0
    yaw, pitch = 0.0, 0.0
    move_speed = 0.1
    mouse_sensitivity = MOUSE_SENSITIVITY

    glTranslatef(cam_x, cam_y, cam_z)

    cyl = OBJModel("assets\cylinder.obj")

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

        if not levelMap.is_in_navmesh(cam_x + dx, cam_z):
            cam_x += dx

        if not levelMap.is_in_navmesh(cam_x, cam_z + dz):
            cam_z += dz

        # clear previous screen
        glClear(GL_COLOR_BUFFER_BIT | GL_DEPTH_BUFFER_BIT)

        # transformations and drawing
        # ===============================================
        glPushMatrix()

        # Camera
        glRotatef(pitch, 1, 0, 0)
        glRotatef(yaw, 0, 1, 0)
        glTranslatef(-cam_x, -cam_y, -cam_z)

        glPushMatrix()
        glTranslatef(5, 1, 5)
        glColor3f(0.1, 0.5, 0.1)
        cyl.draw()
        glPopMatrix()

        # Static objects
        for obj in levelMap.objects:
            obj.draw()

        # Moving objects should be handled with individual matrices
        # glPushMatrix()
        # glRotatef(cube_rotation, 1, 1, 1)
        # draw_wire_cube()
        # glPopMatrix()

        glPopMatrix()
        # ===============================================

        # Update any states here for e.g. animations
        # cube_rotation += 1

        # display to user
        pg.display.flip()

        # wait at 60 fps
        clock.tick(FPS)


if __name__ == "__main__":
    main()
