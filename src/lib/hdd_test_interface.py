import strawberry
import datetime

from typing import Optional
from strawberry.scalars import ID

from lib.hdd_interface import ActiveHdd
from lib.task import TaskQueue, TaskService, Task
from lib.notes import Notes
from lib.hddmon_dataclasses import SmartData

@strawberry.type
class HddTestInterface(ActiveHdd):

    serial: ID
    model: str
    wwn: Optional[str]
    node: str
    name: str
    port: Optional[str]
    capacity: float
    medium: str
    seen: int
    locality: str

    @strawberry.field
    def last_seen(self) -> datetime.datetime:
        return datetime.datetime.now()

    def __init__(self, mock_smart: SmartData = SmartData(str(datetime.datetime.now(datetime.timezone.utc)), [], "Test", "ata", [], True, True, "PASS", []), mock_node: str = "/dev/sdT", mock_serial: str = "HDD-TEST-INTERFACE", mock_model: str = "TEST-MODEL", mock_capacity: float = "1234.5", mock_locality: str = "local", mock_tasksvc = TaskService()):
        self.node = mock_node
        self.model = mock_model
        self.serial = mock_serial
        self.capacity = mock_capacity
        self._taskqueue = TaskQueue(task_change_callback=self._tc_callback)
        self._smart = mock_smart
        self.locality = mock_locality
        self._tasksvc = mock_tasksvc

        self.seen = 0
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
