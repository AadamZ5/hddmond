import asyncio
import logging
import strawberry
import uvicorn

from typing import List, Optional, Union
from injectable import inject
from starlette.applications import Starlette
from starlette.middleware.cors import CORSMiddleware
from strawberry.asgi import GraphQL

from lib.hddlib.hdd_entry import HddEntry
from lib.hddlib.hdd_test_interface import HddTestInterface
from lib.hddlistmodel import HddListModel
from lib.hddlib.hdd_interface import ActiveHdd

@strawberry.type
class Query:

    @strawberry.field
    def hdd(self, serial: str) -> Optional[Union[ActiveHdd]]:
        #return None #TODO: Look for the HDD!
        return HddTestInterface(None, "/dev/sdX", serial, mock_capacity=453.7)
        #return HddEntry(serial, "Test", "8675309", 435.2)

    @strawberry.field
    def live_hdds(self) -> List[ActiveHdd]:
        list_model = inject(HddListModel)
        return list_model.hdds

    @strawberry.field
    def search_hdd(self, search_string: str) -> List[Union[ActiveHdd]]:
        return list() #TODO: Search for the HDD!

@strawberry.type
class Mutation:
    pass

@strawberry.type
class Subscription:
    pass

class StrawberryGraphQL:

    def __init__(self):
        self.list_model = inject(HddListModel)
        self.schema = strawberry.Schema(query=Query) #, mutation=self.Mutation, subscription=self.Subscription)
        self.app = Starlette(debug=False)
        self.app.add_middleware(CORSMiddleware, allow_headers=["*"], allow_origins=["*"], allow_methods=["*"])
        self.graphql_app = GraphQL(self.schema, debug=False)
        paths = ["/", "/graphql"]
        for path in paths:
            self.app.add_route(path, self.graphql_app)
            self.app.add_websocket_route(path, self.graphql_app) 
        self.server = None
        self.server_task = None

    async def start(self):
        import uvicorn.server
        uvicorn.server.HANDLED_SIGNALS = []
        cfg = uvicorn.Config(self.app, log_level=logging.INFO)
        self.server = uvicorn.Server(cfg)
        self.server_task = asyncio.create_task(self.server.serve())

    async def stop(self):
        if self.server_task != None:
            self.server_task.cancel()
