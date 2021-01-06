#!/usr/bin/python3.8

import sys
import signal
import asyncio
import logging
import logging.handlers
import datetime

from injectable import load_injection_container, inject
load_injection_container('./') #For the `injectable` module. Scans files for injectable items.
from pathlib import Path
from os import makedirs

from hddmondtools.application import App
from hddmontools.config_service import ConfigService

root_logger = logging.getLogger()
logger = logging.getLogger("Bootstrapper")
logger.setLevel(logging.DEBUG)

if __name__ == '__main__':
    logger.info("Executing file...")
    log_path = Path('logs').resolve()
    console_logfeed = logging.StreamHandler()
    makedirs(log_path, 0x755, True)
    file_logfeed = logging.handlers.RotatingFileHandler(str(log_path / (str(datetime.datetime.now().isoformat(sep="_", timespec='seconds')) + '.log')), backupCount=5, maxBytes=500000000, delay=True)
    slim_formatter = logging.Formatter("%(asctime)s [%(levelname)s] - %(message)s", "%Y-%m-%d %H:%M:%S")
    general_formatter = logging.Formatter("%(asctime)s [%(levelname)s] %(name)s - %(message)s", "%Y-%m-%d %H:%M:%S")
    verbose_formatter = logging.Formatter("%(asctime)s [%(levelname)s] %(name)s in %(filename)s:%(lineno)d - %(message)s", "%Y-%m-%d %H:%M:%S")
    console_logfeed.setFormatter(general_formatter)
    console_logfeed.setLevel(logging.INFO)
    file_logfeed.setFormatter(verbose_formatter)
    file_logfeed.setLevel(logging.DEBUG)

    root_logger.addHandler(console_logfeed)
    root_logger.addHandler(file_logfeed)

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
                console_logfeed.setFormatter(verbose_formatter)
                console_logfeed.setLevel(logging.DEBUG)
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