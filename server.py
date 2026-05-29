from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from typing import Dict, List
import json
import uvicorn
from src.engine.room import Room, Player, GameState

app = FastAPI(title="UNO Isometrias - Servidor Final")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],  
    allow_headers=["*"],
)

active_rooms: Dict[str, Room] = {}
global_paused = False  # CONTROLO DOCENTE: Pausa Global

class ConnectionManager:
    def __init__(self):
        self.active_connections: Dict[str, List[WebSocket]] = {}

    async def connect(self, websocket: WebSocket, room_id: str):
        await websocket.accept()
        if room_id not in self.active_connections:
            self.active_connections[room_id] = []
        self.active_connections[room_id].append(websocket)

    def disconnect(self, websocket: WebSocket, room_id: str):
        if room_id in self.active_connections:
            self.active_connections[room_id].remove(websocket)

    async def broadcast(self, message: dict, room_id: str):
        if room_id in self.active_connections:
            for connection in self.active_connections[room_id]:
                await connection.send_text(json.dumps(message))
                
    async def send_personal(self, message: dict, websocket: WebSocket):
        await websocket.send_text(json.dumps(message))

manager = ConnectionManager()

class RoomConfig(BaseModel):
    room_id: str
    passwords: List[str]
    expected_players: int

class GlobalPauseConfig(BaseModel):
    pause: bool

@app.post("/api/create_room")
async def api_create_room(config: RoomConfig):
    room_id_seguro = config.room_id.strip().upper()
    if room_id_seguro in active_rooms:
        return {"success": False, "message": f"A sala {room_id_seguro} já está aberta."}
    
    nova_sala = Room(room_id_seguro)
    nova_sala.passwords = config.passwords
    nova_sala.expected_players = config.expected_players
    active_rooms[room_id_seguro] = nova_sala
    return {"success": True, "message": f"Sala '{room_id_seguro}' criada!"}

@app.post("/api/global_pause")
async def api_global_pause(config: GlobalPauseConfig):
    global global_paused
    global_paused = config.pause
    for room_id, room in active_rooms.items():
        await manager.broadcast(broadcast_game_update(room), room_id)
    return {"success": True, "global_paused": global_paused}

# NOVA ROTA INJETADA: RESET DO SERVIDOR (Garbage Collection)
@app.post("/api/reset")
async def api_reset_server():
    global active_rooms, global_paused
    
    # Notificar as salas de que vão ser encerradas (opcional, previne que os clientes fiquem bloqueados num estado)
    for room_id, room in active_rooms.items():
        await manager.broadcast({"type": "error", "message": "O professor encerrou as salas. A aula terminou!"}, room_id)
        
    # Limpeza da Memória do Servidor
    active_rooms.clear()
    global_paused = False
    
    # Fechar à força todos os websockets ativos para não ficarem "presos"
    for room_id, connections in manager.active_connections.items():
        for ws in connections:
            try:
                await ws.close()
            except:
                pass
    manager.active_connections.clear()
    
    return {"success": True, "message": "Memória do servidor limpa e conexões encerradas. Pronto para nova turma."}


def broadcast_game_update(room: Room):
    top = room.discard_pile[-1] if room.discard_pile else None
    top_card = None
    if top:
        cor_visual = room.active_color.name if top.color.name == "BLACK" else top.color.name
        top_card = {"color": cor_visual, "value": top.value, "isometry": top.isometry.name, "action": top.action.name}
    
    winner = None
    if room.state == GameState.FINISHED:
        for p in room.players:
            if len(p.hand) == 0:
                winner = p.name
                break
                
    # Se o professor ativou a pausa global, enviamos o estado "TEACHER_PAUSED" para os alunos
    estado_atual = "TEACHER_PAUSED" if global_paused else room.state.name

    return {
        "type": "game_state",
        "state": estado_atual,
        "checkpoint": room.current_checkpoint,
        "players_info": [f"{p.name} ({len(p.hand)} cartas)" for p in room.players],
        "current_turn": room.players[room.current_turn_index].name if room.players and room.state in [GameState.PLAYING, GameState.FREE_PLAY] else None,
        "top_card": top_card,
        "active_color": room.active_color.name if room.active_color else None,
        "winner": winner
    }

async def send_private_hands(room: Room, room_id: str):
    for i, p in enumerate(room.players):
        hand_data = [{"color": c.color.name, "value": c.value, "isometry": c.isometry.name, "action": c.action.name} for c in p.hand]
        if i < len(manager.active_connections[room_id]):
            ws = manager.active_connections[room_id][i]
            await manager.send_personal({"type": "private_hand", "hand": hand_data}, ws)

@app.websocket("/ws/{room_id}/{player_name}")
async def websocket_endpoint(websocket: WebSocket, room_id: str, player_name: str):
    room_id_seguro = room_id.strip().upper()
    await manager.connect(websocket, room_id_seguro)
    
    if room_id_seguro not in active_rooms:
        await manager.send_personal({"type": "error", "message": "Sala não encontrada!"}, websocket)
        manager.disconnect(websocket, room_id_seguro)
        return
    
    room = active_rooms[room_id_seguro]
    success = room.add_player(Player(player_name, str(websocket)))
    if not success:
        await manager.send_personal({"type": "error", "message": "Sala cheia ou jogo em andamento."}, websocket)
        return

    await manager.broadcast(broadcast_game_update(room), room_id_seguro)
    
    try:
        while True:
            data = await websocket.receive_text()
            message = json.loads(data)
            action = message.get("action")
            
            # Bloqueio estrito se a pausa global do professor estiver ativa
            if global_paused and action in ["play_card", "draw_card", "start_game"]:
                await manager.send_personal({"type": "error", "message": "O jogo está congelado pelo professor!"}, websocket)
                continue
            
            if action == "start_game" and room.state == GameState.WAITING:
                if len(room.players) < getattr(room, 'expected_players', 2):
                    await manager.send_personal({"type": "error", "message": f"Mesa incompleta! Aguarda que entrem os {room.expected_players} elementos do grupo."}, websocket)
                else:
                    room.start_game()
                    
            elif action == "play_card":
                card_idx = message.get("index")
                chosen_color = message.get("chosen_color")
                if not room.play_card(player_name, card_idx, chosen_color):
                    await manager.send_personal({"type": "error", "message": "Jogada inválida ou fora do teu turno!"}, websocket)
                    
            elif action == "draw_card":
                if not room.draw_card(player_name):
                    await manager.send_personal({"type": "error", "message": "Não podes pescar agora!"}, websocket)

            elif action == "say_isometria":
                for p in room.players:
                    if p.name == player_name: p.has_said_isometry = True
                await manager.broadcast({"type": "sys", "message": f"📢 {player_name.upper()} GRITOU ISOMETRIA!"}, room_id_seguro)

            elif action == "unlock":
                if room.unlock_checkpoint(message.get("password")):
                    await manager.broadcast({"type": "sys", "message": "Mesa desbloqueada!"}, room_id_seguro)
                else:
                    await manager.send_personal({"type": "error", "message": "PIN incorreto!"}, websocket)

            await manager.broadcast(broadcast_game_update(room), room_id_seguro)
            await send_private_hands(room, room_id_seguro)
                
    except WebSocketDisconnect:
        manager.disconnect(websocket, room_id_seguro)
        room.players = [p for p in room.players if p.name != player_name]
        await manager.broadcast(broadcast_game_update(room), room_id_seguro)

if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=8000)