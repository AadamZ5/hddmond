import strawberry

from typing import Union, Optional
from abc import ABC, abstractmethod

from strawberry.scalars import ID

from hddmondtools.databaseinterface import HddEntry
from hddmondtools.hddmon_dataclasses import SmartData

class TaskQueueInterface(ABC):
    
    @property
    @abstractmethod
    def Pause(self) -> bool:
        """
        Returns if the queue is paused
        """
        raise NotImplementedError

    @Pause.setter
    @abstractmethod
    def Pause(self, value: bool):
        """
        Sets the pause for the queue
        """
        raise NotImplementedError

    @property
    @abstractmethod
    def Error(self):
        """
        If the queue has an error.
        """
        raise NotImplementedError

    @Error.setter
    @abstractmethod
    def Error(self, value: bool):
        """
        Sets the error status for the queue
        """
        raise NotImplementedError

    @property
    @abstractmethod
    def Full(self) -> bool:
        """
        If the queue is at capacity
        """
        raise NotImplementedError

@strawberry.type
class ActiveHdd(HddEntry):

    @property
    @abstractmethod
    def TaskQueue(self) -> TaskQueueInterface:
        """
        Returns the TaskQueue interface for the device
        """
        raise NotImplementedError

    serial: ID
    model: str
    wwn: Optional[str]
    node: str
    name: str
    port: Optional[str]
    capacity: float
    medium: str
    seen: int
    locality: str

    def __init__(self, serial: ID, model: str, wwn: Optional[str], capacity: float):
        super().__init__(serial, model, wwn, capacity)

    @property
    @abstractmethod
    def notes(self):
        """
        The notes object
        """
        raise NotImplementedError

    @property
    @abstractmethod
    def smart_data(self) -> SmartData:
        """
        The smart_data object
        """
        raise NotImplementedError

    @abstractmethod
    def disconnect(self):
        """
        Block and finalize anything on the HDD
        """
        raise NotImplementedError

    @abstractmethod
    def add_task(self, *a, **kw) -> bool:
        """
        Adds a task to the HDD with any possible parameters sent in keyword arguments.
        """
        raise NotImplementedError

    @abstractmethod
    def abort_task(self) -> bool: 
        """
        Should abort a currently running task.
        """
        raise NotImplementedError

    @abstractmethod
    def add_task_changed_callback(self, *a, **kw):
        """
        Registers a callback for when tasks change on a device.
        """
        raise NotImplementedError

    @abstractmethod
    def update_smart(self):
        """
        Updates the SMART info for a drive.
        """
        raise NotImplementedError

    @abstractmethod
    def get_available_tasks(self):
        """
        Gets the tasks that are available to start on this device. Should return a dictionary of display_name: class_name
        """
        raise NotImplementedError

