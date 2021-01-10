from typing import Union
import strawberry
from lib.databaseinterface import HddEntry

from lib.hdd import Hdd
from lib.hdd_interface import ActiveHdd
from lib.hdd_test_interface import HddTestInterface

@strawberry.type
class Query:

    @strawberry.field
    def test_field(self) -> ActiveHdd:
        return Hdd("/dev/sda")

schema = strawberry.Schema(query=Query, types=(Hdd,ActiveHdd,HddEntry,HddTestInterface))
