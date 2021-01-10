import proc
import datetime
import asyncio
import subprocess

from lib.tasklib.task import Task
from lib.tasklib.task_service import TaskService

class EraseTask(Task):

    display_name = "Scrub Erase"

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
        self._pollingTask = None #threading.Thread(target=self._monitorProgress, name=str(self.node) + "_eraseTask")
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
        self._subproc = asyncio.create_subprocess_exec('scrub', '-f', '-p', 'fillff', self.node, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        self._PID = self._subproc.pid
        self._procview = proc.core.Process.from_pid(self._PID)
        self._pollingTask = asyncio.get_event_loop().create_task(self._monitorProgress(), name="erase_task_poll")
        self._progressString = "Erasing" + (" " + str(self.Progress) + "%" if self.Capacity != 0 else '') 
        self.notes.add("Erasing was started on this storage device.", note_taker="hddmond")

    async def abort(self, wait=False):
        if(self._subproc):
            if(self.Finished == False):
                self.notes.add("Erase task aborted at " + str(self.Progress) + "%.", note_taker="hddmond")
            self._subproc.terminate()
        if wait == True:
            print("\tWaiting for {0} to stop...".format(self._pollingTask.name))
            while not self._pollingTask.done():
                await asyncio.sleep(0)


    async def _monitorProgress(self):

        if(self.Capacity > 0):
            self._progress = int(self._procview.io['write_bytes'] / self._cap_in_bytes)
            self._progressString = "Erasing " + str(self.Progress) + "%" 
        else:
            self._progress = -1
            self._progressString = "Erasing"

        if(self._progress_cb != None) and callable(self._progress_cb):
            self._progress_cb(self.Progress, self._progressString)

        lastprogress = self._progress
        while self._monitor and (self._returncode == None):
            
            self._returncode = self._subproc.returncode
            if(self._returncode == None):
                io = self._procview.io
                if(self.Capacity > 0):
                    self._progress = int(io['write_bytes'] / self._cap_in_bytes)
                    self._progressString = "Erasing " + str(self.Progress) + "%" 
                else:
                    self._progress = -1
                    self._progressString = "Erasing"
                await asyncio.sleep(self._pollingInterval)

                if(self._progress != lastprogress):
                    if(self._progress_cb != None) and callable(self._progress_cb):
                        self._progress_cb(self.Progress, self._progressString)
                    lastprogress = self._progress
        self.returncode = self._returncode
        self.time_ended = datetime.datetime.now(datetime.timezone.utc)
        if(self._returncode == 0):
            self.notes.add("Full erase performed on storage device. Wrote 0xFF to all bits.", note_taker="hddmond")
        else:
            self.notes.add(f"Erase task failed. Return code: {self.returncode}", note_taker="hddmond")
        if(self._callback != None):
            self._callback(self._returncode)

TaskService.register(EraseTask.display_name, EraseTask)