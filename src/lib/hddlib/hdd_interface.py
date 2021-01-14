import strawberry

from typing import  Optional
from abc import ABC, abstractmethod
from strawberry.scalars import ID

from lib.hddlib.hdd_entry import HddEntry
from lib.hddlib.smart_data import SmartCapture
from lib.tasklib.taskqueue import TaskQueue

@strawberry.type(description="Represents data about a device that is currently connected to the application")
class ActiveHdd(HddEntry):
    """
    Represents data about a device that is currently connected to the application
    """

    serial: ID = strawberry.field(description="The serial of the device")
    model: str = strawberry.field(description="The model number for the device")
    wwn: Optional[str] = strawberry.field(description="The world-wide-number of the device, if applicable")
    node: str = strawberry.field(description="The system device node, local to the device's operating environment")
    name: str = strawberry.field(description="The kernel name of the device, local to the device's operating environment")
    port: Optional[str] = strawberry.field(description="The port the device is connected to, if found and if applicable, local to the device's operating environment")
    capacity: float = strawberry.field(description="The capacity of the device in GiB")
    medium: str = strawberry.field(description="The type of storage device, usually HDD or SSD")
    seen: int = strawberry.field(description="The amount of times the device has been seen")
    locality: str = strawberry.field(description="A string describing the operating environment that the device is located at")
    task_queue: TaskQueue = strawberry.field(description="The task queue manages queued and running tasks for the device")

    def __init__(self, serial: ID, model: str, wwn: Optional[str], capacity: float, node: str, port: Optional[str], medium: str, locality: str, task_queue: TaskQueue):
        super().__init__(serial, model, wwn, capacity)
        self.node = node
        self.port = port
        self.medium = medium
        self.locality = locality
        self.task_queue = task_queue

    @property
    @abstractmethod
    def notes(self):
        """
        The notes object
        """
        raise NotImplementedError

    @property
    @abstractmethod
    def smart_data(self) -> SmartCapture:
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

