import pySMART
import threading
import time
import enum
import datetime

class TestResult(enum.Enum):
    FINISH_PASSED = 1,
    FINISH_FAILED = 0,
    CANT_START = 2,
    ABORTED = 3,
    UNKNOWN = 4,

class Test():
    Short = 'short'
    Long = 'long'
    Existing = 'existing'

    @property
    def testing(self):
        return self.device._test_running

    @property
    def progress(self):
        return self._progress

    def __getstate__(self):
        state = self.__dict__.copy()
        del state['_testingThread']
        return state

    def __setstate__(self, state):
        state['_testingThread'] = None
        self.__dict__.update(state)

    def __init__(self, smart_device: pySMART.Device, testType, pollingInterval=5, callback=None, progressCallback=None):
        self.device = smart_device
        self.testType = testType
        self.result = None
        self._progress = 0
        self._callbacks = []
        self._progressCallback = progressCallback
        self.date_completed = None
        self.date_started = None
        self.passed = False
        if(callback):
            self._callbacks.append(callback)
        self._pollingInterval = pollingInterval
        self._testing = True
        if(self.testType == Test.Existing):
            self._testingThread = threading.Thread(target=self._loose_test, args=(pollingInterval,))
        else:
            self._testingThread = threading.Thread(target=self._captive_test, args=(self.testType, pollingInterval,))
        self._testingThread.start()

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
        self._callCallbacks()

    def abort(self):
        self.device.abort_selftest()
        #The _test function takes care of the result management

    def detach(self):
        '''
        Closes this test object without aborting the offline test.
        '''
        self._testingThread._stop()
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
        for cb in self._callbacks:
            cb(self.result)

    def _progressHandler(self, progress):
        try:
            self._progress = int(progress)
        except Exception as e:
            pass
        if(self._progressCallback != None):
            self._progressCallback(progress)

            
            

            
