# Implementation for socket_manager.py
from fastapi import WebSocket
from typing import Dict, List

class ConnectionManager:
    def __init__(self):
        # Key: run_id, Value: List of active WebSocket connections
        self.active_connections: Dict[str, List[WebSocket]] = {}

    async def connect(self, websocket: WebSocket, run_id: str):
        await websocket.accept()
        if run_id not in self.active_connections:
            self.active_connections[run_id] = []
        self.active_connections[run_id].append(websocket)
        print(f"Client connected to project: {run_id}")

    def disconnect(self, websocket: WebSocket, run_id: str):
        if run_id in self.active_connections:
            self.active_connections[run_id].remove(websocket)
            if not self.active_connections[run_id]:
                del self.active_connections[run_id]

    async def send_notification(self, run_id: str, message: dict):
        """Sends a JSON message to all clients connected to a specific run_id"""
        if run_id in self.active_connections:
            for connection in self.active_connections[run_id]:
                await connection.send_json(message)

# Global instance to be used across the app
manager = ConnectionManager()
