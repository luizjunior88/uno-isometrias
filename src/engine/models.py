from enum import Enum, auto
from dataclasses import dataclass

class Color(Enum):
    RED = auto()
    BLUE = auto()
    GREEN = auto()
    YELLOW = auto()
    BLACK = auto()

class Action(Enum):
    NONE = auto()
    SKIP = auto()
    REVERSE = auto()
    DRAW_TWO = auto()
    JOKER = auto()
    JOKER_DRAW_FOUR = auto()

# AQUI ESTÁ A NOSSA NOVA ESTRELA DO JOGO!
class Isometry(Enum):
    NONE = auto()
    TRANSLATION = auto()
    ROTATION = auto()
    REFLECTION = auto()
    GLIDE_REFLECTION = auto()

@dataclass
class Card:
    color: Color
    value: int
    isometry: Isometry
    action: Action