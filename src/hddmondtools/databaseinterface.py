from .hddmon_dataclasses import HddData, TaskData, AttributeData, ImageData
from abc import ABC, abstractmethod

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