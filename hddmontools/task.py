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


class TaskResult(enum.Enum):
    FINISHED = 1,
    ERROR = 0,

class Task:
    def __init__(self, taskName):
        self.name = taskName
        self._progressString = self.name
        self._callback = None

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

    def start(self):
        '''
        Should be overridden in sub-classes to define the starting point of the operation.
        This is necessary for task-queues.
        '''
        pass

    def abort(self):
        '''
        Should be overridden in a sub-class to provide the implimentation of aborting the task.
        '''
        pass

class TaskQueue:
    '''
    A container that manages and handles multiple tasks.
    '''

    def __getstate__(self):
        state = self.__dict__.copy()
        state['_queue_thread'] = None
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

    @property
    def Full(self):
        return len(self.Queue) == self.maxqueue

    def __init__(self, maxqueue=4, between_task_wait=1, continue_on_error=True):
        self.Queue = [] #list of (preexec_cb, task, callback)
        self.CurrentTask = None
        self._currentcb = None
        self.maxqueue = maxqueue
        self.between_task_wait = between_task_wait
        self.continue_on_error = continue_on_error
        self._pause = False
        self._queue_thread = None
        self._task_name_history = []

    def AddTask(self, task: Task, preexec_cb=None, index=None):
        if not (len(self.Queue) >= self.maxqueue):
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
            return True
        else:
            return False

    def _taskcb(self, returncode, *args, **kwargs):

        self._task_name_history.append(self.CurrentTask.name + ": " + str(returncode))

        if(self._currentcb != None and callable(self._currentcb)): #Call the original callback associated with the completed task
            self._currentcb(returncode)

        if(int(returncode) != 0 and self.continue_on_error == False):
            self.Pause = True

        self.CurrentTask = None
        self._currentcb = None
        if(self.Pause == True):
            return
        else:
            self._create_queue_thread()

    def _create_queue_thread(self):
        self._queue_thread = threading.Thread(target=self._launch_new_task)
        self._queue_thread.start() #This thread should exit soon after the start() function of the task exits. This thread is just to offload the sleep between tasks, and detach from the last finished thread.

    def _launch_new_task(self): 
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
            self.CurrentTask.start()
        else:
            return

    def PushUp(self, index):
        lastpause = self.Pause
        self.Pause = True
        last_index = self.maxqueue-1 #Don't shove above our max index
        if(index >= last_index):
            return
        t = self.Queue[index]
        del self.Queue[index]
        self.Queue.insert(index+1, t)
        self.Pause = lastpause

    def PushDown(self, index):
        lastpause = self.Pause
        self.Pause = True
        if(index <= 0): #Dont shove below 0 index
            return
        t = self.Queue[index]
        del self.Queue[index]
        self.Queue.insert(index-1, t)
        self.Pause = lastpause

    def RemoveTask(self, index):
        lastpause = self.Pause
        self.Pause = True
        if index < 0 or index > self.maxqueue-1:
            return
        del self.Queue[index]
        self.Pause = lastpause

    def AbortCurrentTask(self, pause=True):
        if(self.CurrentTask != None):
            self.Pause = pause
            #self._task_name_history.append(self.CurrentTask.name)
            self.CurrentTask.abort()
        

class ExternalTask(Task):

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

    def __init__(self, pid, processExitCallback=None, pollingInterval=5, start=False):
        self._procview = proc.core.Process.from_pid(pid)
        self._PID = self._procview.pid
        self._finished = False
        self._poll = True
        self._pollingInterval = pollingInterval
        self._pollingThread = threading.Thread(target=self._pollProcess, name=str(self.PID) + "_pollingThread")
        super(ExternalTask, self).__init__("External")
        self._callback = processExitCallback
        self._progressString = "PID " + str(self.PID)
        if(start):
            self._pollingThread.start()
        
    def start(self):
        if(self._pollingThread.isAlive):
            return False
        else:
            self._pollingThread.start()
            return True

    def _pollProcess(self):
        while self._poll == True and self._finished == False:
            if(self._procview.is_alive == False):
                self._finished = True
            time.sleep(self._pollingInterval)

        if(self._callback != None) and (self._poll == True):
            self._callback(0) #They might be expecting a return code. We can't obtain it, so assume 0.
    
    def abort(self):
        if(self._procview.is_alive == True):
            self._procview.terminate()

    def detach(self):
        '''
        Should be used only when quitting the hddmon-daemon program
        '''
        self._poll = False
        self._pollingThread.join()
    

class EraseTask(Task):

    def __getstate__(self):
        state = self.__dict__.copy()
        state['_pollingThread'] = None
        state['_subproc'] = None
        return state

    def __setstate__(self, state):
        self.__dict__.update(state)

    def __init__(self, node, capacity=0, pollingInterval = 5, callback=None):
        self._subproc = None
        self._procview = None
        self._PID = None
        self._diskusage = None
        self._cap_in_bytes = None
        self._progress = 0
        self.node = node
        self.Capacity = int(capacity)
        self._monitor = True
        self._started = False
        self._returncode = None
        self._pollingInterval = pollingInterval
        self._pollingThread = threading.Thread(target=self._monitorProgress, name=str(node) + "_eraseTask")
        self._subproc = None
        self._PID = None
        self._procview = None
        super(EraseTask, self).__init__("Erase")
        self._callback = callback
        

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
        
    def start(self):
        self._subproc = subprocess.Popen(['scrub', '-f', '-p', 'fillff', self.node], stdout=subprocess.PIPE, stderr=subprocess.PIPE, universal_newlines=True)
        self._PID = self._subproc.pid
        self._procview = proc.core.Process.from_pid(self._PID)
        self._pollingThread.start()
        self._progressString = "Erasing" + (" " + str(self.Progress) + "%" if self.Capacity != 0 else '') 


    def abort(self):
        if(self._subproc):
            self._subproc.terminate()

    def _monitorProgress(self):
        while self._monitor and (self._returncode == None):
            self._returncode = self._subproc.poll()
            if(self._returncode == None):
                io = self._procview.io
                self._progress = int(io['write_bytes'] / self._cap_in_bytes)
                self._progressString = "Erasing " + str(self.Progress) + "%" 
                time.sleep(self._pollingInterval)
        
        if(self._callback != None):
            self._callback(self._returncode)

class ImageTask(Task):

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

    def __init__(self, image: DiskImage, diskname, callback=None, pollingInterval=5):
        self._image = image
        #self._partitions = image.partitions.copy()
        self._diskname = diskname
        self._subproc = None
        self._PID = None
        self._returncode = None
        self._partclone_procview = None
        self._md5sum_procview = None
        self._proctree = None
        self._cloning = False
        self._checking = False
        self._poll = True
        self._pollingInterval = pollingInterval
        self._pollingThread = threading.Thread(target=self._monitor, name=str(diskname) + "_cloneTask")
        super(ImageTask, self).__init__("Image")
        self._callback = callback
        
    def start(self):
        self._subproc = subprocess.Popen(['/usr/sbin/ocs-sr', '-e1', 'auto', '-e2', '-nogui', '-batch', '-r', '-irhr', '-ius', '-icds', '-j2', '-k1', '-cmf', '-scr', '-p', 'true', 'restoredisk', self._image.name, self._diskname], stdin=subprocess.PIPE, stdout=subprocess.PIPE, stderr=subprocess.PIPE, universal_newlines=True)        
        self._PID = self._subproc.pid
        self._proctree = get_process_tree().find(pid=self.PID, recursive=True)
        self._progressString = "Loading " + self._image.name
        self._pollingThread.start()

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
                    self._cloning = True
                if m != None:
                    self._md5sum_procview = p
                    self._progressString = "Checking " + self._image.name
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
                self._checking = True

        while self._checking == True and self._poll == True: #Wait for the end of the md5sum process
            time.sleep(self._pollingInterval/4)
            self._check_subproc()
            if(self._md5sum_procview.is_alive == False):
                self._checking = False

        while self._poll:
            time.sleep(self._pollingInterval)
            self._check_subproc()

        if(self._callback != None and callable(self._callback)):
            self._callback(self._returncode)

    def _check_subproc(self):
        try:
            self._subproc.communicate(timeout=1)
        except TimeoutExpired as e:
            pass
        self._returncode = self._subproc.poll()
        if(self._returncode != None):
            try:
                self.err = self._subproc.stderr.read()
                self.out = self._subproc.stdout.read()
            except ValueError as e:
                pass
            self._poll = False  
            
    def abort(self):
        self._poll = False
        if(self._subproc):
            self._subproc.terminate()
        else:
            if(self._callback != None and callable(self._callback)):
                self._callback(self._returncode)
        
