#!/usr/bin/python3.8
import os, sys
import signal

PACKAGE_PARENT = '..'
SCRIPT_DIR = os.path.dirname(os.path.realpath(os.path.join(os.getcwd(), os.path.expanduser(__file__))))
sys.path.append(os.path.normpath(os.path.join(SCRIPT_DIR, PACKAGE_PARENT)))

from injectable import load_injection_container, inject, InjectionContainer
load_injection_container() #For the `injectable` module. Scans files for injectable items.

from lib.hdd import Hdd
from lib.task_service import TaskService
from lib.task import Task
from lib.hdd_remote import HddRemoteHost
from lib.hdd_test_interface import HddTestInterface
import time
class LocalInstance:

    def __init__(self, test_interface = False, *a, **kw):
        self.server_address = kw.get('address', ('127.0.0.1', 56567))
        # authkey = kw.get('authkey', None)

        # if(authkey == None):
        #     #print("WARNING! No authkey was supplied!")
        #     authkey = b''
        # else:
        #     authkey = bytearray(authkey, 'ascii')

        task_svc = TaskService()

        self.node = kw.get('node', None)
        if(test_interface == True):
            print("Instantiating test interface...")
            self.hdd = HddTestInterface(mock_node=self.node)
        else:
            self.hdd = Hdd(self.node)
        self.hdd.add_task_changed_callback(self.tc_c)
        
    
    def tc_c(self, *a, **kw):
        print(str(a))
        print(str(kw))

    def start(self, *a, **kw):
        self.hdd_wrapper = HddRemoteHost(self.hdd, self.server_address)
        self.hdd_wrapper.messenger._server_loop_thread.join() 

    def stop(self, *a, **kw):
        self.hdd_wrapper.stop()

if __name__ == "__main__":

    verbose = False
    def vprint(s: str):
        if verbose == True:
            print(s)

    import getopt, sys
    unixOptions = "hd:va:p:t"
    gnuOptions = ["help", "disk=", "verbose", "address=", "port=", "test"]
    fullCmdArguments = sys.argv
    argumentList = fullCmdArguments[1:] #exclude the name
    arguments = None
    
    try:
        arguments, values = getopt.getopt(argumentList, unixOptions, gnuOptions)
    except getopt.error as err:
        print (str(err))
        sys.exit(2)
    if arguments != None:
        disk = None
        address = None
        port = None
        authkey = None
        test = False

    for currentArgument, currentValue in arguments:
        if currentArgument in ("-v", "--verbose"):
            print("Verbose")
            verbose = True
        elif currentArgument in ("-h", "--help"):
            print("Let me help you,")
            print("Launch this program with at least the -d, -a, and -p commands to specify a disk, address, and port to connect to.")
            print("ex: -d /dev/sda, -a 127.0.0.1 -p 56567")
            print("Valid options: ")
            for op in gnuOptions:
                print("--" + str(op))
            exit(0)
        elif currentArgument in ("-d", "--disk"):
            disk = str(currentValue).strip()
            vprint("Looking at disk " + str(disk))
        elif currentArgument in ("-a", "--address"):
            address = currentValue.strip()
            vprint("Working with address {0}".format(address))
        elif currentArgument in ("-p", "--port"):
            port = currentValue.strip()
            vprint("Working with port {0}".format(port))
        elif currentArgument in ("-t", "--test"):
            test = True
            vprint("Using test interface")
            
    l_inst = LocalInstance(address=(address, int(port)), authkey=authkey, node=disk, test_interface=test)
    signal.signal(signal.SIGINT, l_inst.stop)
    signal.signal(signal.SIGQUIT, l_inst.stop)
    signal.signal(signal.SIGTERM, l_inst.stop)
    #signal.signal(signal.SIGKILL, l_inst.stop) #We should let this kill the program instead of trying to handle it
    signal.signal(signal.SIGUSR1, l_inst.stop)
    l_inst.start()


