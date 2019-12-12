import pyudev
import pySMART
import time
import subprocess
import datetime
import pciaddress


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
            self.CurrentTask = subprocess.Popen(['scrub', '-p', 'fillff', self.node], stdout=subprocess.PIPE, stderr=subprocess.PIPE, universal_newlines=True)
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
        if(self.CurrentTaskStatus == Hdd.TASK_ERASING):
            if(self.CurrentTask != None):
                r = self.CurrentTask.poll()
                if(r):
                    if(r == 0):
                        self.CurrentTaskStatus == Hdd.TASK_NONE
                        self.CurrentTask = None
                    else:
                        pass #What do we do if there is an error?
                else:
                    pass
            else:
                self.CurrentTaskStatus == Hdd.TASK_NONE
                
                    
                    

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