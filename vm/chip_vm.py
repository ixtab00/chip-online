from asyncio import Event, sleep, Queue, create_task, Task, CancelledError

from fastapi import WebSocket

from chip8.chip8 import AsyncEmulator

from typing import Dict, Coroutine, Tuple

from time import perf_counter, time

TTL = 300
PING_INTERVAL = 15

class CHIPVm():
    def __init__(self, ws: WebSocket, rom: Dict[str, str]):
        self._ws = ws
        self._emulator = AsyncEmulator()
        self._emulator.read_rom(rom["path"])
        self._fps = rom["fps"]
        self._cpr = rom["cpr"] #Cycles Per Rerender
        self._stop_event = Event()
        self._play_event = Event()
        self._play_event.set()
        self._param_queue = Queue() #For dynamic emulation params updating
        self._last_active = time()

    @property
    def last_active(self):
        return self._last_active
    
    @last_active.setter
    def last_active(self, new_value: float):
        assert isinstance(new_value, float)
        self._last_active = new_value

    @property
    def ws(self):
        return self._ws
    
    @property
    def is_paused(self):
        return not self._play_event.is_set()

    async def run(self) -> None:

        while not self._stop_event.is_set():
            await self._play_event.wait()

            start_time = perf_counter()

            await self._emulator.cycle(self._cpr)
            await self._ws.send_json({"frame":self._emulator.get_screen_state()})

            while not self._param_queue.empty():
                params = await self._param_queue.get()
                if params is None:
                    break

                if params.get("cpr", None):
                    self._cpr = params.get("cpr")
                elif params.get("fps", None):
                    self._fps = params.get("fps")

            delta = perf_counter() - start_time
            await sleep(max(0, 1/self._fps - delta))

    async def stop(self) -> None:
        self._param_queue.put_nowait(None)
        self._stop_event.set()

    async def pause(self) -> None:
        self._play_event.clear()

    async def unpause(self) -> None:
        self._play_event.set()
    
    async def put_params(self, params: Dict[str, str]) -> None:
        await self._param_queue.put(params)


class VMManager():
    def __init__(self, max_sessions: int = 10):
        self._sessions: Dict[str, Tuple[CHIPVm, Coroutine]] = {}
        self._max_sessions: int = max_sessions

    async def check_activity(self):
        while True:
            for session_id in self._sessions.keys():
                session, _ = self._sessions[session_id]
                if session.last_active - time() > TTL:
                    await self.stop_emulator(session_id)

            await sleep(PING_INTERVAL)

    async def start_emulator(self, session_id: str, ws: WebSocket, rom: Dict[str, str]) -> Task:
        if len(self._sessions) >= self._max_sessions:
            await ws.send_json({"error": "Too many sessions, come back later."})
            await ws.close()
            return
        
        session = CHIPVm(ws, rom)
        task = create_task(session.run())

        self._sessions[session_id] = (session, task)

        return task
    
    async def handle_params(self, session_id: str, params: Dict[str, str]) -> None:
        assert session_id in self._sessions.keys()
        session, _ = self._sessions.get(session_id)

        await session.put_params(params)
    
    async def handle_input(self, session_id: str, data: Dict[str, str]) -> None:
        session, _ = self._sessions[session_id]
        session.last_active = time()
        
        try:
            await session._emulator.put_input(data)
        except Exception as e:
            pass

    async def stop_emulator(self, session_id: str):
        assert session_id in self._sessions.keys()

        session, task = self._sessions.pop(session_id)

        await session.stop()
        task.cancel()
        try:
            await task
        except CancelledError:
            pass

    async def unload_rom(self, session_id: str):
        assert session_id in self._sessions.keys()

        session, task = self._sessions.get(session_id)

        await session.stop()
        await task

    async def pause_emulator(self, session_id: str):
        assert session_id in self._sessions.keys()

        session, _ = self._sessions[session_id]
        await session.pause()

    async def unpause_emulator(self, session_id: str):
        assert session_id in self._sessions.keys()

        session, _ = self._sessions[session_id]
        await session.unpause()

    def get_current_ws(self, session_id: str) -> WebSocket:
        assert session_id in self._sessions.keys()

        session, _ = self._sessions[session_id]
        return session.ws
    
    def is_paused(self, session_id: str) -> bool:
        assert session_id in self._sessions.keys()

        session, _ = self._sessions[session_id]
        return session.is_paused
