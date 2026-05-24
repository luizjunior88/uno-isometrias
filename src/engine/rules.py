from src.engine.models import Card, Color, Action, Isometry

def pode_jogar(carta: Card, carta_topo: Card, cor_ativa: Color) -> bool:
    if carta.color == Color.BLACK: return True
    if carta.color == cor_ativa: return True
    if carta.action != Action.NONE and carta.action == carta_topo.action: return True
    if carta.isometry != Isometry.NONE and carta.isometry == carta_topo.isometry: return True
    return False