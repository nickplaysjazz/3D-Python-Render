import math

from pyglm import glm

from constants import Directions


class Camera:
    def __init__(
        self,
        yaw,
        pitch,
        speed,
        sensitivity,
        fov,
        pos=glm.vec3(0, 0, 0),
        up=glm.vec3(0, 1, 0),
        front=glm.vec3(0, 0, -1),
        world_up=glm.vec3(0, 1, 0),
    ):
        self.yaw = yaw
        self.pitch = pitch
        self.speed = speed
        self.sensitivity = sensitivity
        self.fov = fov

        self.pos = pos
        self.up = up
        self.front = front

        self.world_up = world_up

        self.update_camera_vectors()

    def get_view_matrix(self):
        return glm.lookAt(self.pos, self.pos + self.front, self.up)

    def process_keyboard(self, direction, delta_time):
        velocity = self.speed * delta_time

        # If we use self.front directly, we travel slowly when we look upwards
        flattened_front = glm.normalize(glm.vec3(self.front.x, 0, self.front.z))
        if direction == Directions.FORWARD:
            self.pos += flattened_front * velocity
        if direction == Directions.BACKWARD:
            self.pos -= flattened_front * velocity
        if direction == Directions.RIGHT:
            self.pos += self.right * velocity
        if direction == Directions.LEFT:
            self.pos -= self.right * velocity

    def process_mouse_movement(self, xoffset, yoffset, constrain_pitch=True):
        xoffset *= self.sensitivity
        yoffset *= self.sensitivity

        self.yaw += xoffset
        self.pitch += yoffset

        if constrain_pitch:
            self.pitch = max(-89.0, min(89.0, self.pitch))

        self.update_camera_vectors()

    def update_camera_vectors(self):
        yaw_rad = math.radians(self.yaw)
        pitch_rad = math.radians(self.pitch)

        self.front = glm.vec3(
            math.cos(yaw_rad) * math.cos(pitch_rad),
            math.sin(pitch_rad),
            math.sin(yaw_rad) * math.cos(pitch_rad),
        )
        self.front = glm.normalize(self.front)
        self.right = glm.normalize(glm.cross(self.front, self.world_up))
        self.up = glm.normalize(glm.cross(self.right, self.front))
