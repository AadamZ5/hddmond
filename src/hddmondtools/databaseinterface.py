from datetime import datetime
from typing import List, Optional
import strawberry
from strawberry.scalars import ID
from .hddmon_dataclasses import HddData, TaskData, AttributeData, ImageData
from abc import ABC, abstractmethod

@strawberry.interface
class HddEntry(ABC):
    """
    Represents data about a device entry in the database
    """

    serial: ID = strawberry.field(description="The serial of the device")
    model: str = strawberry.field(description="The model number for the device")
    wwn: Optional[str] = strawberry.field(description="The world-wide-number of the device, if applicable")
    capacity: float = strawberry.field(description="The capacity of the device in GiB")
    first_seen: datetime = strawberry.field(description="The time the device first appeared in the application")
    last_seen: datetime = strawberry.field(description="The last time the device was seen in the application")
    seen: int = strawberry.field(description="The amount of times the device has been seen")
    decommissioned: bool = strawberry.field(description="If the drive is considered decommissioned, or unusable")
    completed_tasks: List[str] = strawberry.field(description="A list of tasks that have been run on the device") #TODO: Change to proper strawberry Task type!
    smart_captures: List[str] = strawberry.field(description="A list of S.M.A.R.T attribute snapshots") #TODO: Change to proper strawberry SmartCapture type!

    def __init__(self, serial: ID, model: str, wwn: Optional[str], capacity: float):
        pass #TODO: Create a proxy for fields that don't rely on live data, and proxy them to the DB.



class GenericDatabase(ABC):
    '''
    This class defines the structure needed for a database implimentation on hddmond.
    '''

    @abstractmethod
    def connect(self, *a, **kw):
        '''
        When overridden, should attempt to connect to a database with supplied info in __init__.
        Returns weather connecting succeeded or not.

        It would be wise to have this method create the databases needed to store the data, in the case
        that this is a brand new instance.
        '''
        return False
    
    @abstractmethod
    def disconnect(self):
        '''
        When overridden, should disconnect (if applicable) from the database.
        '''
        pass

    @abstractmethod
    def update_hdd(self, hdd: HddData):
        pass

    @abstractmethod
    def see_hdd(self, serial: str):
        pass

    @abstractmethod
    def add_task(self, serial: str, task: TaskData):
        pass

    # @abstractmethod
    # def decommission(self, decommissioned=True):
    #     pass

    @abstractmethod
    def insert_attribute_capture(self, hdd: HddData):
        pass