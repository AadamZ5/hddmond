
import asyncio
import socket

from hddmontools.hdd_interface import HddInterface
from hddmontools.hdd import Hdd
from hddmontools.message_dispatcher import MessageDispatcher
                
class HddRemoteHost: #This doesnt inherit from HddInterface, because the HddRemoteReciever class already does that. This class will not be seen by Hddmon.
    """
    HddRemoteHost serves as a wrapper for a native HDD object on a client's end. The HddRemoteHost will host a connection to an HDD, which a reciever server
    will dispatch commands and data to and from. This will allow remote computers to host devices on one server.
    """
    def __init__(self, hdd:Hdd, address):
        self.hdd = hdd
        self._socket = socket.create_connection(address, 10000)
        self.messenger = MessageDispatcher(self._socket)


class HddRemoteReciever(HddInterface):
    """
    HddRemoteReciever is used on the server side after an incoming connection is established with a client. The client will host a connection
    to their HDD using HddRemoteHost which serves as a translater or proxy for commands and data. 
    """
    def __init__(self, socket: socket.socket):
        self.messenger = MessageDispatcher(socket, event_callback=self._event_method)

    def _event_method(self, *a, **kw):
        pass

    @property
    def serial(self) -> str:
        """
        Returns the serial for the device
        """
        data = self.messenger.send_and_recv({'get': 'serial'}, 10000)
        return data['serial']

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

import threading
from injectable import injectable

@injectable(singleton=True)
class HddRemoteRecieverServer:
    def __init__(self, udp_discovery_server_address=None):
        self._udp_address = udp_discovery_server_address
        if(self._udp_address != None):
            self.discovery_server = socket.socket(family=socket.AF_INET, type=socket.SOCK_DGRAM, proto=socket.IPPROTO_UDP)
            self.discovery_server.setsockopt(socket.SOL_SOCKET, socket.SO_BROADCAST, 1)# Enable broadcasting mode
        else:
            self.discovery_server = None
        
        self._tcp_address = ('', 56567)
        self.server = socket.create_server(self._tcp_address, family=socket.AF_INET)
        #self.server.setsockopt(socket.SOL_SOCKET, socket.SOCK_NONBLOCK, 1)# No block
        self.server.settimeout(5)# 5 second timeout
        self._tcp_thread = threading.Thread(name="remote_hdd_server", target=self._server)
        self._loop_go = True

        #self._clients = {} #List of HddRemoteRecievers
        self._callbacks = [] #List of callable

    def register_devchange_callback(self, callback):
        """
        Registers a callback that when called, has kwargs "action" ('add'/'remove') and "device" which is an HddInterface
        """

        if(callback != None) and (callable(callback)):
            self._callbacks.append(callback)

    def _do_callbacks(self, action: str, device: HddInterface):
        for c in self._callbacks:
            c(action=action, device=device)

    def _server(self):
        while self._loop_go:
            try:
                conn, add = self.server.accept()
            except socket.timeout:
                pass #The socket timed out. No failure.
            else:
                if(conn):
                    new_client = HddRemoteReciever(conn)
                    self._do_callbacks('add', new_client)


    def start(self):
        self._loop_go = True
        self._tcp_thread.start()

    def stop(self):
        self._loop_go = False
        self._tcp_thread.join()
        self.server.shutdown(socket.SHUT_RDWR)
