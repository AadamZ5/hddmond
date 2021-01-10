from lib.hdd_detector import HddDetector
from pySMART import DeviceList, Device

import threading
import time
import asyncio
import logging

class SmartctlDetector(HddDetector):

    def __init__(self, poll_interval=2):
        self.logger = logging.getLogger(__name__ + "." + self.__class__.__qualname__)
        self.logger.setLevel(logging.DEBUG)
        self.logger.info("Initializing SmartctlDetector...")
        self._callbacks = []
        self._dev_cache = []
        self._loopgo = True
        self._poll_interval = poll_interval

    async def start(self):
        self.logger.info("Starting SmartctlDetector...")
        asyncio.get_event_loop().create_task(self._poll_method())

    async def stop(self):
        self.logger.info("Stopping SmartctlDetector...")
        self._loopgo = False

    def _make_device_list(self):
        return DeviceList()

    async def _poll_method(self):
        loop = asyncio.get_event_loop()
        while self._loopgo:
            dev_list = await loop.run_in_executor(None, self._make_device_list)
            devices = dev_list.devices
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
            await asyncio.sleep(self._poll_interval)

    def _do_callback(self, action, device: Device):
        for c in self._callbacks:
            if callable(c):
                c(action=action, serial=device.serial, node=f"/dev/{device.name}")

    def add_change_callback(self, callback):
        self._callbacks.append(callback)