"""
Created by Epic at 10/4/20
"""
from aiohttp import ClientSession, ClientWebSocketResponse, WSMsgType
from asyncio import get_event_loop
from ujson import dumps, loads
from typing import Optional, Union


class BridgeClient:
    def __init__(self, service_name: str, paths: list):
        self.sesssion = ClientSession()
        self.loop = get_event_loop()
        self.ws: Optional[ClientWebSocketResponse] = None
        self.service_name = service_name
        self.paths = paths
        self.opcode_listeners = {}
        self.event_listeners = {}

    async def connect(self):
        self.ws = await self.sesssion.ws_connect("ws://bridge:5050")

        await self.send({"op": 0, "d": self.service_name, "p": self.paths})

    async def send(self, data: dict):
        await self.ws.send_json(data, dumps=dumps)

    async def dispatch(self, event_name, data, path):
        await self.send({"op": 1, "e": event_name, "d": data, "p": path})

    async def on_receive(self, data: dict):
        for event_handler in self.opcode_listeners.get(data["op"], []):
            self.loop.create_task(event_handler(data))
        for event_handler in self.opcode_listeners[None]:
            self.loop.create_task(event_handler(data))

        if data["op"] != 1:
            return

        for event_handler in self.event_listeners.get(data["e"], []):
            self.loop.create_task(event_handler(data["d"]))
        for event_handler in self.event_listeners[None]:
            self.loop.create_task(event_handler(data["d"]))

    async def listen_loop(self):
        async for message in self.ws:
            if message.type == WSMsgType.TEXT:
                await self.on_receive(message.json(loads=loads))

    def on(self, opcode_or_event: Union[int, str] = None):
        def inner(func):
            if type(opcode_or_event) == int:
                listeners = self.opcode_listeners.get(opcode_or_event, [])
                listeners.append(func)
                self.opcode_listeners[opcode_or_event] = listeners
            elif type(opcode_or_event) == str:
                listeners = self.event_listeners.get(opcode_or_event, [])
                listeners.append(func)
                self.event_listeners[opcode_or_event] = listeners
            else:
                raise TypeError("Invalid type.")

        return inner
