"""
Created by Epic at 10/4/20
"""
from aiohttp import ClientSession, ClientWebSocketResponse, WSMsgType
from asyncio import get_event_loop, Event, Future
from ujson import dumps, loads
from typing import Optional, Union, Dict
from string import ascii_letters
from random import choice


class ValuedEvent:
    def __init__(self):
        self.future: Optional[Future] = None
        self.loop = get_event_loop()

    def set(self, value):
        if not self.future.done():
            self.future.set_result(value)

    async def wait(self):
        if self.future.done():
            return self.future.result()
        return await self.future


class BridgeClient:
    def __init__(self, service_name: str, paths: list):
        self.sesssion = ClientSession()
        self.loop = get_event_loop()
        self.ws: Optional[ClientWebSocketResponse] = None
        self.opcode_listeners = {}
        self.event_listeners = {}
        self.wait_for_listeners: Dict[str, ValuedEvent] = {}

        self.service_name = service_name
        self.paths = paths
        self.event_id_length = 10

    async def connect(self):
        self.ws = await self.sesssion.ws_connect("ws://bridge:5050")

        await self.send({"op": 0, "d": self.service_name, "p": self.paths})

    async def send(self, data: dict):
        await self.ws.send_json(data, dumps=dumps)

    async def dispatch(self, event_name, data, path="*", *, event_id=None):
        await self.send({"op": 1, "e": event_name, "d": data, "p": path, "eid": event_id})

    async def fetch(self, *args):
        event_id = self.create_event_id()
        event = ValuedEvent()
        self.wait_for_listeners[event_id] = event
        await self.dispatch(*args, event_id=event_id)
        return await event.wait()

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

        listener: ValuedEvent = self.event_listeners.get(data["eid"], None)
        if listener is None:
            return
        listener.set(data["d"])
        del self.event_listeners[data["eid"]]

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

    def create_event_id(self):
        return "".join(choice(ascii_letters) for i in range(self.event_id_length))
