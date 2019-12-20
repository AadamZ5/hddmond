import pyudev
import pySMART
import time
import subprocess
import datetime
import pciaddress
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
        del state['CurrentTask']
        return state

    def __setstate__(self, state):
        # Restore instance attributes (i.e., filename and lineno).
        self.__dict__.update(state)
        # Restore the udev link
        self._udev = pyudev.Devices.from_device_file(pyudev.Context(), self.node)
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

        #Check interface
        if(self._smart.interface != None):

            #Set our status according to initial health assesment
            if(self._smart.assessment == "PASS"):
                self.status = Hdd.STATUS_DEFAULT
            elif(self._smart.assessment == "FAIL"):
                self.status = Hdd.STATUS_FAILING
            else:
                self.status = Hdd.STATUS_UNKNOWN

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
        else:
            self.status = Hdd.STATUS_UNKNOWN
            self.serial = "Unknown HDD"
            self.model = ""
            #Idk where we go from here
        
        sysp = self._udev.sys_path

#     0    1     2        3           4        5     6        7          8      9   10
#EX1:   '/sys/devices/pci0000:00/0000:00:1f.2/ata2/host2/target2:0:0/2:0:0:0/block/sdb        <== For a drive on the internal SATA controller!

#     0    1     2        3           4             5        6       7          8             9         10      11   12
#EX2:   '/sys/devices/pci0000:00/0000:00:01.0/0000:01:00.0/host0/port-0:3/end_device-0:3/target0:0:3/0:0:3:0/block/sdc'   <== For a drive on the LSI SAS controller!

        driveinfo = sysp.split('/')
        pci = str(driveinfo[4])

        #self.OnPciAddress = 
        
        
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
        return str(self.testProgress) + "%"
    
    def GetTaskProgressString(self):
        if(self.CurrentTaskStatus == Hdd.TASK_ERASING):
            return "Erasing"
        elif(self.CurrentTaskStatus == Hdd.TASK_NONE):
            return "Idle"
        elif(self.CurrentTaskStatus == Hdd.TASK_EXTERNAL):
            if(type(self.CurrentTask) == proc.core.Process):
                return str(self.CurrentTask.comm)
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
        if(self.CurrentTaskStatus != Hdd.TASK_NONE):
            logwrite(str(self.serial) + ": Task running! Task type: " + self.CurrentTaskStatus)
        else:
            logwrite(str(self.serial) + ": No task running.")
        
        if(self.CurrentTaskStatus == Hdd.TASK_ERASING):
            if(self.CurrentTask != None):
                r = self.CurrentTask.poll() #Returns either a return code, or 'None' type if the process isn't finished.
                if(r != None):
                    self.CurrentTaskReturnCode = r
                    if(r == 0):
                        self.CurrentTaskStatus == Hdd.TASK_NONE
                        self.CurrentTask = None
                    else:
                        self.CurrentTaskStatus = Hdd.TASK_ERROR
                else:
                    pass #Its still running
                    #logwrite("Task running: " + str(self.CurrentTask.pid))
            else:
                self.CurrentTaskStatus == Hdd.TASK_NONE
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
        else:
            self.status = Hdd.STATUS_UNKNOWN

    def __str__(self):
        if(self.serial):
            return self.serial
        else:
            return "???"

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