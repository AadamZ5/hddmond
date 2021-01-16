import asyncio
import logging
import strawberry
import uvicorn

from typing import List, Optional, Union
from injectable import inject
from starlette.applications import Starlette
from starlette.middleware.cors import CORSMiddleware
from strawberry.asgi import GraphQL

from lib.dblib.couchdb import CouchDatabase
from lib.hddlib.hdd_entry import HddEntry
from lib.hddlib.hdd_test_interface import HddTestInterface
from lib.hddlistmodel import HddListModel
from lib.hddlib.hdd_interface import ActiveHdd

@strawberry.type
class Query:

    @strawberry.field
    def get_hdd(self, serial: str) -> Optional[Union[ActiveHdd, HddEntry]]:
        hdd: Optional[HddEntry] = None
        list_model = inject(HddListModel)
        for h in list_model.hdds:
            if h.serial == serial:
                hdd = h
                break
        if hdd != None:
            return hdd

        database = inject(CouchDatabase)
        hdd = database.get_hdd(serial)

        return hdd

    @strawberry.field
    def live_hdds(self) -> List[ActiveHdd]:
        list_model = inject(HddListModel)
        return list_model.hdds

    @strawberry.field
    def search_hdd(self, search_string: str) -> List[Union[ActiveHdd, HddEntry]]:
        database = inject(CouchDatabase)
        l = database.search_hdd(search_string)
        return l

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
        cfg = uvicorn.Config(self.app, log_level=logging.INFO, port=8001)
        self.server = uvicorn.Server(cfg)
        self.server_task = asyncio.create_task(self.server.serve())

    async def stop(self):
        if self.server_task != None:
            self.server_task.cancel()
