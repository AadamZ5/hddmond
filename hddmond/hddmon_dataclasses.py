from dataclasses import dataclass
from py_ts_interfaces import Interface
from typing import List, Tuple

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

    @staticmethod
    def FromHdd(hdd):
        return HddData(hdd.serial, hdd.model, hdd.wwn, hdd.capacity, str(hdd.status), str(hdd._smart.assessment), TaskQueueData.FromTaskQueue(hdd.TaskQueue), hdd.node, str(hdd.port))




