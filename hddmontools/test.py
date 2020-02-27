import pySMART
import threading
import time
import enum
import datetime
from .task import Task

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

    def __init__(self, smart_device: pySMART.Device, testType, pollingInterval=5, callback=None, progressCallback=None):
        self.device = smart_device
        self.testType = testType
        self.result = None
        self._progress = 0
        self._progressCallback = progressCallback
        self.date_completed = None
        self.date_started = None
        self.passed = False
        self._pollingInterval = pollingInterval
        self._testing = True
        self._finished = False
        if(self.testType == Test.Existing):
            self._testingThread = threading.Thread(target=self._loose_test, args=(pollingInterval,))
        else:
            self._testingThread = threading.Thread(target=self._captive_test, args=(self.testType, pollingInterval,))
        self._started = False
        super(Test, self).__init__("Long test" if self.testType == Test.Long else ("Short test" if self.testType == Test.Short else "Test"))
        self._progressString = "Test"
        self._callback = callback
        self._progress_cb = None
        self._last_progress = self._progress

    def start(self, progress_callback=None):
        if not self._started:
            self._progress_cb = progress_callback
            self._testingThread.start()
            self._started = True
        else:
            return

    def _loose_test(self, *args):
        while self._testing:
            r, t, p = self.device.get_selftest_result()
            if(r == 1):
                if(p != None):
                    self._progressHandler(p)
                time.sleep(args[0])
            else:
                self._testing = False

        self._processReturnCode(r, t)     
        self._callCallbacks()

    def _captive_test(self, *args):
        self.date_started = datetime.datetime.now()
        r, t = self.device.run_selftest_and_wait(args[0], polling=args[1], progress_handler=self._progressHandler)
        self.date_completed = datetime.datetime.now()
        #After we finish the test
        self._processReturnCode(r, t)
        self._testing = False
        self._finished = True
        self._callCallbacks()

    def abort(self):
        self.device.abort_selftest()
        #The _test function takes care of the result management

    def detach(self):
        '''
        Closes this test object without aborting the offline test.
        '''
        self._testing = False
        self._testingThread.join()

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
        elif (r == 3): #Aborted
            self.result = TestResult.ABORTED
            self.passed = False
        else: #2 = No new selftests,    4 = Unknown smartctl error
            self.result = TestResult.UNKNOWN
            self.passed = False
        lock.release()

    def _callCallbacks(self):
        if(self._callback != None and callable(self._callback)):
            self._callback(self.result)

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
        

            
            

            
