
import asyncio
import socket
import logging

from lib.hdd_interface import ActiveHdd, TaskQueueInterface
from lib.hdd import Hdd
from lib.message_dispatcher import MessageDispatcher
from lib.config_service import ConfigService



class HddRemoteHost: #This doesnt inherit from HddInterface, because the HddRemoteReciever class already does that. This class will not be seen by Hddmon.
    """
    HddRemoteHost serves as a wrapper for a native HDD object on a client's end. The HddRemoteHost will host a connection to an HDD, which a reciever server
    will dispatch commands and data to and from. This will allow remote computers to host devices on one server.
    """
    def __init__(self, hdd:ActiveHdd, address):
        self.hdd = hdd
        self.hdd.add_task_changed_callback(self._tc_callback)
        self._socket = socket.create_connection(address, 10000)
        self.messenger = MessageDispatcher(self._socket, incoming_msg_callback=self._incoming_msg, event_callback=self._event_method)
        self.messenger.start()

    def stop(self):
        self.messenger.send_event({'event': 'close', 'data': None})
        self.messenger.stop()

    def _incoming_msg(self, *a, **kw):
        data = kw.get('data', None)

        if('attribute' in data): #They want an attribute from our hdd. Ask our hdd for the attribute, which it should have.
            attr = data['attribute']
            if('value' in data):
                val = data['value']
                try:
                    setattr(self.hdd, attr, val)
                except AttributeError:
                    print("Reciever tried to set {0} attribute, which doesn't exist!".format(attr))
            try:
                ret_val = getattr(self.hdd, attr)
            except AttributeError:
                print("Reciever asked for {0} attribute, which doesn't exist!".format(attr))
                ret_val = None
            
            return {attr: ret_val}
        elif('method' in data):
            method_name = data['method']
            args = data.get('args', [])
            kwargs = data.get('kwargs', {})
            try:
                meth_obj = getattr(self.hdd, method_name)
                ret_val = meth_obj(*args, **kwargs)
            except AttributeError:
                print("Reciever asked for {0} attribute, which doesn't exist!".format(method_name))
                ret_val = None
            
            return {method_name: ret_val}
            

    def _tc_callback(self, *a, **kw):
        #kw has the data we want.
        self.messenger.send_event({'event': 'task_change', 'data': kw})


    def _event_method(self, *a, **kw):
        event = kw.get('event', None)
        data = kw.get('data', None)

        if 'close' == event:
            print("Connection closed gracefully.")
            self.messenger.stop()
        elif 'lost_connection' in event:
            self.messenger.stop()
            print("We've lost connection!")
        elif data:
            #TODO: Parse this!
            pass

class HddRemoteReciever(ActiveHdd):
    """
    HddRemoteReciever is used on the server side after an incoming connection is established with a client. The client will host a connection
    to their HDD using HddRemoteHost which serves as a translater or proxy for commands and data. 
    """
    def __init__(self, socket: socket.socket, disconnected_cb=None):
        self.messenger = MessageDispatcher(socket, event_callback=self._event_method, incoming_msg_callback=self._incoming_msg)
        self.messenger.start()
        self._disconnected_callback = disconnected_cb
        self._task_change_callbacks = []
        self._cache = {}
        self._get_attribute('serial')
        self._get_attribute('model')
        self._get_attribute('node')
        self._get_attribute('name')
        self._get_attribute('wwn')
        self._get_attribute('capacity')

    def stop(self):
        self.messenger.send_event({'event': 'close', 'data': None})
        self.messenger.stop()

    def _task_change_callback(self, *a, **kw):
        for cb in self._task_change_callbacks:
            if callable(cb):
                cb(self, *a, **kw)

    def _incoming_msg(self, *a, **kw):
        #There is no logic here. We should not be getting requests from the HDD host.
        pass

    def _event_method(self, *a, **kw):
        event = kw.get('event', None)
        data = kw.get('data', None)

        if not event:
            return

        if 'close' == event:
            print("Myself is done")
        elif 'lost_connection' in event:
            self.messenger.stop()
            print("We've lost connection!")
            if(callable(self._disconnected_callback)):
                self._disconnected_callback(self)
                self._disconnected_callback = None
        elif 'task_change' in event:
            self._task_change_callback(**data)

    def _get_attribute(self, attribute, cache=True, cache_fallback=True):
        if (attribute in self._cache) and (cache == True):
            return self._cache[attribute]
        else:
            if not self.messenger.running:
                if attribute in self._cache:
                    return self._cache[attribute]
                else:
                    return None
            data = self.messenger.send_and_recv({'attribute': attribute}, 10000)
            if not data:
                if cache_fallback == True:
                    if attribute in self._cache:
                        return self._cache[attribute]
                    else:
                        return None
                else:
                    return None
            if attribute in data:
                self._cache[attribute] = data[attribute]
                return self._cache[attribute]
            else:
                return None

    def _set_attribute(self, attribute, value, cache=True, cache_fallback=True):
        if not self.messenger.running:
            if attribute in self._cache:
                return self._cache[attribute]
            else:
                return None
        data = self.messenger.send_and_recv({'attribute': attribute, 'value': value}, 10000)
        if not data:
            if cache_fallback == True:
                if attribute in self._cache:
                    return self._cache[attribute]
                else:
                    return None
            else:
                return None
        if attribute in data:
            self._cache[attribute] = data[attribute]
            return self._cache[attribute]
        else:
            return None

    def _run_method(self, method_name, cache_fallback=True, *a, **kw):
        if not self.messenger.running:
            return None
        
        data = self.messenger.send_and_recv({'method': method_name, 'args': a, 'kwargs': kw}, 10000)
        if not data:
            if cache_fallback == True:
                if method_name in self._cache:
                    return self._cache[method_name]
                else:
                    return None
            else:
                return None
        if method_name in data:
            self._cache[method_name] = data[method_name]
            return data[method_name]
        else:
            return None

    @property
    def TaskQueue(self) -> TaskQueueInterface:
        return self._get_attribute('TaskQueue')

    @property
    def locality(self) -> str:
        """
        Some string representing where the HDD exists. 
        HDDs on the same machine as the server should report 'local'
        """
        return str(self.messenger._socket.getpeername())

    @property
    def serial(self) -> str:
        """
        Returns the serial for the device
        """
        return self._get_attribute('serial')

    @property
    def model(self) -> str:
        """
        Returns the model for the device
        """
        return self._get_attribute('model')

    @property
    def wwn(self) -> str:
        """
        Returns the WWN that smartctl obtained for the device
        """
        return self._get_attribute('wwn')

    @property
    def node(self) -> str:
        """
        Returns the node for the device ("/dev/sdX" for example)
        """
        return self._get_attribute('node')

    @property
    def name(self) -> str:
        """
        Returns the kernel name for the device. ("sdX" for example)
        """
        return self._get_attribute('name')

    @property
    def port(self):
        """
        Returns the port for the device, if applicable.
        """
        return self._get_attribute('port')

    @property
    def capacity(self) -> float:
        """
        Returns the capacity in GiB for the device
        """
        return self._get_attribute('capacity')

    @property
    def medium(self) -> str:
        """
        Returns the medium of the device. (SSD or HDD)
        """
        return self._get_attribute('medium')

    @property
    def seen(self) -> int:
        """
        Returns how many times this drive has been seen
        """
        return self._get_attribute('seen', cache=False)
    
    @seen.setter
    def seen(self, value: int):
        """
        Sets how many times this drive has been seen
        """
        data = self._set_attribute('seen', value)

    @property
    def notes(self):
        """
        The notes object
        """
        return self._get_attribute('notes', cache=False)

    @property
    def smart_data(self):
        """
        The smart_data object
        """
        return self._get_attribute('smart_data', cache=False)

    def add_task(self, task_name, parameters, *a, **kw) -> bool:
        """
        Adds a task to the HDD with any possible parameters sent in keyword arguments.
        """
        return self._run_method('add_task', cache_fallback=False, task_name=task_name, parameters=parameters, *a, **kw)

    def abort_task(self) -> bool: 
        """
        Should abort a currently running task.
        """
        return self._run_method('abort_task', cache_fallback=False)

    def add_task_changed_callback(self, callback, *a, **kw):
        """
        Registers a callback for when tasks change on a device.
        """
        self._task_change_callbacks.append(callback)

    def update_smart(self):
        """
        Updates the SMART info for a drive.
        """
        return self._run_method('update_smart')

    def get_available_tasks(self):
        """
        Gets the tasks that are available to start on this device. Should return a dictionary of display_name: class_name
        """
        return self._run_method('get_available_tasks')

    def disconnect(self):
        """
        Block and finalize anything on the HDD
        """
        self.stop()

import threading
from injectable import injectable, inject

@injectable(singleton=True)
class HddRemoteRecieverServer:
    def __init__(self, udp_discovery_server_address=None):
        self.logger = logging.getLogger(__name__ + "." + self.__class__.__qualname__)
        self.logger.setLevel(logging.DEBUG)
        self.logger.info("Initializing HddRemoteRecieverServer...")
        self._udp_address = udp_discovery_server_address
        if(self._udp_address != None):
            self.discovery_server = socket.socket(family=socket.AF_INET, type=socket.SOCK_DGRAM, proto=socket.IPPROTO_UDP)
            self.discovery_server.setsockopt(socket.SOL_SOCKET, socket.SO_BROADCAST, 1)# Enable broadcasting mode
        else:
            self.discovery_server = None
        
        cfg_svc = inject(ConfigService)
        port = cfg_svc.data["hddmon_remote_host"]["port"]
        self._tcp_address = ('', port)
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

    def _do_callbacks(self, action: str, device: ActiveHdd):
        for c in self._callbacks:
            c(action=action, device=device)

    def _hdd_rem_disconnect(self, device: HddRemoteReciever):
        self._do_callbacks('remove', device)

    def _server(self):
        while self._loop_go:
            try:
                conn, add = self.server.accept()
            except socket.timeout:
                pass #The socket timed out. No failure.
            else:
                if(conn):
                    new_client = HddRemoteReciever(conn, self._hdd_rem_disconnect)
                    self._do_callbacks('add', new_client)


    def start(self):
        self.logger.info("Starting HddRemoteRecieverServer...")
        self._loop_go = True
        self._tcp_thread.start()

    def stop(self):
        self.logger.info("Stopping HddRemoteRecieverServer...")
        self._loop_go = False
        self._tcp_thread.join()
        self.server.shutdown(socket.SHUT_RDWR)
