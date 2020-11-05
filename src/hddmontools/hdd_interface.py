from abc import ABC, abstractmethod
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

class HddInterface(ABC):

    @property
    @abstractmethod
    def TaskQueue(self) -> TaskQueueInterface:
        """
        Returns the TaskQueue interface for the device
        """
        raise NotImplementedError

    @property
    @abstractmethod
    def serial(self) -> str:
        """
        Returns the serial for the device
        """
        raise NotImplementedError

    @property
    @abstractmethod
    def model(self) -> str:
        """
        Returns the model for the device
        """
        raise NotImplementedError

    @property
    @abstractmethod
    def wwn(self) -> str:
        """
        Returns the WWN that smartctl obtained for the device
        """
        raise NotImplementedError

    @property
    @abstractmethod
    def node(self) -> str:
        """
        Returns the node for the device ("/dev/sdX" for example)
        """
        raise NotImplementedError

    @property
    @abstractmethod
    def name(self) -> str:
        """
        Returns the kernel name for the device. ("sdX" for example)
        """
        raise NotImplementedError

    @property
    @abstractmethod
    def port(self):
        """
        Returns the port for the device, if applicable.
        """
        raise NotImplementedError

    @property
    @abstractmethod
    def capacity(self) -> float:
        """
        Returns the capacity in GiB for the device
        """
        raise NotImplementedError

    @property
    @abstractmethod
    def medium(self) -> str:
        """
        Returns the medium of the device. (SSD or HDD)
        """
        raise NotImplementedError

    @property
    @abstractmethod
    def seen(self) -> int:
        """
        Returns how many times this drive has been seen
        """
        raise NotImplementedError
    
    @seen.setter
    @abstractmethod
    def seen(self, value: int):
        """
        Sets how many times this drive has been seen
        """
        raise NotImplementedError

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
    def add_task_changed_callback(self):
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
    def capture_attributes(self):
        """
        Captures SMART attributes and returns the list.
        """
        raise NotImplementedError

    @abstractmethod
    def get_available_tasks(self):
        """
        Gets the tasks that are available to start on this device. Should return a dictionary of display_name: class_name
        """
        raise NotImplementedError