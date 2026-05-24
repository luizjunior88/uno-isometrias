import random
from src.engine.models import Card, Color, Action, Isometry

def criar_baralho() -> list[Card]:
    baralho = []
    cores_normais = [Color.RED, Color.BLUE, Color.GREEN, Color.YELLOW]
    isometrias = [Isometry.TRANSLATION, Isometry.ROTATION, Isometry.REFLECTION, Isometry.GLIDE_REFLECTION]
    
    for cor in cores_normais:
        for isometria in isometrias:
            for _ in range(4):
                baralho.append(Card(color=cor, value=0, isometry=isometria, action=Action.NONE))
        
        acoes = [Action.SKIP, Action.REVERSE, Action.DRAW_TWO]
        for acao in acoes:
            for _ in range(2):
                baralho.append(Card(color=cor, value=0, isometry=Isometry.NONE, action=acao))

    for _ in range(4):
        baralho.append(Card(color=Color.BLACK, value=0, isometry=Isometry.NONE, action=Action.JOKER))
        baralho.append(Card(color=Color.BLACK, value=0, isometry=Isometry.NONE, action=Action.JOKER_DRAW_FOUR))

    random.shuffle(baralho)
    return baralho