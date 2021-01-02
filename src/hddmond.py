#!/usr/bin/python3.8
from injectable import load_injection_container, Autowired, autowired, inject

import sys
import os
import signal
import asyncio
import logging

# PACKAGE_PARENT = '..'
# SCRIPT_DIR = os.path.dirname(os.path.realpath(os.path.join(os.getcwd(), os.path.expanduser(__file__))))
# sys.path.append(os.path.normpath(os.path.join(SCRIPT_DIR, PACKAGE_PARENT)))

load_injection_container('./') #For the `injectable` module. Scans files for injectable items.

from hddmondtools.hddmanager import ListModel
from hddmondtools.websocket import WebsocketServer
from hddmondtools.hddmon_dataclasses import ImageData
from hddmontools.image import ImageManager
from hddmontools.config_service import ConfigService

logger = logging.getLogger(__name__)
logger.setLevel(logging.DEBUG)

class App:
    def __init__(self):
        self.logger = logging.getLogger(__name__ + "." + self.__class__.__qualname__)
        self.logger.setLevel(logging.DEBUG)
        self.logger.info("Initializing application...")
        self.images = inject(ImageManager)
        self.list = ListModel(taskChangedCallback = self.task_changed_cb)
    
        self.ws = inject(WebsocketServer)
        self.ws.connect_instance(self.list) #All API functions are defined in ListModel

    async def ws_update(self, payload):
        self.logger.debug(f"Broadcasting data to websockets: {payload}")
        await self.ws.broadcast_data(payload)
        
    def image_shim(self, *args, **kw):
        imags = []
        for i in self.images.added_images:
            imags.append(ImageData.FromDiskImage(i))
        disc = []
        for i in self.images.discovered_images:
            disc.append(ImageData.FromDiskImage(i))
        return {'onboarded_images': imags, 'discovered_images': disc}

    async def start(self):
        self.logger.info("Starting application...")
        await self.images.start()
        await self.ws.start()
        await self.list.start()

    async def stop(self, *args, **kwargs):
        self.logger.info("Stopping application...")
        await self.ws.stop()
        await self.list.stop()
        await self.images.stop()
        
    def task_changed_cb(self, payload):
        loop = asyncio.get_event_loop()
        loop.create_task(self.ws_update(payload))
    


if __name__ == '__main__':
    logger.info("Executing file...")
    
    console_logfeed = logging.StreamHandler()
    general_formatter = logging.Formatter("%(asctime)s [%(levelname)s] %(name)s - %(message)s", "%Y-%m-%d %H:%M:%S")
    console_logfeed.setFormatter(general_formatter)
    console_logfeed.setLevel(logging.DEBUG)

    logger.addHandler(console_logfeed)

    cfg_svc = inject(ConfigService)

    verbose = False

    logger.debug("Using getopt, sys modules...")
    #TODO: Use argparse instead!
    import getopt, sys
    unixOptions = "hvw:r:A:p:U:P:"
    gnuOptions = ["help", "verbose", "wsport=", "rhdport=", "dbaddress=", "dbport=", "dbuser=", "dbpassword="]
    fullCmdArguments = sys.argv
    argumentList = fullCmdArguments[1:] #exclude the name
    arguments = None
    
    try:
        logger.debug("Parsing options...")
        arguments, values = getopt.getopt(argumentList, unixOptions, gnuOptions)
    except getopt.error as err:
        logger.error(f"Error while parsing options: {str(err)}")
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
                logger.debug("Using verbose...")
                verbose = True
            elif currentArgument in ("-h", "--help"):
                logger.debug("Showing help...")
                print("Let me help you,")
                print("Launch this program with at least the -d, -a, and -p commands to specify a disk, address, and port to connect to.")
                print("ex: , -a 127.0.0.1 -p 56567")
                print("Valid options: ")
                for op in gnuOptions:
                    print("--" + str(op))
                logger.info("Exiting after showing help...")
                exit(0)
            elif currentArgument in ("-w", "--wsport"):
                wsport = str(currentValue).strip()
                logger.debug("Websocket port overridden to " + str(wsport))
            elif currentArgument in ("-r", "--rhdport"):
                rhdport = currentValue.strip()
                logger.debug("Remote HDD port overridden to {0}".format(rhdport))
            elif currentArgument in ("-A", "--dbaddress"):
                dbaddress = currentValue.strip()
                logger.debug("Database address overridden to {0}".format(dbaddress))
            elif currentArgument in ("-p", "--dbport"):
                dbport = currentValue.strip()
                logger.debug("Database port overridden to {0}".format(dbport))
            elif currentArgument in ("-U", "--dbuser"):
                dbuser = currentValue.strip()
                logger.debug(f"Database user overridden")
            elif currentArgument in ("-P", "--dbpassword"):
                dbpass = currentValue.strip()
                logger.debug(f"Database password overridden")

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

    if not verbose:
        console_logfeed.setLevel(logging.INFO)

    app = App()
    
    logger.debug("Getting asyncio event loop...")
    loop = asyncio.get_event_loop()

    async def async_stop():
        logger.debug("Asking app to stop...")
        await app.stop()

    def async_is_over(*a, **kw):
        logger.debug("Stopping event loop...")
        asyncio.get_event_loop().stop()

    def stop_shim():
        logger.info("Got request to exit.")
        logger.debug("Scheduling application exit...")
        exit_task = asyncio.get_event_loop().create_task(async_stop(), name="exit_task")
        exit_task.add_done_callback(async_is_over)

    loop.add_signal_handler(signal.SIGINT, stop_shim)
    loop.add_signal_handler(signal.SIGQUIT, stop_shim)
    loop.add_signal_handler(signal.SIGTERM, stop_shim)
    #loop.add_signal_handler(signal.SIGKILL, stop_shim) #We should let this kill the program instead of trying to handle it
    loop.add_signal_handler(signal.SIGUSR1, stop_shim)

    loop.run_until_complete(app.start())
    loop.run_forever()

    logger.info("Done.")
    exit(0)