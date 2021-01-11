import asyncio
import logging

from injectable import inject
from lib.api.graphql_schema import StrawberryGraphQL

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
        self.list = inject(HddListModel)
        self.list.add_task_change_callback(self.task_changed_cb)

        self.ws = inject(WebsocketServer)
        self.ws.connect_instance(self.list) #All API functions are defined in ListModel

        self.graph_schema = StrawberryGraphQL()
        #TODO: Construct a graphql server class, and serve it asynchronously here.
        #TODO: Some sort of HTTP server because graphql needs that, and eventually we wanna serve the webpage from here too.

    async def ws_update(self, payload):
        await self.ws.broadcast_data(payload)

    async def start(self):
        self.logger.info("Starting application...")
        #await self.images.start()
        await self.graph_schema.start()
        await self.ws.start()
        await self.list.start()

    async def stop(self, *args, **kwargs):
        self.logger.info("Stopping application...")
        await self.ws.stop()
        await self.graph_schema.stop()
        await self.list.stop()
        #await self.images.stop()
        
    async def task_changed_cb(self, payload):
        await self.ws_update(payload)
    