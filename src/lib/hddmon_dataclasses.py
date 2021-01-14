import datetime
import strawberry

from dataclasses import dataclass
from py_ts_interfaces import Interface
from typing import *

from lib.note_data import NoteData
from lib.tasklib.task_entry import TaskEntry
from lib.hddlib.smart_data import SmartCapture
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
class TaskQueueData(Interface):
    maxqueue: int
    paused: bool
    queue: List[Any]
    completed: List[Any]
    current_task: Any

    @staticmethod
    def FromTaskQueue(taskqueue):
        taskdatas = []
        for t in taskqueue.Queue: #t is a tuple of (preexec_cb, task, finish_cb)
            task = t[1]
            taskdatas.append(TaskEntry.FromTask(task))
        historytaskdatas = []
        for t in taskqueue.history:
            historytaskdatas.append(TaskEntry.FromTask(t))
        return TaskQueueData(taskqueue.maxqueue, taskqueue.Pause, taskdatas, historytaskdatas, (TaskEntry.FromTask(taskqueue.CurrentTask) if taskqueue.CurrentTask != None else None))

@dataclass
class HddData:
    serial: str
    model: str
    wwn: str
    capacity: float
    status: str
    assessment: str
    task_queue: TaskQueueData
    node: str
    port: Optional[str]
    smart: SmartCapture
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




