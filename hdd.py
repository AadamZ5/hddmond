import pyudev
import pySMART
import multitasking

multitasking.set_max_threads(20)

class Hdd:
    """
    Class for storing data about HDDs
    """

    STATUS_FAILING = 'failinghdd'
    STATUS_TESTING = 'testinghdd'
    STATUS_DEFAULT = 'defaulthdd'
    STATUS_PASSING = 'passinghdd'
    STATUS_UNKNOWN = 'unknownhdd'

    def __init__(self, node: str):
        self.serial = '"HDD"'
        self.model = str()
        self.testProgress
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

    def _testProgressHandler(self, testProgress):
        self.testProgress = testProgress
        self.testProgressCallback(testProgress)

    @multitasking.task
    def ShortTest(self, callback=None):
        self.status = Hdd.STATUS_TESTING
        self.testProgressCallback = callback
        self._smart.run_selftest_and_wait('short', progress_handler=self._testProgressHandler)

    @multitasking.task
    def LongTest(self, callback=None):
        self.status = Hdd.STATUS_TESTING
        self.testProgressCallback = callback
        self._smart.run_selftest_and_wait('long', progress_handler=self._testProgressHandler)

    def __str__(self):
        if(self.serial):
            return self.serial
        else:
            return "???"