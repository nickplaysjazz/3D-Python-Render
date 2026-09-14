import argparse
import math
import socket
import time
from dataclasses import dataclass

import glm

from collision import resolve_collisions
from levels import load_collision_objects
from shared_state import decode_packet, encode_packet

TICK_RATE = 30
MOVE_SPEED = 10.0 / TICK_RATE
SPAWN_POSITION = glm.vec3(0.0, 5.0, 0.0)
PLAYER_TIMEOUT = 3.0


@dataclass
class Player:
    player_id: int
    address: tuple
    pos: glm.vec3
    yaw: float = -90.0
    pitch: float = 0.0
    last_sequence: int = 0
    last_seen: float = 0.0


def run_server(host, port, level_path):
    collision_objects = load_collision_objects(level_path)
    server_socket = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    server_socket.bind((host, port))
    server_socket.settimeout(1.0 / TICK_RATE)
    players = {}
    addresses = {}
    next_player_id = 1
    print(f"Listening on {host}:{port}")

    while True:
        try:
            data, address = server_socket.recvfrom(65535)
        except (socket.timeout, ConnectionResetError):
            data = None
            address = None

        if data is not None:
            try:
                packet = decode_packet(data)
            except (ValueError, UnicodeDecodeError):
                continue

            if packet.get("type") == "hello" and address not in addresses:
                player = Player(
                    next_player_id,
                    address,
                    glm.vec3(SPAWN_POSITION),
                    last_seen=time.monotonic(),
                )
                next_player_id += 1
                players[player.player_id] = player
                addresses[address] = player.player_id
                server_socket.sendto(
                    encode_packet(
                        {
                            "version": 1,
                            "type": "welcome",
                            "player_id": player.player_id,
                            "position": list(player.pos),
                        }
                    ),
                    address,
                )
            elif address in addresses:
                player_id = addresses[address]
                player = players[player_id]
                if packet.get("type") == "leave":
                    del players[player_id]
                    del addresses[address]
                    continue
                if packet.get("type") != "input":
                    continue
                player.last_seen = time.monotonic()
                sequence = int(packet.get("sequence", 0))
                if sequence <= player.last_sequence:
                    continue
                player.last_sequence = sequence
                player.yaw = float(packet.get("yaw", player.yaw))
                player.pitch = float(packet.get("pitch", player.pitch))
                flattened_front = glm.normalize(
                    glm.vec3(
                        math.cos(math.radians(player.yaw)),
                        0.0,
                        math.sin(math.radians(player.yaw)),
                    )
                )
                right = glm.vec3(-flattened_front.z, 0.0, flattened_front.x)
                movement = glm.vec3(0.0)
                if packet.get("forward"):
                    movement += flattened_front
                if packet.get("backward"):
                    movement -= flattened_front
                if packet.get("right"):
                    movement += right
                if packet.get("left"):
                    movement -= right
                if glm.length(movement) > 0:
                    movement = glm.normalize(movement) * MOVE_SPEED
                    player.pos = resolve_collisions(
                        player.pos + movement, collision_objects
                    )

        now = time.monotonic()
        for player_id, player in list(players.items()):
            if now - player.last_seen > PLAYER_TIMEOUT:
                del players[player_id]
                addresses.pop(player.address, None)

        if players:
            state = {
                "version": 1,
                "type": "state",
                "players": [
                    {
                        "id": player.player_id,
                        "position": list(player.pos),
                        "rotation": [player.pitch, player.yaw, 0.0],
                        "last_input": player.last_sequence,
                    }
                    for player in players.values()
                ],
            }
            encoded_state = encode_packet(state)
            for player in players.values():
                server_socket.sendto(encoded_state, player.address)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="UDP game server")
    parser.add_argument("--host", default="0.0.0.0")
    parser.add_argument("--port", type=int, default=9999)
    parser.add_argument("--level", default="levels/texture_land.json")
    arguments = parser.parse_args()
    run_server(arguments.host, arguments.port, arguments.level)
