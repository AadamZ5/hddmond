from abc import ABC, abstractmethod

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