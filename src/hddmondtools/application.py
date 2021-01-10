import asyncio
import logging

from injectable import inject

from hddmondtools.hddmanager import HddListModel
from hddmondtools.websocket import WebsocketServer
from hddmondtools.hddmon_dataclasses import ImageData
from hddmontools.image import ImageManager

class App:
    def __init__(self):
        self.logger = logging.getLogger(__name__ + "." + self.__class__.__qualname__)
        self.logger.setLevel(logging.DEBUG)
        self.logger.info("Initializing application...")
        self.images = inject(ImageManager)
        self.list = HddListModel(taskChangedCallback = self.task_changed_cb)
    
        self.ws = inject(WebsocketServer)
        self.ws.connect_instance(self.list) #All API functions are defined in ListModel

    async def ws_update(self, payload):
        await self.ws.broadcast_data(payload)
        
    def image_shim(self, *args, **kw):
        imags = []
        for i in self.images.added_images:
            imags.append(ImageData.FromDiskImage(i))
        disc = []
        for i in self.images.discovered_images:
            disc.append(ImageData.FromDiskImage(i))
        return {'onboarded_images': imags, 'discovered_images': disc}

    async def start(self):
        self.logger.info("Starting application...")
        await self.images.start()
        await self.ws.start()
        await self.list.start()

    async def stop(self, *args, **kwargs):
        self.logger.info("Stopping application...")
        await self.ws.stop()
        await self.list.stop()
        await self.images.stop()
        
    def task_changed_cb(self, payload):
        loop = asyncio.get_event_loop()
        loop.create_task(self.ws_update(payload))
    