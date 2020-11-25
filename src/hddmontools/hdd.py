from __future__ import annotations
import pyudev
import pySMART
import time
import subprocess
import datetime
import enum
from .task_service import TaskService
from .pciaddress import PciAddress
from .test import Test
from .task import Task, TaskQueue, ExternalTask
from .portdetection import PortDetection
from .notes import Notes
import proc.core
from injectable import inject
from .hdd_interface import HddInterface, TaskQueueInterface
from hddmondtools.hddmon_dataclasses import SmartData

#
#   This file holds the class definition for Hdd. Hdd holds all of the information about a hard-drive (or solid-state drive) in the system.  
#
class HealthStatus(enum.Enum):
    Failing = 0,
    ShortTesting = 1,
    LongTesting = 2,
    Default = 3,
    Passing = 4,
    Warn = 5,
    Unknown = 6,

    def __str__(self):
        return self.name

class Hdd(HddInterface):
    """
    Class for storing data about HDDs
    """

    @property
    def TaskQueue(self) -> TaskQueueInterface:
        """
        Returns the serial for the device
        """
        return self._TaskQueue

    @property
    def serial(self) -> str:
        """
        Returns the serial for the device
        """
        return self._serial

    @property
    def model(self) -> str:
        """
        Returns the model for the device
        """
        return self._model

    @property
    def wwn(self) -> str:
        """
        Returns the WWN that smartctl obtained for the device
        """
        return self._wwn

    @property
    def node(self) -> str:
        """
        Returns the node for the device ("/dev/sdX" for example)
        """
        return self._node

    @property
    def name(self) -> str:
        """
        Returns the kernel name for the device. ("sdX" for example)
        """
        return self._name

    @property
    def port(self):
        """
        Returns the port for the device, if applicable.
        """
        return self._port

    @property
    def capacity(self) -> float:
        """
        Returns the capacity in GiB for the device
        """
        return self._capacity

    @property
    def medium(self) -> str:
        """
        Returns the medium of the device. (SSD or HDD)
        """
        return self._medium

    @property
    def seen(self) -> int:
        """
        Returns how many times this drive has been seen
        """
        return self._seen

    @seen.setter
    def seen(self, value: int):
        """
        Sets how many times this drive has been seen
        """
        self._seen = value

    @property
    def notes(self):
        """
        Sets how many times this drive has been seen
        """
        return self._notes

    @property
    def smart_data(self) -> SmartData:
        """
        The smart_data object
        """
        self.update_smart()
        return SmartData.FromSmartDev(self._smart)
        
    @property
    def locality(self) -> str:
        """
        Some string representing where the HDD exists. 
        HDDs on the same machine as the server should report 'local'
        """
        return 'local'

    def __getstate__(self):
        # Copy the object's state from self.__dict__ which contains
        # all our instance attributes. Always use the dict.copy()
        # method to avoid modifying the original state.
        state = self.__dict__.copy()
        # Remove the unpicklable entries. Udev referres to CDLL which won't pickle.
        state['_udev'] = None
        state['_task_changed_callbacks'] = None
        return state

    def __setstate__(self, state):
        # Restore instance attributes (i.e., serial and model).
        self.__dict__.update(state)
        # Restore the udev link
        self._udev = pyudev.Devices.from_device_file(pyudev.Context(), self.node)

    def __init__(self, node: str):
        '''
        Create a hdd object from its symlink node '/dev/sd?'
        '''
        self._serial = '"HDD"'
        self._model = str()
        self._wwn = str()
        self._node = node
        self._name = str(node).replace('/dev/', '')
        self._udev = pyudev.Devices.from_device_file(pyudev.Context(), node)
        self._task_changed_callbacks = []
        self._smart = pySMART.Device(self.node)
        self._port = None
        self._TaskQueue = TaskQueue(continue_on_error=False, task_change_callback=self._task_changed)
        self._size = self._smart.capacity
        self._pci_address = None
        self._notes = Notes()
        self._seen = 0

        port_detector = inject(PortDetection)
        port_detector.Update()
        self._pci_address = port_detector.GetPci(self._udev.sys_path)
        self._port = port_detector.GetPort(self._udev.sys_path, self._pci_address, self.serial)

        try:
            sizeunit = self._smart.capacity.split()
            unit = sizeunit[1]
            size = float(sizeunit[0])

            if unit.lower() == 'tb':
                size = size * 1000

            self._capacity = size
        except AttributeError:
            self._capacity = None
            pass
        except Exception:
            self._capacity = None
            print("Exception occurred while parsing capacity of drive " + self.serial + ". This drive may not function properly")

        self._smart_last_call = time.time()
        self._medium = None #SSD or HDD

        #Check interface
        if(self._smart.interface != None):
            self._serial = str(self._smart.serial).replace('-', '')
            self._model = self._smart.model
            if(self._smart.is_ssd):
                self._medium = "SSD"
            else:
                self._medium = "HDD"
        else:
            self._serial = "Unknown HDD"
            self._model = ""
            #Idk where we go from here
        
    @staticmethod
    def FromSmartDevice(d: pySMART.Device) -> Hdd:
        '''
        Create a HDD object from a pySMART Device object
        '''
        return Hdd("/dev/" + d.name)

    @staticmethod
    def FromUdevDevice(d: pyudev.Device) -> Hdd: #pyudev.Device
        '''
        Create a HDD object from a pyudev Device object
        '''
        h = Hdd(d.device_node)
        h._udev = d
        return h

    @staticmethod
    def IsHdd(node: str) -> bool:
        '''
        See if this storage object has an HDD-like interface.
        '''
        if(pySMART.Device(node).interface != None):
            return True
        else:
            return False

    def add_task(self, task_name, parameters, *a, **kw):
        task_svc = TaskService()
        task_obj = task_svc.task_types[task_name]
        parameter_schema = Task.GetTaskParameterSchema(task_obj)
        if(parameter_schema != None and len(parameters.keys()) <= 0):
            return {'need_parameters': parameter_schema, 'task': task_name}
        else:
            t = task_obj(self, **parameters)
            self._TaskQueue.AddTask(t)

    def abort_task(self, *a, **kw):
        pass

    def _task_changed(self, *args, **kw):
        for c in self._task_changed_callbacks:
            if c != None and callable(c):
                c(self, *args, **kw)

    def add_task_changed_callback(self, callback, *a, **kw) -> None:
        self._task_changed_callbacks.append(callback)

    def update_smart(self) -> None:
        self._smart.update()

    def get_available_tasks(self):
        task_svc = TaskService()
        return task_svc.display_names.copy()

    def disconnect(self):
        """
        Block and finalize anything on the HDD
        """
        if(self.TaskQueue.CurrentTask != None) and (self.TaskQueue.Error != True):
                if(isinstance(self.TaskQueue.CurrentTask, ExternalTask)) or (isinstance(self.TaskQueue.CurrentTask, Test)):
                    print("Detaching task " + str(self.TaskQueue.CurrentTask.name) + " on " + self.serial)
                    self.TaskQueue.CurrentTask.detach()
                else:
                    print("Aborting task " + str(self.TaskQueue.CurrentTask.name) + " (PID: " + str(self.TaskQueue.CurrentTask.PID) + ") on " + self.serial)
                    self.TaskQueue.CurrentTask.abort(wait=True) #Wait for abortion so database entries can be entered before we disconnect the database.
            
    def __str__(self):
        if(self.serial):
            return self.serial
        else:
            return "???"

    def __repr__(self):
        if(self._smart.is_ssd):
            t = "SSD"
        else:
            t = "HDD"
        s = t + " " + str(self.serial) + " at " + str(self.node)
        return "<" + s + ">"

from multiprocessing.managers import BaseManager
class HddManager(BaseManager): pass
HddManager.register('Hdd', Hdd)