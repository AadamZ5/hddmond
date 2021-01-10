from dataclasses import dataclass
from py_ts_interfaces import Interface
from typing import *
import datetime
#
#   The purpose of this file is to hold data classes that correspond to typescript interface definitions on the web app thing.
#   Basically this is all a translation layer to make sure data is neatly and properly laid out for Angular.
#   All of these classes are designed to be easily translatable into JSON and also typescript interfaces.
#   See: https://github.com/cs-cordero/py-ts-interfaces
#
#   While this might seem redundant, it actually allows for greater flexibility on the backend and helps us weed out which data
#   to send to the front end. Our front end will not need hdd.syspath or hdd.pciaddress. Or in the case of the TaskQueue class,
#   Our front end will not need the TaskQueue._queue_thread or TaskQueue._task_change_callback variables. Trying to build in
#   serialization with pure back-end classes would be tedious, tiresome, and hinder flexibility in my opinion. Thats why I opted
#   to go with this translation layer instead.
#
#   Side note: The classes marked with @dataclass have their constructors auto-generated. The constructors just accept the
#   variables defined below the class in order of definition.
#
#   Side note: The inheritance from the Interface class allows py-ts-interfaces to automagically convert these to typescript interfaces.
#

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
        # sums = []     #This takes too long and is too much data to send! This will kill your websocket.
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
    #tests: Test #Test type not implimented yet. We must rely on our database to hold this info. S.M.A.R.T. is skimpy here.

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

        return SmartData(datetime.datetime.now(datetime.timezone.utc).isoformat(), formatted_attrs, device.firmware, device.interface, device.messages, device.smart_capable, device.smart_enabled, device.assessment, test_capabilities)

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
        for t in taskqueue.Queue: #t is a tuple of (preexec_cb, task, finish_cb)
            task = t[1]
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
    port: Optional[str]
    smart: SmartData
    notes: List[NoteData]
    seen: int
    locality: str
    supported_tasks: Dict[str, str]

    @staticmethod
    def FromHdd(hdd): #HddInterface
        notes = []
        # for n in hdd.notes.entries:
        #     #notes.append(NoteData.FromNote(n))
        #     pass
        try:
            return HddData(hdd.serial, hdd.model, hdd.wwn, hdd.capacity, None, str(hdd.smart_data.assessment), TaskQueueData.FromTaskQueue(hdd.TaskQueue), hdd.node, str(hdd.port), hdd.smart_data, notes, hdd.seen, hdd.locality, hdd.get_available_tasks())
        except Exception as e:
            ("Error while parsing HDD {0} {1}".format(hdd.serial, hdd.node))
            print(str(e))
            return None




