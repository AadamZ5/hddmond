from typing import Union
import strawberry
from hddmontools.databaseinterface import HddEntry

from hddmontools.hdd import Hdd
from hddmontools.hdd_interface import ActiveHdd
from hddmontools.hdd_test_interface import HddTestInterface

@strawberry.type
class Query:

    @strawberry.field
    def test_field(self) -> ActiveHdd:
        return Hdd("/dev/sda")

schema = strawberry.Schema(query=Query, types=(Hdd,ActiveHdd,HddEntry,HddTestInterface))
