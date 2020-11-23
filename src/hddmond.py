#!/usr/bin/python3.8
from injectable import load_injection_container, Autowired, autowired, inject

import sys
import os
import signal

# PACKAGE_PARENT = '..'
# SCRIPT_DIR = os.path.dirname(os.path.realpath(os.path.join(os.getcwd(), os.path.expanduser(__file__))))
# sys.path.append(os.path.normpath(os.path.join(SCRIPT_DIR, PACKAGE_PARENT)))

load_injection_container('./') #For the `injectable` module. Scans files for injectable items.


from hddmontools.task import Task, EraseTask, ImageTask
from hddmondtools.hddmanager import ListModel
from hddmondtools.websocket import WebsocketServer
from hddmondtools.hddmon_dataclasses import HddData, TaskData, TaskQueueData, ImageData
from hddmondtools.couchdb import CouchDatabase
from hddmontools.image import ImageManager, CustomerImage, DiskImage
from hddmontools.config_service import ConfigService


class App:
    def __init__(self):
        self.images = inject(ImageManager)
        self.list = ListModel(taskChangedCallback = self.task_changed_cb)
        
        self.ws = inject(WebsocketServer)
        
        self.ws.register_command(self.list.taskBySerial, 'addtask')
        self.ws.register_command(self.list.abortTaskBySerial, 'aborttask')
        self.ws.register_command(self.list.sendHdds, 'hdds')
        self.ws.register_command(self.list.modifyTaskQueue, 'modifyqueue')
        self.ws.register_command(self.list.pauseQueue, 'pausequeue')
        self.ws.register_command(self.list.blacklist, 'blacklist')
        self.ws.register_command(self.list.sendBlacklist, 'blacklisted')

    def ws_update(self, payload):
        self.ws.broadcast_data(payload)
    def image_shim(self, *args, **kw):
        imags = []
        for i in self.images.added_images:
            imags.append(ImageData.FromDiskImage(i))
        disc = []
        for i in self.images.discovered_images:
            disc.append(ImageData.FromDiskImage(i))
        return {'onboarded_images': imags, 'discovered_images': disc}
    def start(self):
        self.images.start()
        self.ws.start()
        self.list.start()
    def stop(self, *args, **kwargs):
        print("Stopping...")
        self.ws.stop()
        self.list.stop()
        self.images.stop()
    def task_changed_cb(self, payload):
        self.ws_update(payload)
        


if __name__ == '__main__':

    cfg_svc = inject(ConfigService)

    verbose = False
    def vprint(s: str):
        if verbose == True:
            print(s)

    import getopt, sys
    unixOptions = "hvw:r:A:p:U:P:"
    gnuOptions = ["help", "verbose", "wsport=", "rhdport=", "dbaddress=", "dbport=", "dbuser=", "dbpassword="]
    fullCmdArguments = sys.argv
    argumentList = fullCmdArguments[1:] #exclude the name
    arguments = None
    
    try:
        arguments, values = getopt.getopt(argumentList, unixOptions, gnuOptions)
    except getopt.error as err:
        print (str(err))
        sys.exit(2)
    if arguments != None:
        wsport = None
        rhdport = None
        dbaddress = None
        dbport = None
        dbuser = None
        dbpass = None

        for currentArgument, currentValue in arguments:
            if currentArgument in ("-v", "--verbose"):
                print("Verbose")
                verbose = True
            elif currentArgument in ("-h", "--help"):
                print("Let me help you,")
                print("Launch this program with at least the -d, -a, and -p commands to specify a disk, address, and port to connect to.")
                print("ex: , -a 127.0.0.1 -p 56567")
                print("Valid options: ")
                for op in gnuOptions:
                    print("--" + str(op))
                exit(0)
            elif currentArgument in ("-w", "--wsport"):
                wsport = str(currentValue).strip()
                vprint("Websocket port overridden to " + str(wsport))
            elif currentArgument in ("-r", "--rhdport"):
                rhdport = currentValue.strip()
                vprint("Remote HDD port overridden to {0}".format(rhdport))
            elif currentArgument in ("-A", "--dbaddress"):
                dbaddress = currentValue.strip()
                vprint("Database address overridden to {0}".format(dbaddress))
            elif currentArgument in ("-p", "--dbport"):
                dbport = currentValue.strip()
                vprint("Database port overridden to {0}".format(dbport))
            elif currentArgument in ("-U", "--dbuser"):
                dbuser = currentValue.strip()
                vprint(f"Database user overridden")
            elif currentArgument in ("-P", "--dbpassword"):
                dbpass = currentValue.strip()
                vprint(f"Database password overridden")

        if wsport != None:
            cfg_svc._data['websocket_host']['port'] = int(wsport)
        if rhdport != None:
            cfg_svc._data['hddmon_remote_host']['port'] = int(rhdport)
        if dbaddress != None:
            cfg_svc._data['couchdb']['address'] = str(dbaddress)
        if dbport != None:
            cfg_svc._data['couchdb']['port'] = int(dbport)
        if dbuser != None:
            cfg_svc._data['couchdb']['user'] = str(dbuser)
        if dbpass != None:
            cfg_svc._data['couchdb']['password'] = str(dbpass)


    app = App()
    signal.signal(signal.SIGINT, app.stop)
    signal.signal(signal.SIGQUIT, app.stop)
    signal.signal(signal.SIGTERM, app.stop)
    #signal.signal(signal.SIGKILL, app.stop) #We should let this kill the program instead of trying to handle it
    signal.signal(signal.SIGUSR1, app.stop)
    app.start()
    print("Done.")
    exit(0)