import enum
import subprocess
import proc
from proc.tree import get_process_tree
import threading
import time
from .image import DiskImage, Partition


class TaskResult(enum.Enum):
    FINISHED = 1,
    ERROR = 0,

class Task:
    def __init__(self, taskName):
        self.name = taskName
        self._progressString = self.name

    @property
    def Progress(self):
        '''
        When overridden in a sub-class implimentation, provides the progress of a current task.
        '''
        return 0

    @property
    def ProgressString(self):
        return self._progressString

    @property
    def PID(self):
        '''
        When overridden in a sub-class implimentation, provides the PID of a task. 
        -1 should symbolize no progress available to report.
        '''
        return -1

    @property
    def Finished(self):
        return True

    def abort(self):
        pass

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

    def __init__(self, pid, processExitCallback=None, pollingInterval=5):
        self._procview = proc.core.Process.from_pid(pid)
        self._PID = self._procview.pid
        self._callback = processExitCallback
        self._finished = False
        self._poll = True
        self._pollingInterval = pollingInterval
        self._pollingThread = threading.Thread(target=self._pollProcess)
        super(ExternalTask, self).__init__("External")
        self._progressString = "PID " + str(self.PID)
        self._pollingThread.start()

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

    def __init__(self, node, capacity, pollingInterval = 5, callback=None):
        self._subproc = None
        self._procview = None
        self._PID = None
        self._diskusage = None
        self._cap_in_bytes = None
        self._progress = 0
        self._callback = callback
        self.node = node
        self.Capacity = int(capacity)
        self._monitor = True
        self._started = False
        self._returncode = None
        self._pollingInterval = pollingInterval
        self._pollingThread = threading.Thread(target=self._monitorProgress)
        self._subproc = subprocess.Popen(['scrub', '-f', '-p', 'fillff', self.node], stdout=subprocess.PIPE, stderr=subprocess.PIPE, universal_newlines=True)
        self._PID = self._subproc.pid
        self._procview = proc.core.Process.from_pid(self._PID)
        super(EraseTask, self).__init__("Erase")
        self._progressString = "Erasing"
        self._pollingThread.start()

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
        

    def abort(self):
        self._monitor = False
        if(self._subproc):
            self._subproc.terminate()

    def _monitorProgress(self):
        while self._monitor and (self._returncode == None):
            self._returncode = self._subproc.poll()
            if(self._returncode == None):
                io = self._procview.io
                self._progress = int(io['write_bytes'] / self._cap_in_bytes)
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

    def __init__(self, image: DiskImage, diskname, callback=None, pollingInterval=5):
        self._subproc = subprocess.Popen(['/usr/sbin/ocs-sr', '-e1 auto', '-e2', '-nogui', '-batch', '-r', '-irhr', '-ius', '-icds', '-j2', '-cmf', '-k1', '-scr', '-p true', 'restoredisk', image.name, diskname], stdin=subprocess.PIPE, stdout=subprocess.PIPE, stderr=subprocess.PIPE, universal_newlines=True)
        self._PID = self._subproc.pid
        self._returncode = None
        self._partclone_procview = None
        self._md5sum_procview = None
        self._proctree = get_process_tree().find(pid=self._PID)

        self._callback = callback

        self._poll = True
        self._pollingInterval = pollingInterval
        self._pollingThread = threading.Thread(target=self._monitor)
        super(ImageTask, self).__init__("Image")
        self._pollingThread.start()

        self._stage = 'cloning'
            
        
    def _monitor(self):
        while self._poll == True and self._returncode == None:
            # for p in self._proctree.descendants:
            #     if(self._stage == 'cloning') and self._partclone_procview != None:
            #         if 'partclone.ntfs' in p.cmdline:
            #             self._partclone_procview = p
            #     elif(self._stage == 'checking') and self._md5sum_procview != None:
            #         if 'md5sum' in p.cmdline:
            #             self._md5sum_procview = p
            self._returncode = self._subproc.poll()
            time.sleep(self._pollingInterval)
        
        if(self._callback != None):
            self._callback(self._returncode)
            
            
                
            

        
            


