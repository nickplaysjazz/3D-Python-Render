from enum import Enum


class Directions(Enum):
    FORWARD = "forward"
    BACKWARD = "backward"
    LEFT = "left"
    RIGHT = "right"


class Filters(Enum):
    NEAREST = "nearest"
    LINEAR = "linear"