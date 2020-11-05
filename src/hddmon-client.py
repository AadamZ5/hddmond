#!/usr/bin/python3.8
import os, sys

PACKAGE_PARENT = '..'
SCRIPT_DIR = os.path.dirname(os.path.realpath(os.path.join(os.getcwd(), os.path.expanduser(__file__))))
sys.path.append(os.path.normpath(os.path.join(SCRIPT_DIR, PACKAGE_PARENT)))

from injectable import load_injection_container
load_injection_container('./') #For the `injectable` module. Scans files for injectable items.

from hddmontools.hdd import Hdd
from hddmontools.hdd_remote import HddRemoteHost
import time
class LocalInstance:

    def __init__(self, *a, **kw):
        self.server_address = kw.get('address', ('127.0.0.1', 56567))
        authkey = kw.get('authkey', None)

        if(authkey == None):
            print("WARNING! No authkey was supplied!")
            authkey = b''
        else:
            authkey = bytearray(authkey, 'ascii')

        self.node = kw.get('node', None)
        self.hdd = Hdd(self.node)
        self.hdd_wrapper = HddRemoteHost(self.hdd, self.server_address)
        self.hdd_wrapper.messenger._server_loop_thread.join() 

if __name__ == "__main__":
    verbose = False
    def vprint(s: str):
        if verbose == True:
            print(s)

    import getopt, sys
    unixOptions = "hd:va:p:A:"
    gnuOptions = ["help", "disk=", "verbose", "address=", "port=", "authkey="]
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

    for currentArgument, currentValue in arguments:
        if currentArgument in ("-v", "--verbose"):
            print("Verbose")
            verbose = True
        elif currentArgument in ("-h", "--help"):
            print("Let me help you,")
            print("Launch this program with at least the -d command to specify a disk")
            print("ex: -d /dev/sda")
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
        elif currentArgument in ("-A", "--authkey"):
            authkey = currentValue.strip()
            vprint("Working with specified authkey")
            
    l_inst = LocalInstance(address=(address, int(port)), authkey=authkey, node=disk)


