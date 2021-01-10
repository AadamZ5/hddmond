import asyncio
import logging

from injectable import inject

from lib.hddlistmodel import HddListModel
from lib.api.websocket import WebsocketServer
from lib.hddmon_dataclasses import ImageData
from lib.image import ImageManager

class App:
    def __init__(self):
        self.logger = logging.getLogger(__name__ + "." + self.__class__.__qualname__)
        self.logger.setLevel(logging.DEBUG)
        self.logger.info("Initializing application...")
        #self.images = inject(ImageManager)
        self.list = HddListModel(taskChangedCallback = self.task_changed_cb)
    
        self.ws = inject(WebsocketServer)
        self.ws.connect_instance(self.list) #All API functions are defined in ListModel

        #TODO: Construct a graphql server class, and serve it asynchronously here.

    async def ws_update(self, payload):
        await self.ws.broadcast_data(payload)

    async def start(self):
        self.logger.info("Starting application...")
        #await self.images.start()
        await self.ws.start()
        await self.list.start()

    async def stop(self, *args, **kwargs):
        self.logger.info("Stopping application...")
        await self.ws.stop()
        await self.list.stop()
        #await self.images.stop()
        
    def task_changed_cb(self, payload):
        loop = asyncio.get_event_loop()
        loop.create_task(self.ws_update(payload))
    