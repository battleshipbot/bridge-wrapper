"""
Created by Epic at 10/4/20
"""
from discord.ext.commands import Bot
from .bridge import BridgeClient


class BridgeBot(Bot):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.bridge: BridgeClient = BridgeClient(kwargs["bridge_name"], kwargs["bridge_paths"])
        self.loop.create_task(self.connect_bridge())

    async def connect_bridge(self):
        await self.bridge.connect()

