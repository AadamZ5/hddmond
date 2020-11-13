from hddmontools.hdd_detector import HddDetector
from pySMART import DeviceList, Device

import threading
import time


class SmartctlDetector(HddDetector):

    def __init__(self, poll_interval=2):
        self._callbacks = []
        self._dev_cache = []
        self._loopgo = True
        self._poll_interval = poll_interval
        self._poll_thread = threading.Thread(target=self._poll_method, name="SmartctlDetector")

    def start(self):
        self._poll_thread.start()

    def stop(self):
        self._loopgo = False
        self._poll_thread.join()

    def _poll_method(self):
        while self._loopgo:
            devices = DeviceList().devices
            for d in devices:
                for cd in self._dev_cache:
                    if d.serial == cd.serial:
                        self._dev_cache.remove(cd) #It exists!
                        break
                else:
                    self._do_callback('add', d) #It doesn't exist, let people know it is new.
            
            for d in self._dev_cache:
                #These devices weren't found during the last comparison, so they must have been removed.
                #self._dev_cache.remove(d)
                self._do_callback('remove', d)

            self._dev_cache = devices.copy() #Our new cache is what we were given this round.
            time.sleep(self._poll_interval)

    def _do_callback(self, action, device: Device):
        for c in self._callbacks:
            if callable(c):
                c(action=action, serial=device.serial, node=f"/dev/{device.name}")

    def add_change_callback(self, callback):
        self._callbacks.append(callback)