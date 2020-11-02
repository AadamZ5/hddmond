import os
import enum
import subprocess
from subprocess import TimeoutExpired
import proc
from proc.tree import get_process_tree
import threading
import time
from pySMART import Device
from .image import DiskImage, Partition
from .notes import Notes
from .image import ImageManager
import datetime
from injectable import Autowired, autowired

class TaskResult(enum.Enum):
    FINISHED = 1,
    ERROR = 0,

class Task:

    display_name = "Task"

    @staticmethod
    def GetTaskParameterSchema(task):
        s: str = None

        if task.parameter_schema == None:
            return None

        if callable(task.parameter_schema):
            s = task.parameter_schema(task)
        else:
            s = str(task.parameter_schema)
        return s
            

    """_parameter_schema holds JSON Schema that defines the properties needed for a task to initialize. This can be callable, or just a static property."""
    parameter_schema = None

    def __init__(self, taskName, hdd):
        self.name = taskName
        self._progressString = self.name
        self._callback = None
        self.returncode = None
        self.notes = Notes()
        self.time_started = None
        self.time_ended = None

    @property
    def Progress(self):
        '''
        When overridden in a sub-class implimentation, provides the progress of a current task.
        -1 should symbolize no progress available to report.
        '''
        return -1

    @property
    def ProgressString(self):
        '''
        Returns the _progressString of a task
        '''
        return self._progressString

    @property
    def PID(self):
        '''
        When overridden in a sub-class implimentation, provides the PID of a task. 
        '''
        return 0

    @property
    def Finished(self):
        return True

    def start(self, progress_callback=None):
        '''
        Should be overridden in sub-classes to define the starting point of the operation.
        This is necessary for task-queues.
        '''
        pass

    def abort(self, wait=False):
        '''
        Should be overridden in a sub-class to provide the implimentation of aborting the task.
        If wait is true, the method should wait to return until the task is totally aborted.
        '''
        pass

class TaskQueue: #TODO: Use asyncio for polling and looping!
    '''
    A container that manages and handles a queue of multiple tasks.
    '''

    def __getstate__(self):
        state = self.__dict__.copy()
        state['_queue_thread'] = None #Can't pickle thread objects
        return state

    @property
    def Pause(self):
        return self._pause

    @Pause.setter
    def Pause(self, value: bool):
        if (self._pause == True and value == False):
            self._pause = value
            if(self.CurrentTask == None):
                self._create_queue_thread()
        else:
            self._pause = value
        self._taskchanged_cb(action='pausechange', data={'paused': self._pause})

    @property
    def Error(self):
        return self._error

    @Error.setter
    def Error(self, value: bool):
        self._error = value
        self._taskchanged_cb(action='errorchange', data={'error': self._error})

    @property
    def Full(self):
        return len(self.Queue) >= self.maxqueue

    def __init__(self, maxqueue=8, between_task_wait=1, continue_on_error=True, task_change_callback=None, queue_preset=None):
        self.maxqueue = maxqueue
        self.CurrentTask = None
        self._currentcb = None
        self.between_task_wait = between_task_wait
        self.continue_on_error = continue_on_error
        self._pause = False
        self._error = False
        self._queue_thread = None
        if(queue_preset == None):
            queue_preset = []
        else:
            if(len(queue_preset) > self.maxqueue):
                self.Queue = (queue_preset[0:self.maxqueue-1]).copy() #Only take the maximum allowed tasks from the preset.
        self.Queue = queue_preset #list of (preexec_cb, task, callback)
        self.history = []
        self._task_change_callback = task_change_callback

    def AddTask(self, task: Task, preexec_cb=None, index=None):
        '''
        Appends a task to the task queue, if it is not full.
        Returns a bool True if successfull.
        '''
        if not (self.Full):
            cb = task._callback 
            task._callback = self._taskcb #Hijack the callback so we can catch when the task is done.
            if(index != None):
                if(index >= self.maxqueue):
                    raise IndexError("Index out of range 0-" + str(self.maxqueue-1))
                else:
                    self.Queue.insert(index, (preexec_cb, task, cb))
            else:
                self.Queue.append((preexec_cb, task, cb))
            if(len(self.Queue) == 1 and self.CurrentTask == None): #We added the first task of this chain-reaction. Kick off the queue.
                self._create_queue_thread()
            self._taskchanged_cb(action='taskadded', data={'taskqueue': self})
            return True
        else:
            return False

    def _taskcb(self, returncode, *args, **kwargs):

        #   _taskcb(...) is called when a task finished, no matter the return code. This method is injected into the task's _callback attribute during the AddTask(...) method, and the original callback is stored.
        #   This method is responsible for continuing the chain of task running, if any tasks are left. Also, this method is responsible for pausing the queue if a task fails, and the continue_on_error attribute is False.

        self.history.insert(0, self.CurrentTask)#First element is always most recent task.

        if(self._currentcb != None and callable(self._currentcb)): #Call the original callback associated with the completed task
            self._currentcb(returncode)

        if(int(returncode) != 0):
            self.Error = True
            if(self.continue_on_error == False):
                self.Pause = True

        self.CurrentTask = None
        self._currentcb = None
        self._taskchanged_cb(action='taskfinished', data={'task': self.CurrentTask})
        if(self.Pause == True):
            return
        else:
            self._create_queue_thread()

    def _task_progresscb(self, progress=None, string=None):

        #   Helper method to notify the progress of the current task.

        self._taskchanged_cb(action='taskprogress', data={'taskqueue': self})

    def _create_queue_thread(self):

        #   Helper method to create the queue thread if none exists in the moment.

        self._queue_thread = threading.Thread(target=self._launch_new_task)
        self._queue_thread.start() #This thread should exit soon after the start() function of the task exits. This thread is just to offload the sleep between tasks, and detach from the last finished thread.

    def _launch_new_task(self): 

        #   This method holds the logic for determining to run another task.

        if(len(self.Queue) != 0) and self.Pause != True:
            time.sleep(self.between_task_wait)
            tup = self.Queue.pop(0)
            pcb = tup[0]
            t = tup[1]
            cb = tup[2]
            if(pcb != None and callable(pcb)):
                pcb()
            self.CurrentTask = t
            self._currentcb = cb
            self._taskchanged_cb(action='tasklistmod', data={'taskqueue': self})
            self.CurrentTask.start(progress_callback=self._task_progresscb)
        else:
            return

    def GetAllNotes(self):
        '''
        Returns a complete list of all task notes from the current session in no particular order.
        '''
        allNotes = {}
        if self.CurrentTask != None:
            allNotes.update(self.CurrentTask.notes.entries)
        for t in self.history:
            allNotes.update(t.notes.entries)
        for _tuple in self.Queue:
            t = _tuple[1]
            allNotes.update(t.notes.entries)

        return allNotes
        
    def PushUp(self, current_index):
        '''
        Pushes a task up in the queue
        '''
        lastpause = self.Pause
        self.Pause = True
        last_index = len(self.Queue)-1 #Don't shove above our max index
        if(current_index >= last_index):
            return
        try:
            t = self.Queue[current_index]
            del self.Queue[current_index]
        except IndexError:
            return

        self.Queue.insert(current_index+1, t)
        self.Pause = lastpause
        self._taskchanged_cb(action='tasklistmod', data={'taskqueue': self})

    def PushDown(self, current_index):
        '''
        Pushes a task down in the queue
        '''
        lastpause = self.Pause
        self.Pause = True
        if(current_index <= 0): #Dont shove below 0 index
            return
        try:
            t = self.Queue[current_index]
            del self.Queue[current_index]
        except IndexError:
            return

        self.Queue.insert(current_index-1, t)
        self.Pause = lastpause
        self._taskchanged_cb(action='tasklistmod', data={'taskqueue': self})

    def SetIndex(self, current_index, new_index):
        '''
        Sets the index of a task in the queue within the bounds of the current list size.
        '''
        lastpause = self.Pause
        self.Pause = True
        if(new_index < 0): #Dont shove below 0 index
            return
        last_index = len(self.Queue)-1 
        if(new_index > last_index): #Don't shove above our max index
            return
        t = self.Queue[current_index]
        del self.Queue[current_index]
        self.Queue.insert(new_index, t)
        self.Pause = lastpause
        self._taskchanged_cb(action='tasklistmod', data={'taskqueue': self})

    def RemoveTask(self, index):
        '''
        Removes a task at index.
        '''
        lastpause = self.Pause
        self.Pause = True
        if index < 0 or index > self.maxqueue-1 or index > len(self.Queue)-1:
            return False
        del self.Queue[index]
        self.Pause = lastpause
        self._taskchanged_cb(action='tasklistmod', data={'taskqueue': self})

    def AbortCurrentTask(self, pause=True):
        '''
        Aborts the current task.
        '''
        if(self.CurrentTask != None):
            self.Pause = pause
            t = self.CurrentTask
            self.CurrentTask.abort()
            self._taskchanged_cb(action='taskabort', data={'task': t})
        
    def _taskchanged_cb(self, *args, **kw):

        #   Helper method to notify when some aspect of the task queue is changed.

        if self._task_change_callback != None and callable(self._task_change_callback):
            self._task_change_callback(*args, **kw)

class ExternalTask(Task):

    display_name = "External Task"

    parameter_schema = None

    @property
    def Finished(self):
        return self._finished

    @property
    def PID(self):
        return self._PID

    def __getstate__(self):
        state = self.__dict__.copy()
        state['_pollingThread'] = None
        return state

    def __setstate__(self, state):
        self.__dict__.update(state)

    def __init__(self, hdd,  pid, processExitCallback=None, pollingInterval=5, start=False):
        self._procview = proc.core.Process.from_pid(pid)
        self._PID = self._procview.pid
        self._finished = False
        self._poll = True
        self._pollingInterval = pollingInterval
        self._pollingThread = threading.Thread(target=self._pollProcess, name=str(self.PID) + "_pollingThread")
        super(ExternalTask, self).__init__("External", hdd)
        self.returncode = 0
        self._callback = processExitCallback
        self._progressString = "PID " + str(self.PID)
        self.notes.add("An external task was detected running on this storage device.\nCommand: " + str(" ".join(map(str, self._procview.cmdline))), note_taker="hddmond")
        if(start):
            self.start()
        
    def start(self, progress_callback=None):
        if(self._pollingThread.is_alive()):
            return False
        else:
            self.time_started = datetime.datetime.now(datetime.timezone.utc)
            self._pollingThread.start()
            return True

    def _pollProcess(self):
        while self._poll == True and self._finished == False:
            if(self._procview.is_alive == False): # is_alive is a generated bool, evaluating every time we check it. This should be a real-time status. 
                self._finished = True
            else:
                time.sleep(self._pollingInterval)

        self.notes.add("The process has exited.", note_taker="hddmond")
        self.time_ended = datetime.datetime.now(datetime.timezone.utc)
        if(self._callback != None) and (self._poll == True):
            self._callback(0) #They might be expecting a return code. We can't obtain it, so assume 0. 
    
    def abort(self, wait=False, true_abort=False):
        if(true_abort == True): #Don't kill the process unless explicitly stated.
            if(self._procview.is_alive == True):
                self.notes.add("A termination signal was sent to the process.", note_taker="hddmond")
                self._procview.terminate()
        else:
            self.detach()
        
        if wait == True:
            print("\tWaiting for {0} to stop...".format(self._pollingThread.name))
            try:
                self._pollingThread.join()
            except RuntimeError:
                pass

    def detach(self):
        '''
        Should be used only when quitting the hddmon-daemon program
        '''
        self._poll = False
        try:
            self._pollingThread.join()
        except RuntimeError:
            pass
        self.notes.add("The process was detatched from the hddmond monitor.", note_taker="hddmond")
    
class EraseTask(Task):

    display_name = "Erase"

    parameter_schema = None

    def __getstate__(self):
        state = self.__dict__.copy()
        state['_pollingThread'] = None
        state['_subproc'] = None
        return state

    def __setstate__(self, state):
        self.__dict__.update(state)

    def __init__(self, hdd, pollingInterval = 5, callback=None):
        self._subproc = None
        self._procview = None
        self._PID = None
        self._diskusage = None
        self._cap_in_bytes = None
        self._progress = 0
        self.node = hdd.node
        self.Capacity = int(hdd.capacity if hdd.capacity != None else -1)
        self._monitor = True
        self._started = False
        self._returncode = None
        self._pollingInterval = pollingInterval
        self._pollingThread = threading.Thread(target=self._monitorProgress, name=str(self.node) + "_eraseTask")
        self._subproc = None
        self._PID = None
        self._procview = None
        super(EraseTask, self).__init__("Erase", hdd)
        self._callback = callback
        self._progress_cb = None
        

    @property
    def Capacity(self):
        '''
        Get the capacity in GIGAbytes
        '''
        return float(self._cap_in_bytes / 10000000) #1*10^7

    @Capacity.setter
    def Capacity(self, value):
        '''
        Set the capacity in GIGAbytes
        '''
        self._cap_in_bytes = float(float(value) * 10000000.0)

    @property
    def PID(self):
        return self._PID

    @property
    def Progress(self):
        return self._progress

    @property
    def Finished(self):
        return self._returncode != None
        
    def start(self, progress_callback=None):
        self.time_started = datetime.datetime.now(datetime.timezone.utc)
        self._progress_cb = progress_callback
        self._subproc = subprocess.Popen(['scrub', '-f', '-p', 'fillff', self.node], stdout=subprocess.PIPE, stderr=subprocess.PIPE, universal_newlines=True)
        self._PID = self._subproc.pid
        self._procview = proc.core.Process.from_pid(self._PID)
        self._pollingThread.start()
        self._progressString = "Erasing" + (" " + str(self.Progress) + "%" if self.Capacity != 0 else '') 
        self.notes.add("Erasing was started on this storage device.", note_taker="hddmond")


    def abort(self, wait=False):
        if(self._subproc):
            if(self.Finished == False):
                self.notes.add("Erase task aborted at " + str(self.Progress) + "%.", note_taker="hddmond")
            self._subproc.terminate()
        if wait == True:
            print("\tWaiting for {0} to stop...".format(self._pollingThread.name))
            try:
                self._pollingThread.join()
            except RuntimeError:
                pass


    def _monitorProgress(self):
        if(self._progress_cb != None) and callable(self._progress_cb):
            self._progress_cb(self.Progress, self._progressString)
        lastprogress = self._progress
        while self._monitor and (self._returncode == None):
            
            self._returncode = self._subproc.poll()
            if(self._returncode == None):
                io = self._procview.io
                if(self.Capacity > 0):
                    self._progress = int(io['write_bytes'] / self._cap_in_bytes)
                    self._progressString = "Erasing " + str(self.Progress) + "%" 
                else:
                    self._progress = -1
                    self._progressString = "Erasing"
                time.sleep(self._pollingInterval)

                if(self._progress != lastprogress):
                    if(self._progress_cb != None) and callable(self._progress_cb):
                        self._progress_cb(self.Progress, self._progressString)
                    lastprogress = self._progress
        self.returncode = self._returncode
        self.time_started = datetime.datetime.now(datetime.timezone.utc)
        if(self._returncode == 0):
            self.notes.add("Full erase performed on storage device. Wrote 0xFF to all bits.", note_taker="hddmond")
        else:
            self.notes.add("Erase task failed", note_taker="hddmond")
        if(self._callback != None):
            self._callback(self._returncode)

class ImageTask(Task):

    display_name = "Image"

    @staticmethod
    @autowired
    def parameter_schema(task, i_s: Autowired(ImageManager), **kw):

        images_comma_separated = ', '.join('"{0}"'.format(str(image.name)) for image in i_s.discovered_images)
    
        schema = """{{
    "default": {{
        "image_name": null
    }},
    "description": "Parameters that are needed for the Image task",
    "examples": [
        {{
            "image_name": "hp_g1_26k"
        }}
    ],
    "required": [
        "image_name"
    ],
    "title": "Image task parameters",
    "properties": {{
        "image_name": {{
            "default": "",
            "description": "This is the name of the data image that should be applied to the HDD(s) in question.",
            "examples": [
                "hp_g1_26k"
            ],
            "title": "Image name",
            "enum": [
                {0}
            ],
            "type": "string"
        }}
    }},
    "additionalProperties": true
}}""".format(images_comma_separated)
        return schema
        

    def __getstate__(self):
        state = self.__dict__.copy()
        state['_pollingThread'] = None
        state['_subproc'] = None
        return state

    def __setstate__(self, state):
        self.__dict__.update(state)

    @property
    def PID(self):
        return self._PID

    @property
    def Finished(self):
        return self._returncode != None

    @autowired
    def __init__(self, hdd, i_s: Autowired(ImageManager), **kw):

        image_name = kw.get("image_name", None)
        self._image = None
        for dimage in i_s.discovered_images:
            if dimage.name == image_name:
                self._image = dimage
                break;
        
        if self._image == None:
            raise Exception("No imaged matched {0}!".format(image_name))

        #self._partitions = image.partitions.copy()
        self._diskname = hdd.node
        self._subproc = None
        self._PID = None
        self._returncode = None
        self._partclone_procview = None
        self._md5sum_procview = None
        self._proctree = None
        self._cloning = False
        self._checking = False
        self._poll = True
        self._pollingInterval = kw.get("pollingInterval", 5)
        self._pollingThread = threading.Thread(target=self._monitor, name=str(self._diskname) + "_cloneTask")
        super(ImageTask, self).__init__("Image " + self._image.name, hdd)
        self._callback = kw.get("callback", None)
        self._progress_cb = None
        
    def start(self, progress_callback=None):
        self.time_started = datetime.datetime.now(datetime.timezone.utc)
        self._subproc = subprocess.Popen(['/usr/sbin/ocs-sr', '-e1', 'auto', '-e2', '-nogui', '-batch', '-r', '-irhr', '-ius', '-icds', '-j2', '-k1', '-cmf', '-scr', '-p', 'true', 'restoredisk', self._image.name, self._diskname], stdin=subprocess.PIPE, stdout=subprocess.PIPE, stderr=subprocess.PIPE, universal_newlines=True)        
        self._PID = self._subproc.pid
        self._proctree = get_process_tree().find(pid=self.PID, recursive=True)
        self._progressString = "Loading " + self._image.name
        self._pollingThread.start()
        self._progress_cb = progress_callback
        self.notes.add("Imaging task started on this storage device. " + str(len(self._image.partitions)) + " to clone.", note_taker="hddmond")

    def _call_progress_cb(self):
        if(self._progress_cb != None) and callable(self._progress_cb):
            self._progress_cb(None, self._progressString)

    def _monitor(self):
        for i in range(len(self._image.partitions)): #The partclone.ntfs process will spawn once for each partition. Watch for partclone.ntfs as many times as there are partitions to clone.

            while self._poll == True and self._partclone_procview == None and self._md5sum_procview == None: #Watch for the creation of the partclone.ntfs process
                time.sleep(self._pollingInterval)
                self._check_subproc()
                
                self._proctree.update_descendants()
                p = self._proctree.find(exe_name='partclone.ntfs', recursive=True)
                m = self._proctree.find(exe_name='md5sum', recursive=True)
                if p != None:
                    self._partclone_procview = p
                    self._progressString = "Cloning " + self._image.name + ":" + str(i+1) + "/" + str(len(self._image.partitions))
                    self.notes.add("Cloning partition " + str(i+1) + "/" + str(len(self._image.partitions)) + " of " + self._image.name, note_taker="hddmond")
                    self._call_progress_cb()
                    self._cloning = True
                if m != None:
                    self._md5sum_procview = p
                    self._progressString = "Checking " + self._image.name
                    self.notes.add("Checking " + self._image.name + ".", note_taker="hddmond")
                    self._call_progress_cb()
                    self._checking = True

            while self._cloning == True and self._poll == True and self._md5sum_procview == None: #Wait for the end of the partclone.ntfs process, or skip these loops if we see the md5sum process. Possibility to incorrectly count partitions
                time.sleep(self._pollingInterval/4) #Increased pollrate to catch the death of the process.
                self._check_subproc()
                if(self._partclone_procview.is_alive == False):
                    self._partclone_procview = None
                    self._cloning = False
                    

        while self._poll == True and self._md5sum_procview == None: #Watch for the creation of the md5sum process
            time.sleep(self._pollingInterval)
            self._check_subproc()
            self._proctree.update_descendants()
            p = self._proctree.find(exe_name='md5sum', recursive=True)
            if p != None:
                self._md5sum_procview = p
                self._progressString = "Checking " + self._image.name
                self.notes.add("Checking " + self._image.name + ".", note_taker="hddmond")
                self._call_progress_cb()
                self._checking = True

        while self._checking == True and self._poll == True: #Wait for the end of the md5sum process
            time.sleep(self._pollingInterval/4)
            self._check_subproc()
            if(self._md5sum_procview.is_alive == False):
                self._checking = False

        while self._poll:
            time.sleep(self._pollingInterval)
            self._check_subproc()

        self.returncode = self._returncode
        self.time_started = datetime.datetime.now(datetime.timezone.utc)
        if(self._returncode == 0):
            self.notes.add("Finished imaging " + self._image.name + ".", note_taker="hddmond")
        else:
            self.notes.add("Failed imaging " + self._image.name + ".", note_taker="hddmond")
            self.notes.add("stderr:\n" + str(self.err if self.err else "Unkown error"), note_taker="hddmond")

        if(self._callback != None and callable(self._callback)):
            self._callback(self._returncode)

    def _check_subproc(self):
        try:
            self._subproc.communicate(timeout=1)
        except TimeoutExpired:
            pass
        self._returncode = self._subproc.poll()
        if(self._returncode != None): #Return code should be None until the process has exited.
            try:
                self.err = self._subproc.stderr.read()
                self.out = self._subproc.stdout.read()
            except ValueError as e:
                self.err = None
                self.out = None
                pass
            self._poll = False  
            
    def abort(self, wait=False):
        
        self._poll = False
        if(self._subproc):
            self._subproc.terminate()
        self.notes.add("Image task aborted.", note_taker="hddmond")
        # if(self._callback != None and callable(self._callback)):
        #     self._callback(self._returncode)
        if wait == True:
            print("\tWaiting for {0} to stop...".format(self._pollingThread.name))
            try:
                self._pollingThread.join()
            except RuntimeError:
                pass
        
