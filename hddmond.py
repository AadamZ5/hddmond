#!/usr/bin/python3.8
from hddmondtools.hddmanager import ListModel
from hddmondtools.websocket import WebsocketServer
from hddmondtools.multiproc_socket import MultiprocSock
from hddmondtools.hddmon_dataclasses import HddData, TaskData, TaskQueueData
import signal


class App:
    def __init__(self):
        self.list = ListModel(taskChangedCallback = self.task_changed_cb)
        self.mps = MultiprocSock()
        self.ws = WebsocketServer()

        self.mps.register_command('erase', self.list.eraseBySerial)
        self.mps.register_command('shorttest', self.list.shortTestBySerial)
        self.mps.register_command('longtest', self.list.longTestBySerial)
        self.mps.register_command('aborttest', self.list.abortTestBySerial)
        self.mps.register_command('getimages', self.list.sendImages)
        self.mps.register_command('image', self.list.imageBySerial)
        self.mps.register_command('aborttask', self.list.abortTaskBySerial)
        self.mps.register_command('hdds', self.list.sendHdds)
        self.mps.register_command('modifyqueue', self.list.modifyTaskQueue)
        self.mps.register_command('pausequeue', self.list.pauseQueue)
        self.mps.register_command('blacklist', self.list.blacklist)
        
        self.ws.register_command('erase', self.list.eraseBySerial)
        self.ws.register_command('shorttest', self.list.shortTestBySerial)
        self.ws.register_command('longtest', self.list.longTestBySerial)
        self.ws.register_command('aborttest', self.list.abortTestBySerial)
        self.ws.register_command('getimages', self.list.sendImages)
        self.ws.register_command('image', self.list.imageBySerial)
        self.ws.register_command('aborttask', self.list.abortTaskBySerial)
        self.ws.register_command('hdds', self.list.sendHdds)
        self.ws.register_command('modifyqueue', self.list.modifyTaskQueue)
        self.ws.register_command('pausequeue', self.list.pauseQueue)
        self.ws.register_command('blacklist', self.list.blacklist)

    def ws_update(self, payload):
        self.ws.broadcast_data(payload)

    def start(self):
        self.mps.start()
        self.ws.start()
        self.list.start()

    def stop(self, *args, **kwargs):
        print("Stopping...")
        self.mps.stop()
        self.ws.stop()
        self.list.stop()

    def task_changed_cb(self, payload):
        self.mps.broadcast_data(payload)
        self.ws_update(payload)
        


if __name__ == '__main__':
    app = App()
    signal.signal(signal.SIGINT, app.stop)
    signal.signal(signal.SIGQUIT, app.stop)
    signal.signal(signal.SIGTERM, app.stop)
    #signal.signal(signal.SIGKILL, app.stop) #We should let this kill the program instead of trying to handle it
    signal.signal(signal.SIGUSR1, app.stop)
    app.start()
    exit(0)