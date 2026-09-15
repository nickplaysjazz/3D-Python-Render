import json
from dataclasses import dataclass

PROTOCOL_VERSION = 1


@dataclass
class InputState:
    sequence: int
    forward: bool
    backward: bool
    left: bool
    right: bool
    yaw: float
    pitch: float

    def to_packet(self):
        return {
            "version": PROTOCOL_VERSION,
            "type": "input",
            "sequence": self.sequence,
            "forward": self.forward,
            "backward": self.backward,
            "left": self.left,
            "right": self.right,
            "yaw": self.yaw,
            "pitch": self.pitch,
        }


def encode_packet(packet):
    return json.dumps(packet, separators=(",", ":")).encode("utf-8")


def decode_packet(data):
    packet = json.loads(data.decode("utf-8"))
    if packet.get("version") != PROTOCOL_VERSION:
        raise ValueError("Unsupported network protocol version")
    return packet
