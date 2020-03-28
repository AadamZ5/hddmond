from dataclasses import dataclass
from py_ts_interfaces import Interface
from typing import List, Tuple
import datetime

@dataclass
class Md5SumData(Interface):
    root_path: str
    md5_sum: str

@dataclass
class PartitionData(Interface):
    index: int
    start_sector: int
    end_sector: int
    filesystem: str
    part_type: str
    flags: List[str]
    #md5_sums: List[Md5SumData]

    @staticmethod
    def FromPartition(p):
        # sums = []
        # for s in p.md5sums.keys():
        #     md5sum = Md5SumData(s, p.md5sums[s])
        #     sums.append(md5sum)
        
        return PartitionData(p.index, p.startSector, p.endSector, p.filesystem, p.parttype, p.flags)

@dataclass
class ImageData(Interface):
    name: str
    part_table: str
    partitions: List[PartitionData]
    path: str

    @staticmethod
    def FromDiskImage(d):
        parts = []
        for p in d.partitions:
            parts.append(PartitionData.FromPartition(p))
        return ImageData(d.name, d.parttable, parts, d.path)

@dataclass
class NoteData(Interface):
    tags: List[str]
    note: str
    note_taker: str
    timestamp: str

    @staticmethod
    def FromNote(note):
        return NoteData(note.tags, note.note, note.note_taker, str(note.timestamp.isoformat()))

@dataclass
class AttributeData(Interface):
    index: int
    name: str
    flags: int
    raw_value: int
    threshold: int
    attr_type: str
    updated_freq: str
    value: int
    when_failed: str
    worst: int

@dataclass
class SmartData(Interface):
    last_captured: str
    attributes: List[AttributeData]
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
                attr = AttributeData(a.num, a.name, a.flags, a.raw, a.thresh, a.type, a.updated, a.value, a.when_failed, a.worst)
                formatted_attrs.append(attr)
        
        test_capabilities = []
        for k in device.test_capabilities:
            t = (str(k), device.test_capabilities[k])
            test_capabilities.append(t)

        return SmartData(datetime.datetime.utcnow().isoformat(), formatted_attrs, device.firmware, device.interface, device.messages, device.smart_capable, device.smart_enabled, device.assessment, test_capabilities)

@dataclass
class TaskData(Interface):
    name: str
    progress_supported: bool
    progress: float
    string_rep: str
    return_code: int
    notes: List[NoteData]
    time_started: str
    time_ended: str

    @staticmethod
    def FromTask(task):
        notes = []
        for n in task.notes.entries:
            notes.append(NoteData.FromNote(n))
        return TaskData(task.name, (task.Progress != -1), task.Progress, task.ProgressString, task.returncode, notes, (task.time_started.isoformat() if task.time_started != None else None), (task.time_ended.isoformat() if task.time_ended != None else None))

@dataclass
class TaskQueueData(Interface):
    maxqueue: int
    paused: bool
    queue: List[TaskData]
    completed: List[TaskData]
    current_task: TaskData

    @staticmethod
    def FromTaskQueue(taskqueue):
        taskdatas = []
        for t in taskqueue.Queue:
            task = t[1] #(preexec_cb, task, finish_cb)
            taskdatas.append(TaskData.FromTask(task))
        historytaskdatas = []
        for t in taskqueue.history:
            historytaskdatas.append(TaskData.FromTask(t))
        return TaskQueueData(taskqueue.maxqueue, taskqueue.Pause, taskdatas, historytaskdatas, (TaskData.FromTask(taskqueue.CurrentTask) if taskqueue.CurrentTask != None else None))

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
    smart: SmartData
    notes: List[NoteData]
    seen: int

    @staticmethod
    def FromHdd(hdd):
        notes = []
        for n in hdd.notes.entries:
            notes.append(NoteData.FromNote(n))
        return HddData(hdd.serial, hdd.model, hdd.wwn, hdd.capacity, str(hdd.status), str(hdd._smart.assessment), TaskQueueData.FromTaskQueue(hdd.TaskQueue), hdd.node, str(hdd.port), SmartData.FromSmartDev(hdd._smart), notes, hdd.seen)




