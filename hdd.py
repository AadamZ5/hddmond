import pyudev
import pySMART
import multitasking
import time
import multiprocessing
import datetime


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

    def __init__(self, node: str):
        self.serial = '"HDD"'
        self.model = str()
        self.testProgress = int()
        self.node = node
        self.estimatedCompletionTime = datetime.datetime.now()
        self._smart = pySMART.Device(self.node)

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
            
            self.serial = self._smart.serial
            self.model = self._smart.model
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
        return Hdd(d.device_node)

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

    def GetTestProgressString(self):
        return str(self.testProgress) + "%"

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