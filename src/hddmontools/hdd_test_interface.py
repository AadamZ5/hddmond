from hddmontools.hdd_interface import HddInterface
from hddmontools.task import TaskQueue, TaskService, Task
from hddmontools.notes import Notes
from hddmondtools.hddmon_dataclasses import SmartData

import datetime

class HddTestInterface(HddInterface):
    def __init__(self, mock_smart: SmartData = SmartData(str(datetime.datetime.now(datetime.timezone.utc)), [], "Test", "ata", [], True, True, "PASS", []), mock_node: str = "/dev/sdT", mock_serial: str = "HDD-TEST-INTERFACE", mock_model: str = "TEST-MODEL", mock_capacity: float = "1234.5", mock_locality: str = "local", mock_tasksvc = TaskService()):
        self._node = mock_node
        self._model = mock_model
        self._serial = mock_serial
        self._capacity = mock_capacity
        self._taskqueue = TaskQueue(task_change_callback=self._tc_callback)
        self._smart = mock_smart
        self._locality = mock_locality
        self._tasksvc = mock_tasksvc

        self._seen = 0
        self._notes = Notes()

        self._tc_callbacks = []

    def _tc_callback(self, *a, **kw):
        for c in self._tc_callbacks:
            if c != None and callable(c):
                c(self, *a, **kw)

    @property
    def TaskQueue(self):
        """
        Returns the TaskQueue interface for the device
        """
        return self._taskqueue

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
        return "1234"

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
        return self._node.replace("/dev/", "")

    @property
    def port(self):
        """
        Returns the port for the device, if applicable.
        """
        return "Nowhere"

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
        return "HDD"

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
        The notes object
        """
        return self._notes

    @property
    def smart_data(self) -> SmartData:
        """
        The smart_data object
        """
        return self._smart

    @property
    def locality(self) -> str:
        """
        Some string representing where the HDD exists. 
        HDDs on the same machine as the server should report 'local'
        """
        return self._locality


    def disconnect(self):
        """
        Block and finalize anything on the HDD
        """
        pass

    
    def add_task(self, task_name, parameters, *a, **kw) -> bool:
        """
        Adds a task to the HDD with any possible parameters sent in keyword arguments.
        """
        task_svc = self._tasksvc
        task_obj = task_svc.task_types[task_name]
        parameter_schema = Task.GetTaskParameterSchema(task_obj)
        if(parameter_schema != None and len(parameters.keys()) <= 0):
            return {'need_parameters': parameter_schema, 'task': task_name}
        else:
            #t = task_obj(self, **parameters)
            #self._taskqueue.AddTask(t)
            self._tc_callback(action='taskadded', data={'taskqueue': self.TaskQueue})
            print("Skipping adding task on test instance.")

    def abort_task(self) -> bool: 
        """
        Should abort a currently running task.
        """
        self._taskqueue.AbortCurrentTask()
        return True
    
    def add_task_changed_callback(self, callback, *a, **kw):
        """
        Registers a callback for when tasks change on a device.
        """
        self._tc_callbacks.append(callback)

    
    def update_smart(self):
        """
        Updates the SMART info for a drive.
        """
        pass

    
    def get_available_tasks(self):
        """
        Gets the tasks that are available to start on this device. Should return a dictionary of display_name: class_name
        """
        task_svc = self._tasksvc
        return task_svc.display_names.copy()
