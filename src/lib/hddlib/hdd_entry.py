import strawberry
import datetime

from abc import ABC
from strawberry import  ID
from typing import List, Optional
from injectable.injection.inject import inject

from lib.hddlib.smart_data import SmartCapture
from lib.tasklib.task_entry import TaskEntry

@strawberry.type
class HddEntry(ABC):
    """
    Represents data about a device entry in the database
    """
    serial: ID = strawberry.field(description="The serial of the device")
    model: str = strawberry.field(description="The model number for the device")
    wwn: Optional[str] = strawberry.field(description="The world-wide-number of the device, if applicable")
    capacity: float = strawberry.field(description="The capacity of the device in GiB")
    first_seen: datetime.datetime = strawberry.field(description="The time the device first appeared in the application")
    last_seen: datetime.datetime = strawberry.field(description="The last time the device was seen in the application")
    seen: int = strawberry.field(description="The amount of times the device has been seen")
    decommissioned: bool = strawberry.field(description="If the drive is considered decommissioned, or unusable")
    completed_tasks: List[TaskEntry] = strawberry.field(description="A list of tasks that have been run on the device") #TODO: Change to proper strawberry Task type!
    smart_captures: List[SmartCapture] = strawberry.field(description="A list of S.M.A.R.T. attribute snapshots")
    def __init__(self, serial: ID, model: str, wwn: Optional[str], capacity: float):
        self.serial = serial
        self.model = model
        self.wwn = wwn
        self.capacity = capacity
        self.seen = 1
        self.decommissioned = False
        self.first_seen = datetime.datetime.now(datetime.timezone.utc)
        self.last_seen = datetime.datetime.now(datetime.timezone.utc)
        self.completed_tasks = []
        self.smart_captures = []
        #TODO: Verify our fields with any database entry. Create one if none exists. This can be an async task started from here, doesn't have to complete right away.
    def _check_database(self):
        pass