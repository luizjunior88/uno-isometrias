import random
from enum import Enum, auto
from typing import List, Dict, Optional
from src.engine.models import Card, Color, Action, Isometry

class GameState(Enum):
    WAITING = auto()
    PLAYING = auto()
    BLOCKED = auto()
    FREE_PLAY = auto()
    FINISHED = auto()

class Player:
    def __init__(self, name: str, ws_id: str):
        self.name = name
        self.ws_id = ws_id
        self.hand: List[Card] = []
        self.has_said_isometry = False

class Room:
    def __init__(self, room_code: str):
        self.room_code = room_code
        self.players: List[Player] = []
        self.state: GameState = GameState.WAITING
        self.deck: List[Card] = []
        self.discard_pile: List[Card] = []
        self.current_turn_index: int = 0
        self.direction: int = 1
        self.active_color: Optional[Color] = None
        
        self.turns_played: int = 0
        self.current_checkpoint: int = 0
        self.passwords: List[str] = ["1111", "2222", "3333", "4444"]

    def add_player(self, player: Player) -> bool:
        if len(self.players) >= 5 or self.state != GameState.WAITING:
            return False
        self.players.append(player)
        return True

    def start_game(self) -> bool:
        if len(self.players) < 2:
            return False
        self.deck = criar_baralho()
        for _ in range(7):
            for player in self.players:
                player.hand.append(self.deck.pop())
        primeira_carta = self.deck.pop()
        self.discard_pile.append(primeira_carta)
        self.active_color = primeira_carta.color if primeira_carta.color != Color.BLACK else Color.RED
        self.state = GameState.PLAYING
        self.current_turn_index = 0
        self.turns_played = 0
        self.current_checkpoint = 0
        return True

    def advance_turn(self, steps: int = 1):
        self.current_turn_index = (self.current_turn_index + (steps * self.direction)) % len(self.players)

    def check_portagem(self):
        if self.state in [GameState.FREE_PLAY, GameState.FINISHED]:
            return

        jogadas_por_portagem = 3 * len(self.players)
        
        if self.turns_played > 0 and self.turns_played % jogadas_por_portagem == 0:
            if self.current_checkpoint < 4:
                self.current_checkpoint += 1
                self.state = GameState.BLOCKED
            else:
                self.state = GameState.FREE_PLAY

    def unlock_checkpoint(self, password: str) -> bool:
        if self.state != GameState.BLOCKED:
            return False
            
        senha_correta = self.passwords[self.current_checkpoint - 1]
        
        if password == senha_correta:
            self.state = GameState.PLAYING if self.current_checkpoint < 4 else GameState.FREE_PLAY
            return True
        return False

    def play_card(self, player_name: str, card_index: int, chosen_color: str = None) -> bool:
        if self.state != GameState.PLAYING and self.state != GameState.FREE_PLAY:
            return False
        
        current_player = self.players[self.current_turn_index]
        if current_player.name != player_name:
            return False
            
        if card_index < 0 or card_index >= len(current_player.hand):
            return False

        carta = current_player.hand[card_index]
        carta_topo = self.discard_pile[-1]

        from src.engine.rules import pode_jogar
        if not pode_jogar(carta, carta_topo, self.active_color):
            return False

        current_player.hand.pop(card_index)
        self.discard_pile.append(carta)

        # SE FOR PRETA, USA A COR ESCOLHIDA, SENÃO USA A DA CARTA
        if carta.color == Color.BLACK:
            if chosen_color:
                self.active_color = Color[chosen_color]
            else:
                self.active_color = Color.RED # Fallback
        else:
            self.active_color = carta.color

        steps_to_advance = 1
        if carta.action == Action.SKIP:
            steps_to_advance = 2
        elif carta.action == Action.REVERSE:
            self.direction *= -1
            if len(self.players) == 2: steps_to_advance = 2
        elif carta.action == Action.DRAW_TWO:
            self.advance_turn(1)
            target = self.players[self.current_turn_index]
            for _ in range(2):
                if self.deck: target.hand.append(self.deck.pop())
            steps_to_advance = 1
        elif carta.action == Action.JOKER_DRAW_FOUR:
            self.advance_turn(1)
            target = self.players[self.current_turn_index]
            for _ in range(4):
                if self.deck: target.hand.append(self.deck.pop())
            steps_to_advance = 1

        if len(current_player.hand) == 0:
            self.state = GameState.FINISHED
            return True

        self.turns_played += 1
        self.check_portagem()
        self.advance_turn(steps_to_advance)
        return True

    def draw_card(self, player_name: str) -> bool:
        if self.state != GameState.PLAYING and self.state != GameState.FREE_PLAY:
            return False
        current_player = self.players[self.current_turn_index]
        if current_player.name != player_name:
            return False

        if not self.deck:
            if len(self.discard_pile) > 1:
                topo = self.discard_pile.pop()
                self.deck = self.discard_pile[:]
                self.discard_pile = [topo]
                random.shuffle(self.deck)
            else:
                return False

        current_player.hand.append(self.deck.pop())
        
        self.turns_played += 1
        self.check_portagem()
        self.advance_turn(1)
        return True

def criar_baralho() -> list[Card]:
    from src.engine.deck import criar_baralho as gen
    return gen()