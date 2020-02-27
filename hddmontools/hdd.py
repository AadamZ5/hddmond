import pyudev
import pySMART
import time
import subprocess
import datetime
import enum
from .pciaddress import PciAddress
from .test import Test, TestResult
from .task import EraseTask, ImageTask, TaskQueue
import proc.core

debug = False
def logwrite(s:str, endl='\n'):
    if debug:
        fd = open("./hdds.log", 'a')
        fd.write(s)
        fd.write(endl)
        fd.close()

class HealthStatus(enum.Enum):
    Failing = 0,
    ShortTesting = 1,
    LongTesting = 2,
    Default = 3,
    Passing = 4,
    Warn = 5,
    Unknown = 6,

    def __str__(self):
        return self.name

class TaskStatus(enum.Enum):
    Idle = 0,
    Erasing = 1,
    External = 2,
    Error = 3,
    Imaging = 4,
    ShortTesting = 4,
    LongTesting = 5,

    def __str__(self):
        return self.name

class Hdd:
    """
    Class for storing data about HDDs
    """

    def __getstate__(self):
        # Copy the object's state from self.__dict__ which contains
        # all our instance attributes. Always use the dict.copy()
        # method to avoid modifying the original state.
        state = self.__dict__.copy()
        # Remove the unpicklable entries. Udev references CDLL which won't pickle.
        state['_udev'] = None
        state['_task_changed_callbacks'] = None
        return state

    def __setstate__(self, state):
        # Restore instance attributes (i.e., serial and model).
        self.__dict__.update(state)
        # Restore the udev link
        self._udev = pyudev.Devices.from_device_file(pyudev.Context(), self.node)
        
    @property
    def testProgress(self):
        if(self.test != None):
            return self.test.progress
        else:
            if ('_test_progress' in self._smart.__dict__):
                return self._smart._test_progress
            else:
                return 0

    def __init__(self, node: str):
        '''
        Create a hdd object from its symlink node '/dev/sd?'
        '''
        self.serial = '"HDD"'
        self.model = str()
        self.wwn = str()
        self.node = node
        self.name = str(node).replace('/dev/', '')
        self._udev = pyudev.Devices.from_device_file(pyudev.Context(), node)
        self.OnPciAddress = None
        self.test = None
        self._task_changed_callbacks = []
        self._smart = pySMART.Device(self.node)
        self.port = None
        self.TaskQueue = TaskQueue(continue_on_error=False, task_change_callback=self._task_changed)
        self.CurrentTaskStatus = TaskStatus.Idle
        self.Size = self._smart.capacity
        
        try:
            sizeunit = self._smart.capacity.split()
            unit = sizeunit[1]
            size = float(sizeunit[0])

            if unit.lower() == 'tb':
                size = size * 1000

            self.capacity = size
        except AttributeError:
            pass
        except Exception as e:
            print("Exception occurred while parsing capacity of drive " + self.serial)
            print("This drive may not function properly")

        self._smart_last_call = time.time()
        self.medium = None #SSD or HDD
        self.status = HealthStatus.Default

        #Check interface
        if(self._smart.interface != None):

            #Set our status according to initial health assesment
            #self._map_smart_assesment()

            #See if we're currently running a test
            status, testObj, remain = self._smart.get_selftest_result()
            if status == 1:
                #self.testProgress = self._smart._test_progress
                if not (self.status == HealthStatus.ShortTesting) or (self.status == HealthStatus.LongTesting):
                    self.status = HealthStatus.LongTesting #We won't know if this is a short or long test, so assume it can be long for sake of not pissing off the user.
                    t = Test(self._smart, Test.Existing, callback=self._testCompletedCallback)
                    self.TaskQueue.AddTask(t, self._longtest)
                else:
                    pass
            
            self.serial = str(self._smart.serial).replace('-', '')
            self.model = self._smart.model
            if(self._smart.is_ssd):
                self.medium = "SSD"
            else:
                self.medium = "HDD"
        else:
            self.status = HealthStatus.Unknown
            self.serial = "Unknown HDD"
            self.model = ""
            #Idk where we go from here
        
    @staticmethod
    def FromSmartDevice(d: pySMART.Device):
        '''
        Create a HDD object from a pySMART Device object
        '''
        return Hdd("/dev/" + d.name)

    @staticmethod
    def FromUdevDevice(d: pyudev.Device): #pyudev.Device
        '''
        Create a HDD object from a pyudev Device object
        '''
        h = Hdd(d.device_node)
        h._udev = d
        return h

    @staticmethod
    def IsHdd(node: str):
        '''
        See if this storage object has an HDD-like interface.
        '''
        if(pySMART.Device(node).interface != None):
            return True
        else:
            return False

    def _task_changed(self, *args, **kw):
        for c in self._task_changed_callbacks:
            if c != None and callable(c):
                c(self, *args, **kw)

    def AddTaskChangeCallback(self, callback):
        self._task_changed_callbacks.append(callback)

    def _testCompletedCallback(self, result: TestResult):
        if(result == TestResult.FINISH_PASSED):
            self.status = HealthStatus.Passing

        elif(result == TestResult.FINISH_FAILED): 
            self.status = HealthStatus.Failing

        elif(result == TestResult.ABORTED):
            self.status = HealthStatus.Default
        elif(result == TestResult.CANT_START):
            self.status = self.status
        else:
            self.status = HealthStatus.Warn

        self._taskCompletedCallback(0)
    
    def _shorttest(self):
        self.status = HealthStatus.ShortTesting
        self.CurrentTaskStatus = TaskStatus.ShortTesting

    def _longtest(self):
        self.status = HealthStatus.LongTesting
        self.CurrentTaskStatus = TaskStatus.LongTesting

    def ShortTest(self):
        #self.status = HealthStatus.ShortTesting
        t = Test(self._smart, 'short', pollingInterval=5, callback=self._testCompletedCallback)
        self.TaskQueue.AddTask(t, preexec_cb=self._shorttest)

    def LongTest(self):
        #self.status = HealthStatus.ShortTesting
        t = Test(self._smart, 'long', pollingInterval=5, callback=self._testCompletedCallback)
        self.TaskQueue.AddTask(t, preexec_cb=self._longtest)

    def AbortTest(self):
        if(self.test != None):
            self.test.abort()

    def _taskCompletedCallback(self, returncode):
        if(returncode != 0):
            self.CurrentTaskStatus = TaskStatus.Error
        else:
            self.CurrentTaskStatus = TaskStatus.Idle

    def _erasing(self):
        self.CurrentTaskStatus = TaskStatus.Erasing

    def Erase(self, callback=None):
        if not self.TaskQueue.Full:
            t = EraseTask(self.node, self.Size.replace('GB', '').strip(), callback=self._taskCompletedCallback)
            r = self.TaskQueue.AddTask(t, preexec_cb=self._erasing)
            return r #We probably queued the task sucessfully
        else:
            return False #Queue is full

    def _imaging(self):
        self.CurrentTaskStatus = TaskStatus.Imaging

    def Image(self, image, callback=None):
        if not self.TaskQueue.Full:
            t = ImageTask(image, self.name, self._taskCompletedCallback)
            self.TaskQueue.AddTask(t, preexec_cb=self._imaging)
            return True #We queued the task sucessfully
        else:
            return False #Queue is full, wait.

    def GetTestProgressString(self):
        if(self.testProgress == None):
            p = "0"
        else:
            p = str(self.testProgress)

        return p + "%"
    
    def GetTaskProgressString(self):
        if(self.TaskQueue.CurrentTask != None) and (self.CurrentTaskStatus != TaskStatus.Idle):
            if(self.CurrentTaskStatus == TaskStatus.Error):
                return "Err: " + str(self.TaskQueue.CurrentTask._returncode)
            elif(self.TaskQueue.CurrentTask.Finished):
                return "Done"
            elif(self.TaskQueue.CurrentTask != None):
                return self.TaskQueue.CurrentTask.ProgressString
            else:
                return "Busy"
                
        else:
            return "Idle"

    def UpdateSmart(self):
        self._smart.update()
        #print(self._smart._test_running)
                
    def refresh(self):
        pass
            
    def __str__(self):
        if(self.serial):
            return self.serial
        else:
            return "???"

    def __repr__(self):
        if(self._smart.is_ssd):
            t = "SSD"
        else:
            t = "HDD"
        s = t + " " + str(self.serial) + " at " + str(self.node)
        return "<" + s + ">"

class HddViewModel:
    def __init__(self, serial=None, node=None, taskQueueSize=0, pciAddress=None, status=None, taskStatus=None, taskString=None, testProgress=None, port=None, size=None, isSsd=None, smartResult=None):
        self.serial=serial
        self.node=node
        self.pciAddress=pciAddress
        self.status=status
        self.taskStatus=taskStatus
        self.taskString=taskString
        self.testProgress=testProgress
        self.port=port
        self.size=size
        self.isSsd=isSsd
        self.smartResult=smartResult
        self.taskQueueSize = taskQueueSize

    @staticmethod
    def FromHdd(h: Hdd):
        logwrite(str(h))
        hvm = HddViewModel(serial=h.serial, node=h.node, pciAddress=h.OnPciAddress, status=h.status, testProgress=h.GetTestProgressString(), taskStatus=h.CurrentTaskStatus, taskString=h.GetTaskProgressString(), port=h.Port, size=h.Size, isSsd=h._smart.is_ssd, taskQueueSize=len(h.TaskQueue.Queue))
        hvm.smartResult = h._smart.__dict__.get('assessment', h._smart.__dict__.get('smart_status', None)) #Pickling mixup https://github.com/freenas/py-SMART/issues/23
        logwrite("\t" + str(hvm.status))
        return hvm