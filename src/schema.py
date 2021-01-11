

from typing import Union

from lib.dblib.databaseinterface import HddEntry
from lib.hddlib.hdd import Hdd
from lib.hddlib.hdd_interface import ActiveHdd
from lib.hddlib.hdd_test_interface import HddTestInterface

import strawberry

@strawberry.type
class Query:
    @strawberry.field
    def test_field(self) -> str:
        return "Hello"
    @strawberry.field
    def test_field2(self) -> str:
        print(self)
        return str(self)
    @strawberry.field
    def test_field3(self, test_param: str) -> str:
        print(self)
        print(test_param)
        return str(self)

q = Query()
#m = Mutation()
#s = Subscription()

schema = strawberry.Schema(query=q)
