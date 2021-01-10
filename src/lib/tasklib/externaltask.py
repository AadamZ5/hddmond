import proc
import datetime
import asyncio

from typing import Coroutine

from lib.tasklib.task import Task

class ExternalTask(Task):

    display_name = "External Task"

    parameter_schema = None

    @property
    def Finished(self):
        return self._finished

    @property
    def PID(self):
        return self._PID if self._PID != None else "Unknown"

    def __getstate__(self):
        state = self.__dict__.copy()
        state['_pollingThread'] = None
        return state

    def __setstate__(self, state):
        self.__dict__.update(state)

    def __init__(self, hdd,  pid, processExitCallback=None, pollingInterval=5, start=False):
        super(ExternalTask, self).__init__("External", hdd)
        
        self._procview = proc.core.Process.from_pid(pid)

        try:
            self._PID = self._procview.pid
            self._finished = False
            self._poll = True
            self.notes.add("An external task was detected running on this storage device.\nCommand: " + str(" ".join(map(str, self._procview.cmdline))), note_taker="hddmond")
        except AttributeError: #Sometimes _procview is None from the start if the process exited super fast, so if that's the case, go ahead and finish.
            self._PID = -1
            self._finished = True
            self._poll = False
            self.notes.add("An external task was detected running on this storage device.", note_taker="hddmond")

        self._pollingInterval = pollingInterval
        self._pollingTask = None
        self.returncode = 0
        self._callback = processExitCallback
        self._progressString = "PID " + str(self.PID)
        
        if(start):
            self.start()
        
    def start(self, progress_callback=None):
        if(self._pollingTask != None):
            return False
        else:
            self.time_started = datetime.datetime.now(datetime.timezone.utc)
            self._pollingTask = asyncio.get_event_loop().create_task(self._pollProcess(), name="external_task_poll")
            return True

    async def _pollProcess(self):
        while self._poll == True and self._finished == False:
            if(self._procview.is_alive == False): # is_alive is a generated bool, evaluating every time we check it. This should be a real-time status. 
                self._finished = True
            else:
                await asyncio.sleep(self._pollingInterval)

        self.notes.add("The process has exited.", note_taker="hddmond")
        self.time_ended = datetime.datetime.now(datetime.timezone.utc)
        if(self._callback != None) and (self._poll == True):
            # Since callback can be absolutely anything, lets call it in the asyncio executor. This is also appropriate becase
            # we don't care about the response of the callback. We just wanna send data.

            # Also, they might be expecting a return code. We can't obtain it, so assume 0. 
            if(isinstance(self._callback, Coroutine)):
                asyncio.get_event_loop().create_task(self._callback(0)) # We use create_task so we don't block here.
            else:
                asyncio.get_event_loop().run_in_executor(None, self._callback, 0) # Again, don't block here.
    
    async def abort(self, wait=False, true_abort=False):
        if(true_abort == True): #Don't kill the process unless explicitly stated.
            if(self._procview != None) and (self._procview.is_alive == True):
                self.notes.add("A termination signal was sent to the process.", note_taker="hddmond")
                self._procview.terminate()
        else:
            if wait == True:
                await self.detach()
            else:
                asyncio.get_event_loop().create_task(self.detach())

    async def detach(self):
        '''
        Should be used only when quitting the hddmon-daemon program
        '''
        self._poll = False
        while not self._pollingTask.done():
            await asyncio.sleep(0)
        self.notes.add("The process was detatched from the hddmond monitor.", note_taker="hddmond")