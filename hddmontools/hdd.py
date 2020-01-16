import pyudev
import pySMART
import time
import subprocess
import datetime
from .pciaddress import PciAddress
import proc.core

debug = False
def logwrite(s:str, endl='\n'):
    if debug:
        fd = open("./hdds.log", 'a')
        fd.write(s)
        fd.write(endl)
        fd.close()

class Hdd:
    """
    Class for storing data about HDDs
    """
    
    STATUS_FAILING = 'failinghdd'
    STATUS_TESTING = 'testinghdd'
    STATUS_LONGTST = 'longtsthdd'
    STATUS_DEFAULT = 'defaulthdd'
    STATUS_PASSING = 'passinghdd'
    STATUS_WARNING = 'warninghdd'
    STATUS_UNKNOWN = 'unknownhdd'
    TASK_ERASING = 'taskerase'
    TASK_NONE = 'tasknone'
    TASK_EXTERNAL = 'taskextern'
    TASK_ERROR = 'taskerror'

    def __getstate__(self):
        # Copy the object's state from self.__dict__ which contains
        # all our instance attributes. Always use the dict.copy()
        # method to avoid modifying the original state.
        state = self.__dict__.copy()
        # Remove the unpicklable entries. Udev references CDLL which won't pickle.
        del state['_udev']

        #subprocess.Popen objects wont pickle because of threads, but proc.core.Process objects will.
        if(type(self.CurrentTask) == subprocess.Popen):
            del state['CurrentTask']
        return state

    def __setstate__(self, state):
        # Restore instance attributes (i.e., filename and lineno).
        self.__dict__.update(state)
        # Restore the udev link
        self._udev = pyudev.Devices.from_device_file(pyudev.Context(), self.node)
        if not ('CurrentTask' in vars(self)):
            self.CurrentTask = None
        

    def __init__(self, node: str):
        '''
        Create a hdd object from its symlink node
        '''
        self.serial = '"HDD"'
        self.model = str()
        self.testProgress = int()
        self.node = node
        self.name = str(node).replace('/dev/', '')
        self._udev = pyudev.Devices.from_device_file(pyudev.Context(), node)
        self.OnPciAddress = None
        self.estimatedCompletionTime = datetime.datetime.now()
        self._smart = pySMART.Device(self.node)
        self.Port = None
        self.CurrentTask = None
        self.CurrentTaskStatus = Hdd.TASK_NONE
        self.CurrentTaskReturnCode = None
        self.Size = self._smart.capacity
        self._smart_last_call = time.time()
        self.medium = None
        self._smart.tests
        #Check interface
        if(self._smart.interface != None):

            #Set our status according to initial health assesment
            self._map_smart_assesment()

            #See if we're currently running a test
            status, testObj, remain = self._smart.get_selftest_result()
            if status == 1:
                self.testProgress = self._smart._test_progress
                if not (self.status == Hdd.STATUS_TESTING) or (self.status == Hdd.STATUS_LONGTST):
                    self.status = Hdd.STATUS_LONGTST #We won't know if this is a short or long test, so assume it can be long for sake of not pissing off the user.
                else:
                    pass
            
            self.serial = str(self._smart.serial).replace('-', '')
            self.model = self._smart.model
            if(self._smart.is_ssd):
                self.medium = "SSD"
            else:
                self.medium = "HDD"
        else:
            self.status = Hdd.STATUS_UNKNOWN
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

    def ShortTest(self):
        self.status = Hdd.STATUS_TESTING
        status, message, time = self._smart.run_selftest('short')
        if(status == 0):
            self.estimatedCompletionTime = datetime.datetime.strptime(str(time), r'%a %b %d %H:%M:%S %Y')
        self._smart.update()

    def LongTest(self):
        self.status = Hdd.STATUS_LONGTST
        status, message, time = self._smart.run_selftest('long')
        if(status == 0):
            self.estimatedCompletionTime = datetime.datetime.strptime(str(time), r'%a %b %d %H:%M:%S %Y')
        self._smart.update()

    def AbortTest(self):
        if(self._smart._test_running):
            self._smart.abort_selftest()
            self.status = Hdd.STATUS_UNKNOWN
            self._smart._test_running = False
            self.estimatedCompletionTime = datetime.datetime.now()

    def Erase(self):
        if(self.CurrentTask == None):
            self.CurrentTask = subprocess.Popen(['scrub', '-f', '-p', 'fillff', self.node], stdout=subprocess.PIPE, stderr=subprocess.PIPE, universal_newlines=True)
            self.CurrentTaskStatus = Hdd.TASK_ERASING
            return True #We started the task sucessfully
        else:
            return False #There is a task running on this hdd. cancel it first

    def GetTestProgressString(self):
        if(self.testProgress == None):
            p = "0"
        else:
            p = str(self.testProgress)

        return p + "%"
    
    def GetTaskProgressString(self):
        if(self.CurrentTaskStatus == Hdd.TASK_ERASING):
            return "Erasing"
        elif(self.CurrentTaskStatus == Hdd.TASK_NONE):
            return "Idle"
        elif(self.CurrentTaskStatus == Hdd.TASK_EXTERNAL):
            if(type(self.CurrentTask) == proc.core.Process):
                return "PID " + str(self.CurrentTask.pid)
        elif(self.CurrentTaskStatus == Hdd.TASK_ERROR):
            return "Err: " + str(self.CurrentTaskReturnCode)
        else:
            return "???"

    def _getRemainingTime(self):
        complete = self.estimatedCompletionTime
        now = datetime.datetime.now()
        if complete > now:
            timedeltaLeft = (complete - now)
            mm, ss = divmod(timedeltaLeft.total_seconds(), 60)
            hh, mm = divmod(mm, 60)
            s = "%d:%02d:%02d" % (hh, mm, ss)
            return s
        else:
            return "0:00:00"

    def UpdateSmart(self):
        self._smart.update()
        self.testProgress = self._smart._test_progress
        #print(self._smart._test_running)

    def UpdateTask(self):
        if(self.CurrentTaskStatus != Hdd.TASK_NONE) and (self.CurrentTaskStatus != Hdd.TASK_ERROR):
            logwrite(str(self.serial) + ": Task running! Task type: " + self.CurrentTaskStatus)
        else:
            if(self.CurrentTask != None):
                if(type(self.CurrentTask) == proc.core.Process):
                    if(self.CurrentTask.is_alive):
                        pass
                    else:
                        self.CurrentTask = None
                        self.CurrentTaskStatus = Hdd.TASK_NONE
            else:
                logwrite(str(self.serial) + ": No task running.")
        
        if(self.CurrentTaskStatus == Hdd.TASK_ERASING):
            if(self.CurrentTask != None):
                r = self.CurrentTask.poll() #Returns either a return code, or 'None' type if the process isn't finished.
                self.CurrentTaskReturnCode = r
                if(r != None):
                    if(r == 0):
                        self.CurrentTaskStatus == Hdd.TASK_NONE
                        self.CurrentTask = None
                    else:
                        self.CurrentTaskStatus = Hdd.TASK_ERROR
                        self.CurrentTask = None
                else:
                    pass #Its still running
                    #logwrite("Task running: " + str(self.CurrentTask.pid))
            else:
                self.CurrentTaskStatus = Hdd.TASK_NONE
        elif(self.CurrentTaskStatus == Hdd.TASK_EXTERNAL):
            if(type(self.CurrentTask) == proc.core.Process):
                if(self.CurrentTask.is_alive):
                    pass
                else:
                    self.CurrentTask = None
                    self.CurrentTaskStatus = Hdd.TASK_NONE
        else:
            pass
                
                    
                    

    def refresh(self):
        #status, testObj, remain = self._smart.get_selftest_result()
        #self._smart.update()

        self._map_smart_assesment()
            
        
    def _map_smart_assesment(self):
        if self._smart._test_running == True:
            self.testProgress = self._smart._test_progress
            if not (self.status == Hdd.STATUS_TESTING) or (self.status == Hdd.STATUS_LONGTST):
                self.status = Hdd.STATUS_LONGTST
            else:
                pass
        elif self._smart.assessment == 'PASS':
            self.status = Hdd.STATUS_PASSING
        elif self._smart.assessment == 'FAIL':
            self.status = Hdd.STATUS_FAILING
        elif self._smart.assessment == 'WARN':
            self.status = Hdd.STATUS_WARNING
        else:
            self.status = Hdd.STATUS_UNKNOWN

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
    def __init__(self, serial=None, node=None, pciAddress=None, status=None, taskStatus=None, taskString=None, testProgress=None, port=None, size=None, isSsd=None, smartResult=None):
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

    @staticmethod
    def FromHdd(h: Hdd):
        logwrite(str(h))
        hvm = HddViewModel(serial=h.serial, node=h.node, pciAddress=h.OnPciAddress, status=h.status, testProgress=h.GetTestProgressString(), taskStatus=h.CurrentTaskStatus, taskString=h.GetTaskProgressString(), port=h.Port, size=h.Size, isSsd=h._smart.is_ssd)
        hvm.smartResult = h._smart.__dict__.get('assessment', h._smart.__dict__.get('smart_status', None)) #Pickling mixup https://github.com/freenas/py-SMART/issues/23
        logwrite("\t" + hvm.status)
        return hvm