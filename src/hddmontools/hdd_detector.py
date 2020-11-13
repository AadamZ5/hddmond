from abc import ABC, abstractmethod

class HddDetector(ABC):

    @abstractmethod
    def start(self):
        pass

    @abstractmethod
    def stop(self):
        pass

    @abstractmethod
    def add_change_callback(self, callback, *a, **kw):
        """
        Callbacks to be called when a device is added or removed.

        Should call back with kwargs 'action': 'add'|'remove', 'serial': str, and 'node': str
        """
        pass
