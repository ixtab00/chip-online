from fastapi import FastAPI, WebSocket, WebSocketDisconnect, Request, Form
from fastapi.responses import HTMLResponse
from fastapi.templating import Jinja2Templates

from asyncio import create_task

from typing import Annotated

from uuid import uuid4

from vm.chip_vm import VMManager

import logging

from json import loads, dumps

app = FastAPI()
manager = VMManager(20)
templates = Jinja2Templates("templates")

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

logger = logging.getLogger(__name__)

with open("./rom_data.json", encoding="UTF-8") as file:
    ROM_DATA = loads(file.read())


@app.get("/index", response_class=HTMLResponse)
def index(request: Request):
    return templates.TemplateResponse(request, "index.html", {"roms":ROM_DATA})


@app.get("/roms")
async def get_roms():
    return ROM_DATA

@app.post("/pause/{instance_id}")
async def pause(instance_id: str):
    try:
        if manager.is_paused(instance_id):
            await manager.unpause_emulator(instance_id)
            return {"status":"OK"}
        else:
            await manager.pause_emulator(instance_id)
            return {"status":"OK"}
    except Exception as e:
        logger.error(f"@{instance_id}: failed to pause/unpause ROM due to: {e}")
        return {"error": "ERROR"}

@app.post("/change_params/{instance_id}")
async def put_params(instance_id: str, cpr: Annotated[int, Form()], fps: Annotated[int, Form()]):
    try:
        await manager.handle_params(instance_id, {"cpr":cpr, "fps": fps})
        return {"status":"OK"}
    except Exception as e:
        logger.error(f"@{instance_id}: failed to update parameters due to: {e}")
        return {"error":"ERROR"}

@app.get("/stats")
async def get_stats():
    return {"current_sessions": len(manager._sessions), "total_sessions": manager._max_sessions}

@app.post("/change_rom/{rom}/{instance_id}")
async def change_rom(rom: str, instance_id: str):
    try:
        await manager.pause_emulator(instance_id)
        await manager.unload_rom(instance_id)
        ws = manager.get_current_ws(instance_id)
        await manager.start_emulator(instance_id, ws, ROM_DATA[rom])
        await manager.unpause_emulator(instance_id)
        return {"status": "OK"}

    except Exception as e:
        logger.error(f"@{instance_id}: failed to load ROM due to: {e}")
        return {"status":"ERROR"}


@app.websocket("/ws")
async def websocket_endpoint(ws: WebSocket):
    await ws.accept()

    instance_id = str(uuid4())
    try:
        _ = await manager.start_emulator(
            instance_id, ws, {
                "path": "./roms/Tic-Tac-Toe.ch8",
                "fps":60,
                "cpr":10
            }
        )
        await ws.send_text(dumps({"session_id": instance_id}))
        logger.info(f"Session {instance_id} started.")

    except Exception as e:
        await ws.send_json({"error": e})
        logger.error(f"Could not start the session.")

    try:
        while True:
            data = await ws.receive_json()
            await manager.handle_input(instance_id, data)
    except WebSocketDisconnect:
        await manager.stop_emulator(instance_id)