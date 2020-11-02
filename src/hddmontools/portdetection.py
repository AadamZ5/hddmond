#!/usr/bin/python3

from .ahcidetection import *
from .sasdetection import *
import subprocess
from .pciaddress import PciAddress
from injectable import injectable

@injectable(singleton=True)
class PortDetection():
    def __init__(self):
        self.ahcidet = AhciDetective()
        self.sasdet = SasDetective()

        lspci = subprocess.run(['lspci'], stdout=subprocess.PIPE, stderr=subprocess.PIPE, universal_newlines=True)
        lines = str(lspci.stdout).splitlines()

        pcisToParse = []

        for line in lines:
            if "PCI bridge" in line:
                pcisToParse.append(line.split()[0])
        
        self.blacklistPcis = []
        for p in pcisToParse:
            self.blacklistPcis.append(PciAddress.ParseAddr(p))

    def Update(self):
        self.ahcidet.Update()
        self.sasdet.Update()
        
    def GetPci(self, syspath):
        cols = syspath.split('/')
        check = cols[4]
        #print(check)
        pci = PciAddress.ParseAddr(check)
        if(pci in self.blacklistPcis):
            pci = PciAddress.ParseAddr(cols[5])
        return pci

    def GetPort(self, syspath, pci, serial):
        p = self.ahcidet.GetPortFromSysPath(syspath)
        if p != None:
            #print("Setting port to " + str(p))
            return p
        
        p = self.sasdet.GetDevicePort(pci, serial)
        if p != None:
            #print("Setting port to sas" + str(p))
            return "sas" + str(p)

        return None

if __name__ == "__main__":
    verbose = False
    def vprint(s: str):
        if verbose == True:
            print(s)

    import getopt, sys
    unixOptions = "hd:s:v"
    gnuOptions = ["help", "disk=", "syspath=", "verbose"]
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
        syspath = None
        serial = None
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
                print("Looking at disk " + str(disk))
            elif currentArgument in ("-s", "--syspath"):
                syspath = currentValue
                print("Working with syspath ")
        
        if disk != None:
            
            try:
                vprint("Getting serial...")
                srl = subprocess.run(["lsblk", "--nodeps", "-no", "serial", disk], stdout=subprocess.PIPE, stdin=subprocess.PIPE, stderr=subprocess.PIPE, universal_newlines=True)
                if srl.returncode == 0:
                    s = str(srl.stdout)
                    serial = s.strip().replace('-', '')
                    vprint("Got serial as " + str(serial))
            except Exception as e:
                print("Error: " + str(e))
                exit(2)

            if(syspath == None):
                vprint("Syspath not specified, using udev to obtain...")
                import pyudev
                try:
                    context = pyudev.Context()
                    d = pyudev.Devices.from_device_file(context, disk)
                    syspath = d.sys_path
                    vprint("Got syspath as " + str(syspath))
                except Exception as e:
                    print("Error" + str(e))
                    exit(3)

            if(serial != None):
                pd = PortDetection()
                pci = pd.GetPci(syspath)
                vprint("Got PCI address as " + str(pci))
                vprint("ata PCI: " + str(pd.ahcidet.AhciDevice.PciAddress))
                vprint("sas PCI: " + str(pd.sasdet.SasDevices[0].PciAddress))
                port = pd.GetPort(syspath, pci, serial)
                print("Result port: " + str(port))
                exit(0)
        else:
            print("Error, no disk specified.")
            exit(1)
            
    else:
        print("Error, no disk specified. Use -h for help.")
        exit(1)
