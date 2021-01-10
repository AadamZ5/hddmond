import strawberry

from typing import List, Optional, Union

from lib.hddlib.hdd_entry import HddEntry
from lib.hddlistmodel import HddListModel
from lib.hddlib.hdd_interface import ActiveHdd

class StrawberryGraphQL:

    @strawberry.type
    class Query:
        
        @strawberry.field
        def hdd(self, serial: str) -> Optional[Union[HddEntry,ActiveHdd]]:
            return None #TODO: Look for the HDD!

        @strawberry.field
        def live_hdds(self) -> List[ActiveHdd]:
            return list() #TODO: Get the HDDs!

        @strawberry.field
        def search_hdd(self, search_string: str) -> List[Union[HddEntry,ActiveHdd]]:
            return list() #TODO: Search for the HDD!

    @strawberry.type
    class Mutation:
        pass

    @strawberry.type
    class Subscription:
        pass

    def __init__(self, list_model: HddListModel):
        self.list_model = list_model
        self.schema = strawberry.Schema(query=self.Query, mutation=self.Mutation, subscription=self.Subscription)