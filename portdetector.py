#!/usr/bin/python3

import sys
import os
import hdd
import datetime
import pyudev
from portdetection import PortDetection
import subprocess

#Udev should call this with $kernal and $devpath variables which will give us the drive name, and its device path. 
devname = str(sys.argv[1])
devpath = str(sys.argv[2])

symlink = "/dev/" + devname
syspath = "/sys" + devpath
serial = ""


fd = open("./portdetector.log", mode="a")
fd.write("===========Port detector init at " + str(datetime.datetime.now()) + " ===========\n")
fd.write("Params = " + str(sys.argv) + "\n")
fd.close()


try:
    srl = subprocess.run(["lsblk", "--nodeps", "-no", "serial", symlink], stdout=subprocess.PIPE, stdin=subprocess.PIPE, stderr=subprocess.PIPE, universal_newlines=True)
    if srl.returncode == 0:
        s = str(srl.stdout)
        serial = s.strip().replace('-', '')
    else:
        fd = open("./portdetector.log", mode="a")
        fd.write("SUBPROCESS FAILURE (" + str(datetime.datetime.now()) + ")")
        fd.write("STDOUT: " + str(srl.stdout) + "\n")
        fd.write("STDERR: " + str(srl.stderr) + "\n")
        fd.write("\n")
        fd.close()
        exit(2) #subprocess failed
except Exception as e:
    fd = open("./portdetector.log", mode="a")
    fd.write("SUBPROCESS EXCEPTION RAISED (" + str(datetime.datetime.now()) + ")")
    fd.write(str(e) + "\n")
    fd.write("\n")
    fd.close()
    exit(2) #subprocess failed

#Udev will expect "parts" from the output of this program.
#Each part is just a single word, and parts are separated by a single space. http://www.reactivated.net/writing_udev_rules.html#external-naming

pd = PortDetection()

pci = pd.GetPci(syspath)

port = pd.GetPort(syspath, pci, serial)

newname = str()

if port == None:
    fd = open("./portdetector.log", mode="a")
    fd.write("Couldn't find port for " + symlink + "!\n")
    fd.write("PCI: " + str(pci) + ", Serial: " + serial + ", Syspath: " + syspath + "\n")
    fd.write("SAS devices: " + str(pd.sasdet.SasDevices))
    fd.write("\n")
    fd.close()
    exit(1) #Couldn't find the port
else:
    newname = port

print(newname) #Output this to stdout
exit(0)


