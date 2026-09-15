import glm
import math
from dataclasses import dataclass


@dataclass
class CollisionObject:
    pos: glm.vec3
    rotation: glm.vec3
    local_aabb: dict


def check_collision(camera_pos, obj):
    """
    Checks collision and returns (is_colliding, push_out_vector).
    """
    if not hasattr(obj, "local_aabb"):
        return False, glm.vec3(0.0)

    model = glm.mat4(1.0)
    model = glm.translate(model, obj.pos)
    if obj.rotation.y != 0.0:
        model = glm.rotate(model, glm.radians(obj.rotation.y), glm.vec3(0.0, 1.0, 0.0))
    if obj.rotation.x != 0.0:
        model = glm.rotate(model, glm.radians(obj.rotation.x), glm.vec3(1.0, 0.0, 0.0))
    if obj.rotation.z != 0.0:
        model = glm.rotate(model, glm.radians(obj.rotation.z), glm.vec3(0.0, 0.0, 1.0))

    inv_model = glm.inverse(model)
    local_cam_pos = glm.vec3(inv_model * glm.vec4(camera_pos, 1.0))

    box_min = obj.local_aabb["min"]
    box_max = obj.local_aabb["max"]

    player_radius = 1.0
    player_height = 6.0
    eye_height = 5.0

    player_feet_y = local_cam_pos.y - eye_height
    player_head_y = player_feet_y + player_height

    if player_head_y < box_min.y or player_feet_y > box_max.y:
        return False, glm.vec3(0.0)

    closest_x = max(box_min.x, min(local_cam_pos.x, box_max.x))
    closest_z = max(box_min.z, min(local_cam_pos.z, box_max.z))

    dx = local_cam_pos.x - closest_x
    dz = local_cam_pos.z - closest_z
    distance_squared = (dx * dx) + (dz * dz)

    inside_x = box_min.x <= local_cam_pos.x <= box_max.x
    inside_z = box_min.z <= local_cam_pos.z <= box_max.z

    local_normal = glm.vec3(0.0)
    penetration_depth = 0.0

    # Case 1: Player's center is inside the box (Deep penetration)
    if inside_x and inside_z:
        dist_to_min_x = local_cam_pos.x - box_min.x
        dist_to_max_x = box_max.x - local_cam_pos.x
        dist_to_min_z = local_cam_pos.z - box_min.z
        dist_to_max_z = box_max.z - local_cam_pos.z

        min_dist = min(dist_to_min_x, dist_to_max_x, dist_to_min_z, dist_to_max_z)

        if min_dist == dist_to_min_x:
            local_normal = glm.vec3(-1.0, 0.0, 0.0)
            penetration_depth = dist_to_min_x + player_radius
        elif min_dist == dist_to_max_x:
            local_normal = glm.vec3(1.0, 0.0, 0.0)
            penetration_depth = dist_to_max_x + player_radius
        elif min_dist == dist_to_min_z:
            local_normal = glm.vec3(0.0, 0.0, -1.0)
            penetration_depth = dist_to_min_z + player_radius
        else:
            local_normal = glm.vec3(0.0, 0.0, 1.0)
            penetration_depth = dist_to_max_z + player_radius

    # Case 2: Player is outside, but radius intersects the box
    elif distance_squared < (player_radius * player_radius):
        distance = math.sqrt(distance_squared)
        if distance == 0.0:  # Prevent division by zero
            return False, glm.vec3(0.0)

        local_normal = glm.vec3(dx / distance, 0.0, dz / distance)
        penetration_depth = player_radius - distance

    else:
        return False, glm.vec3(0.0)

    # Transform the local normal back into world space
    # Using w=0.0 treats this as a direction vector, ignoring translation
    world_normal = glm.normalize(glm.vec3(model * glm.vec4(local_normal, 0.0)))

    push_vector = world_normal * penetration_depth
    return True, push_vector


def resolve_collisions(position, objects):
    """Push a player position out of every solid object in the level."""
    resolved = glm.vec3(position)
    for obj in objects:
        colliding, push_vector = check_collision(resolved, obj)
        if colliding:
            resolved += push_vector
    return resolved
