from .hddmon_dataclasses import HddData, TaskData, AttributeData
import sgqlc

class GenericDatabase:
    '''
    This class defines the structure needed for a database implimentation on hddmond.
    '''

    def __init__(self):
        pass

    def connect(self, *a, **kw):
        '''
        When overridden, should attempt to connect to a database with supplied info in __init__.
        Returns weather connecting succeeded or not.
        '''
        return False
    
    def disconnect(self):
        '''
        When overridden, should disconnect (if applicable) from the database.
        '''

    def update_hdd(self, hdd: HddData):
        pass

    def see_hdd(self, serial: str):
        pass

    def add_task(self, serial: str, task: TaskData):
        pass

    def decommission(self, decommissioned=True):
        pass

    def insert_attribute_capture(self, serial: str, attribute_capture):
        pass