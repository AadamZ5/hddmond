
from hddmontools.hdd_interface import HddInterface
from hddmontools.hdd import Hdd

import random
import string
import time
import datetime
class MessageDispatcher:
    def __init__(self, socket):
        self.pending_messages = {} #Dict of {message_key: callback}
        self.recieved_waiting = {} #Dict of {message_key: data_string}

    def send(self, message, callback=None):
        """
        Sends a message, and then returns a message key.
        If callback is not supplied, the message will be stored until recieve is called to obtain it.
        """
        m_key = ''.join(random.choices(string.ascii_letters + string.digits, k=5))
        self.pending_messages[m_key] = callback
        #TODO: Socket send {"message_key": m_key, "data": some_data}

        return m_key

    def recv(self, key: str):
        """
        Checks to see if a message has returned.
        Returns `None` if no message is ready, and will Except if no message by that key is pending.
        """
        if key in self.pending_messages:
            return None
        elif key in self.recieved_waiting:
            data = self.recieved_waiting[key]
            del self.recieved_waiting[key]
            return data
        else:
            raise Exception("No message found")

    def send_and_recv(self, message, timeout_ms=None):
        """
        Sends a message and blocks until a response, or an optional timeout.
        """
        key = self.send(message)
        time_start = datetime.datetime.now()
        while True:
            data = self.recv(key)
            if data != None:
                return data
            else:
                if timeout_ms != None:
                    if datetime.datetime.now() - time_start > timeout_ms:
                        return None
                time.sleep(0.001)
                
        


class HddRemoteHost: #This doesnt inherit from HddInterface, because the HddRemoteReciever class already does that. This class will not be seen by Hddmon.
    """
    HddRemoteHost serves as a wrapper for a native HDD object on a client's end. The HddRemoteHost will host a connection to an HDD, which a reciever server
    will dispatch commands and data to and from. This will allow remote computers to host devices on one server.
    """
    def __init__(self, hdd:Hdd, address):
        self.hdd = hdd
        pass


class HddRemoteReciever(HddInterface):
    """
    HddRemoteReciever is used on the server side after an incoming connection is established with a client. The client will host a connection
    to their HDD using HddRemoteHost which serves as a translater or proxy for commands and data. 
    """
    def __init__(self):
        pass

    @property
    def serial(self) -> str:
        """
        Returns the serial for the device
        """
        raise NotImplementedError

    @property
    def model(self) -> str:
        """
        Returns the model for the device
        """
        raise NotImplementedError

    @property
    def wwn(self) -> str:
        """
        Returns the WWN that smartctl obtained for the device
        """
        raise NotImplementedError

    @property
    def node(self) -> str:
        """
        Returns the node for the device ("/dev/sdX" for example)
        """
        raise NotImplementedError

    @property
    def name(self) -> str:
        """
        Returns the kernel name for the device. ("sdX" for example)
        """
        raise NotImplementedError

    @property
    def port(self):
        """
        Returns the port for the device, if applicable.
        """
        raise NotImplementedError

    @property
    def capacity(self) -> float:
        """
        Returns the capacity in GiB for the device
        """
        raise NotImplementedError

    @property
    def medium(self) -> str:
        """
        Returns the medium of the device. (SSD or HDD)
        """
        raise NotImplementedError

    @property
    def seen(self) -> int:
        """
        Returns how many times this drive has been seen
        """
        raise NotImplementedError
    
    @seen.setter
    def seen(self, value: int):
        """
        Sets how many times this drive has been seen
        """
        raise NotImplementedError

    def add_task(self, *a, **kw) -> bool:
        """
        Adds a task to the HDD with any possible parameters sent in keyword arguments.
        """
        raise NotImplementedError

    def abort_task(self) -> bool: 
        """
        Should abort a currently running task.
        """
        raise NotImplementedError

    def add_task_changed_callback(self):
        """
        Registers a callback for when tasks change on a device.
        """
        raise NotImplementedError

    def update_smart(self):
        """
        Updates the SMART info for a drive.
        """
        raise NotImplementedError

    def capture_attributes(self):
        """
        Captures SMART attributes and returns the list.
        """
        raise NotImplementedError

    def get_available_tasks(self):
        """
        Gets the tasks that are available to start on this device. Should return a dictionary of display_name: class_name
        """
        raise NotImplementedError