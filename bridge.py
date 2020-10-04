"""
Created by Epic at 10/4/20
"""
from aiohttp import ClientSession, ClientWebSocketResponse, WSMsgType
from asyncio import get_event_loop
from ujson import dumps, loads
from typing import Optional


class BridgeClient:
    def __init__(self, service_name: str, paths: list):
        self.sesssion = ClientSession()
        self.loop = get_event_loop()
        self.ws: Optional[ClientWebSocketResponse] = None
        self.service_name = service_name
        self.paths = paths
        self.listeners = {}

    async def connect(self):
        self.ws = await self.sesssion.ws_connect("ws://bridge:5050")

        await self.send({"op": 0, "d": self.service_name, "p": self.paths})

    async def send(self, data: dict):
        await self.ws.send_json(data, dumps=dumps)

    async def on_receive(self, data: dict):
        for event_handler in self.listeners.get(data["op"], []):
            self.loop.create_task(event_handler(data["d"]))
        for event_handler in self.listeners[None]:
            self.loop.create_task(event_handler(data["d"]))

    async def listen_loop(self):
        async for message in self.ws:
            if message.type == WSMsgType.TEXT:
                await self.on_receive(message.json(loads=loads))

    def on(self, opcode: int = None):
        def inner(func):
            listeners = self.listeners.get(opcode, [])
            listeners.append(func)
            self.listeners[opcode] = listeners
        return inner

