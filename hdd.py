import pyudev
import pySMART
import multitasking
import time

multitasking.set_max_threads(20)

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
        self.testProgress = ""
        self.node = node
        self._smart = pySMART.Device(self.node)
        if(self._smart.interface != None):
            #print("Has interface " + str(self._smart.interface))
            #print("Result: " + str(self._smart.assessment))
            if(self._smart.assessment == "PASS"):
                self.status = Hdd.STATUS_DEFAULT
            elif(self._smart.assessment == "FAIL"):
                self.status = Hdd.STATUS_FAILING
            self.serial = self._smart.serial
            self.model = self._smart.model
        else:
            #print("Can't read SMART data!")
            self.status = Hdd.STATUS_UNKNOWN
            self.serial = "Unknown HDD"
            self.model = ""
        
    @staticmethod
    def FromSmartDevice(d: pySMART.Device):
        return Hdd("/dev/" + d.name)

    @staticmethod
    def FromUdevDevice(d: pyudev.Device): #pyudev.Device
        return Hdd(d.device_node)

    @staticmethod
    def IsHdd(node: str):
        if(pySMART.Device(node).interface != None):
            return True
        else:
            return False

    def ShortTest(self):
        self.status = Hdd.STATUS_TESTING
        self._smart.run_selftest('short')
        self.testProgress = self._smart._test_progress
        
    def LongTest(self):
        self.status = Hdd.STATUS_LONGTST
        self._smart.run_selftest('long')

    def AbortTest(self):
        if(self._smart._test_running):
            self._smart.abort_selftest()
            self.status = Hdd.STATUS_UNKNOWN
            self._smart._test_running = False

    def _getTestProgress(self):
        return self._smart._test_progress

    def refresh(self):
        if self._smart._test_running:
            self.testProgress = self._smart._test_progress
            self.status = self.status
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