from abc import ABC, abstractmethod
import functools
import inspect
from controllermodel import GenericController

class ApiInterface(GenericController, ABC):
    
    def __init__(self):
        super().__init__()
        self._commandlist = {} #dict of {command_name: command}
        self._description_list = {} #dict of {command_name: description}
        self._ufc = 0 # Un-identified function counter

    def find_action(self, command: str, *a, **kw):
        return self.execute_action(command, *a, **kw)

    @abstractmethod
    def broadcast_data(self, data, *a, **kw):
        """
        Broadcasts data to all connected clients.
        """
        raise NotImplementedError(str(type(self)) + ": This method should be overridden!")

    @abstractmethod
    def start(self, *a, **k):
        """
        Starts the server
        """
        raise NotImplementedError(str(type(self)) + ": This method should be overridden!")

    @abstractmethod
    def stop(self, *a, **k):
        """
        Stops the server
        """
        raise NotImplementedError(str(type(self)) + ": This method should be overridden!")