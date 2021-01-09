import pyudev
import pySMART
import time
import subprocess
import datetime
import enum
import logging
import strawberry

from injectable import inject
from typing import Dict, Any, Optional, Union

from strawberry.scalars import ID

from hddmontools.task_service import TaskService
from hddmontools.test import Test
from hddmontools.task import Task, TaskQueue, ExternalTask
from hddmontools.portdetection import PortDetection
from hddmontools.notes import Notes
from hddmontools.hdd_interface import ActiveHdd, TaskQueueInterface
from hddmondtools.hddmon_dataclasses import SmartData

#
#   This file holds the class definition for Hdd. Hdd holds all of the information about a hard-drive (or solid-state drive) in the system.  
#

@strawberry.type
class Hdd(ActiveHdd):
    """
    Class for storing data about HDDs
    """

    @property
    def TaskQueue(self) -> TaskQueueInterface:
        """
        Returns the serial for the device
        """
        return self._TaskQueue

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

    @property
    def notes(self):
        """
        The notes object
        """
        return self._notes

    @property
    def smart_data(self) -> SmartData:
        """
        The smart_data object
        """
        self.update_smart()
        return SmartData.FromSmartDev(self._smart)

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
        self.logger = logging.getLogger(__name__ + "." + self.__class__.__qualname__ + f'[{node}]')
        self.logger.setLevel(logging.DEBUG)
        self.logger.debug(f"Initializing new HDD from {node}")
        self.serial = '"HDD"'
        self.model = str()
        self.wwn = str()
        self.node = node
        self.name = str(node).replace('/dev/', '')
        self.logger.debug("Getting UDEV device context...")
        self._udev = pyudev.Devices.from_device_file(pyudev.Context(), node)
        self._task_changed_callbacks = []
        self.logger.debug("Getting SMART device context...")
        self._smart = pySMART.Device(self.node)
        self.port = None
        self._TaskQueue = TaskQueue(continue_on_error=False, task_change_callback=self._task_changed)
        self._size = self._smart.capacity
        self._pci_address = None
        self._notes = Notes()
        self.seen = 0
        self.logger.debug("Trying to get PCI and port...")
        port_detector = inject(PortDetection)
        port_detector.Update()
        self._pci_address = port_detector.GetPci(self._udev.sys_path)
        self.logger.debug(f"Got PCI as {self._pci_address}.")
        self.port = port_detector.GetPort(self._udev.sys_path, self._pci_address, self.serial)
        self.logger.debug(f"Got port as {self.port}.")

        try:
            sizeunit = self._smart.capacity.split()
            unit = sizeunit[1]
            size = float(sizeunit[0])

            if unit.lower() == 'tb':
                size = size * 1000

            self.capacity = size
        except AttributeError:
            self.capacity = None
            pass
        except Exception as e:
            self.capacity = None
            self.logger.error("Exception occurred while parsing capacity of drive " + self.serial + f". This drive may not function properly. {str(e)}")

        super().__init__(self.serial, self.model, self.wwn, self.capacity)

        self._smart_last_call = time.time()
        self.medium = None #SSD or HDD

        #Check interface
        if(self._smart.interface != None):
            self.serial = str(self._smart.serial).replace('-', '')
            self.model = self._smart.model
            if(self._smart.is_ssd):
                self.medium = "SSD"
            else:
                self.medium = "HDD"
        else:
            self.serial = "Unknown HDD"
            self.model = ""
            #Idk where we go from here
        self.logger.debug(f"My serial is {self.serial}.")
        n = 'n' if self.medium == "" else ''
        med = self.medium if self.medium != "" else "unknown medium"
        self.logger.debug(f"I am a{n} {med}.")
        
    @staticmethod
    def FromSmartDevice(d: pySMART.Device):
        '''
        Create a HDD object from a pySMART Device object
        '''
        return Hdd("/dev/" + d.name)

    @staticmethod
    def FromUdevDevice(d: pyudev.Device): #pyudev.Device
        '''
        Create a HDD object from a pyudev Device object
        '''
        h = Hdd(d.devicenode)
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

    def add_task(self, taskname: str, parameters: Dict[str, Any], *a, **kw):
        task_svc = TaskService()
        task_obj = task_svc.task_types[taskname]
        parameter_schema = Task.GetTaskParameterSchema(task_obj)
        if(parameter_schema != None and len(parameters.keys()) <= 0):
            return {'need_parameters': parameter_schema, 'task': taskname}
        else:
            t: Task = task_obj(self, **parameters)
            self.logger.debug(f"Sending task {t.name} to my task queue")
            self._TaskQueue.AddTask(t)

    def abort_task(self, *a, **kw):
        self._TaskQueue.AbortCurrentTask(*a, **kw)
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
        return task_svc.displaynames.copy()

    async def disconnect(self):
        """
        Block and finalize anything on the HDD
        """
        if(self.TaskQueue.CurrentTask != None) and (self.TaskQueue.Error != True):
            if(isinstance(self.TaskQueue.CurrentTask, ExternalTask)) or (isinstance(self.TaskQueue.CurrentTask, Test)):
                self.logger.info("Detaching task " + str(self.TaskQueue.CurrentTask.name) + " on " + self.serial)
                await self.TaskQueue.CurrentTask.detach()
            else:
                self.logger.info("Aborting task " + str(self.TaskQueue.CurrentTask.name) + " (PID: " + str(self.TaskQueue.CurrentTask.PID) + ") on " + self.serial)
                await self.TaskQueue.CurrentTask.abort(wait=True) #Wait for abortion so database entries can be entered before we disconnect the database.
            
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