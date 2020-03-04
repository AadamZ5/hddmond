from dataclasses import dataclass
from py_ts_interfaces import Interface
from typing import List, Tuple
import datetime

@dataclass
class Attribute(Interface):
    number: int
    flags: int
    raw_value: int
    threshold: int
    attr_type: str
    updated_freq: str
    value: int
    when_failed: str
    worst: int

@dataclass
class Smart(Interface):
    last_captured: str
    attributes: List[Attribute]
    firmware: str
    interface: str
    messages: List[str]
    smart_capable: bool
    smart_enabled: bool
    assessment: str
    test_capabilities: List[Tuple[str, bool]]
    #tests: Test #Test type not implimented yet. We must rely on our database to hold this info. pySMART is skimpy here.

    @staticmethod
    def FromSmartDev(device):
        formatted_attrs = []
        for a in device.attributes:
            if a != None:
                attr = Attribute(a.num, a.flags, a.raw, a.thresh, a.type, a.updated, a.value, a.when_failed, a.worst)
                formatted_attrs.append(attr)
        
        test_capabilities = []
        for k in device.test_capabilities:
            t = (str(k), device.test_capabilities[k])
            test_capabilities.append(t)

        return Smart(datetime.datetime.now(), formatted_attrs, device.firmware, device.interface, device.messages, device.smart_capable, device.smart_enabled, device.assessment, test_capabilities)

@dataclass
class TaskData(Interface):
    name: str
    progress_supported: bool
    progress: float
    string_rep: str
    return_code: int

    @staticmethod
    def FromTask(task):
        return TaskData(task.name, (task.Progress != -1), task.Progress, task.ProgressString, task.returncode)

@dataclass
class TaskQueueData(Interface):
    maxqueue: int
    paused: bool
    queue: List[TaskData]
    completed: List[str]
    current_task: TaskData

    @staticmethod
    def FromTaskQueue(taskqueue):
        taskdatas = []
        for t in taskqueue.Queue:
            task = t[1] #(preexec_cb, task, finish_cb)
            taskdatas.append(TaskData.FromTask(task))
        return TaskQueueData(taskqueue.maxqueue, taskqueue.Pause, taskdatas, taskqueue._task_name_history, (TaskData.FromTask(taskqueue.CurrentTask) if taskqueue.CurrentTask != None else None))

@dataclass
class HddData(Interface):
    serial: str
    model: str
    wwn: str
    capacity: float
    status: str
    assessment: str
    task_queue: TaskQueueData
    node: str
    port: str
    smart: Smart

    @staticmethod
    def FromHdd(hdd):
        return HddData(hdd.serial, hdd.model, hdd.wwn, hdd.capacity, str(hdd.status), str(hdd._smart.assessment), TaskQueueData.FromTaskQueue(hdd.TaskQueue), hdd.node, str(hdd.port), Smart.FromSmartDev(hdd._smart))




