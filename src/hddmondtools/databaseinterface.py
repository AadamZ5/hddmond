from .hddmon_dataclasses import HddData, TaskData
from abc import ABC, abstractmethod

class DatabaseInterface(ABC):
    '''
    This class defines the structure needed for a database implimentation on hddmond.
    '''

    def __init__(self):
        pass

    @abstractmethod
    async def connect(self, *a, **kw):
        '''
        When overridden, should attempt to connect to a database with supplied info in __init__.
        Returns weather connecting succeeded or not.

        It would be wise to have this method create the databases needed to store the data, in the case
        that this is a brand new instance.
        '''
        return False
    
    @abstractmethod
    async def disconnect(self):
        '''
        When overridden, should disconnect (if applicable) from the database.
        '''
        pass

    @abstractmethod
    async def connected(self):
        '''
        This method should return if the database is currently connected.
        '''
        pass

    @abstractmethod
    async def update_hdd(self, hdd: HddData):
        '''
        This method updates the HDD's information with the latest and greatest data. 
        
        For example, when a HDD we've seen before is inserted, let's update the information
        just in case any of it has changed.
        '''
        pass

    @abstractmethod
    async def see_hdd(self, serial: str) -> int:
        '''
        This method will "see" a HDD, which increases the 'seen' counter in the database. 
        This method should return the new 'seen' value.
        '''
        pass

    @abstractmethod
    async def add_task(self, serial: str, task: TaskData):
        '''
        This method is called when a task is completed (successfully or not) on a HDD. 
        The task's data should be saved to be referenced later for historical data.
        '''
        pass

    @abstractmethod
    async def decommission(self, decommissioned=True):
        '''
        This method will decomission a HDD should the user decide to do that. 
        A decommissioned HDD will have a different look on the UI and alert the user
        that the HDD is decommissioned.
        '''
        pass

    @abstractmethod
    async def insert_attribute_capture(self, hdd: HddData):
        '''
        This method will insert a capture of the HDD's SMART data. This information is useful for
        historical attribute trends. 
        '''
        pass