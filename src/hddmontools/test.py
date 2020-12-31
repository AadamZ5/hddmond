import pySMART
import threading
import time
import enum
import datetime
import asyncio
import functools

from .task import Task
from .task_service import TaskService

class TestResult(enum.Enum):
    FINISH_PASSED = 0
    FINISH_FAILED = 1
    CANT_START = 2
    ABORTED = 3
    UNKNOWN = 4

    def __int__(self):
        return self.value

class Test(Task):
    Short = 'short'
    Long = 'long'
    Existing = 'existing'

    display_name = "Test"

    parameter_schema = """{
    "default": {},
    "description": "The parameters for the Test task",
    "examples": [
        {
            "test_type": "Short"
        }
    ],
    "required": [
        "test_type"
    ],
    "title": "Test task parameters",
    "properties": {
        "test_type": {
            "default": "Short",
            "description": "The duration of the SMART test for the selected drive(s)",
            "examples": [
                "short"
            ],
            "enum": [
                "Short",
                "Long"
            ],
            "title": "Test type"
        }
    },
    "additionalProperties": true
}"""

    @property
    def testing(self):
        return self.device._test_running

    @property
    def Progress(self):
        return self._progress

    @property
    def Finished(self):
        return self._finished

    def __getstate__(self):
        state = self.__dict__.copy()
        state['_testingThread'] = None
        return state

    def __setstate__(self, state):
        self.__dict__.update(state)

    def __init__(self, hdd, test_type: str="short", pollingInterval=5, callback=None, progressCallback=None):
        self.device = hdd._smart
        self.test_type = test_type
        self.result = None
        self._progress = 0
        self._progressCallback = progressCallback
        self._pollingInterval = pollingInterval
        self.date_completed = None
        self.date_started = None
        self.passed = False
        self._pollingInterval = pollingInterval
        self._testing = True
        self._finished = False
        self._testingTask = None
        self._started = False
        super(Test, self).__init__("Long test" if self.test_type.lower() == Test.Long else ("Short test" if self.test_type.lower() == Test.Short else "Test"), hdd)
        self._progressString = "Test"
        self._callback = callback
        self._progress_cb = None
        self._last_progress = self._progress

    def start(self, progress_callback=None):
        if not self._started:
            if(self.test_type == Test.Existing):
                self._testingTask = asyncio.get_event_loop().create_task(self._loose_test(self._pollingInterval), name="test_task_loosepoll")
            else:
                self._testingTask = asyncio.get_event_loop().create_task(self._captive_test(self.test_type, self._pollingInterval), name="test_task_poll")
            if(self.test_type == Test.Existing):
                self.notes.add("Monitoring existing test on storage device.", note_taker="hddmond")
            else:
                self.notes.add("Started " + self.test_type + " SMART test on storage device.", note_taker="hddmond")
            self._progress_cb = progress_callback
            self._started = True
        else:
            return

    async def _loose_test(self, *args):
        while self._testing:
            r, t, p = await asyncio.get_event_loop().run_in_executor(None, self.device.get_selftest_result)
            if(r == 1):
                if(p != None):
                    self._progressHandler(p)
                asyncio.sleep(args[0])
            else:
                self._testing = False

        self._processReturnCode(r, t)    
        self._callCallbacks()

    async def _captive_test(self, test_type, polling_interval):
        self.time_started = datetime.datetime.now(datetime.timezone.utc)
        r, t = await asyncio.get_event_loop().run_in_executor(None, functools.partial(self.device.run_selftest_and_wait, test_type, polling=polling_interval, progress_handler=self._progressHandler))
        self.time_ended = datetime.datetime.now(datetime.timezone.utc)
        #After we finish the test
        self._processReturnCode(r, t)
        self._testing = False
        self._finished = True
        self._callCallbacks()

    async def abort(self, wait=False):
        self.notes.add("Aborted test.", note_taker="hddmond")
        await asyncio.get_event_loop().run_in_executor(None, self.device.abort_selftest)
        #The _test function takes care of the result management
        if wait == True:
            print("\tWaiting for {0} to stop...".format(self._testingTask.name))
            while not self._testingTask.done():
                asyncio.sleep(0)

    def detach(self):
        '''
        Closes this test object without aborting the offline test.
        '''
        
        self._testing = False
        while not self._testingTask.done():
            asyncio.sleep(0)
        self.notes.add("Detached test, no longer monitored by hddmon.", note_taker="hddmond")

    def _processReturnCode(self, r, t):
        lock = threading.Lock() #Lock this thread so we can do some instant variable assignments without sleeping and risking reporting wrong variables
        lock.acquire()
        self.result = TestResult.UNKNOWN
        if (r == 0): #Completed
            if 'failure' in t.status.lower():
                self.result = TestResult.FINISH_FAILED
                self.passed = False
            elif 'without error' in t.status.lower():
                self.result = TestResult.FINISH_PASSED
                self.passed = True
            
        elif (r == 1): #Selftest running
            self.result = TestResult.CANT_START
            self.passed = False
            self.notes.add("A test is already running", note_taker="hddmond")
        elif (r == 3): #Aborted
            self.result = TestResult.ABORTED
            self.passed = False
            self.notes.add("The test was aborted", note_taker="hddmond")
        else: #2 = No new selftests,    4 = Unknown smartctl error
            self.result = TestResult.UNKNOWN
            self.passed = False
            self.notes.add("The test result is unknown", note_taker="hddmond")
        self.returncode = int(self.result)
        lock.release()
        self.notes.add("Test " + ("passed" if self.passed else "failed"), note_taker="hddmond")

    def _callCallbacks(self):
        if(self._callback != None and callable(self._callback)):
            self._callback(self.returncode)

    def _progressHandler(self, progress):
        try:
            self._progress = int(progress)
        except Exception as e:
            pass
        self._progressString = "Testing " + str(self._progress) + "%"
        if self._progress != self._last_progress:
            if(self._progressCallback != None) and callable(self._progressCallback):
                self._progressCallback(progress)
            if(self._progress_cb != None) and callable(self._progress_cb):
                self._progress_cb(self._progress, self._progressString)
            self._last_progress = self._progress
        
TaskService.register(Test.display_name, Test)
            
            

            
