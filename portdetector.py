#!/usr/bin/python3

import sys
import os
import hdd
import datetime
import pyudev
from portdetection import PortDetection

#Udev should call this with its variable %k which will be the drive name in kernal.
devname = str(sys.argv[1])
symlink = "/dev/" + devname
#symlink = devname

fd = open("./log", mode="a")
fd.write("Params = " + str(sys.argv) + "\n")
fd.close()

c = pyudev.Context()

pyudev

try:
    pass
except Exception as e:
    fd = open("./log", mode="a")
    fd.write("HDD CREATE FAILURE (" + str(datetime.datetime.now()) + ") kernal passed: " + devname + " symlink: " + symlink + "\n")
    fd.write(str(e) + "\n")
    fd.write("\n")
    fd.close()
    exit(2) #Not a valid hdd

#Udev will expect "parts" from the output of this program.
#Each part is just a single word, and parts are separated by a single space. http://www.reactivated.net/writing_udev_rules.html#external-naming

pd = PortDetection()

port = pd.GetPort(hdd._udev.sys_path, pd.GetPci(hdd._udev.sys_path), hdd.serial)

newname = str()

if port == None:
    exit(1) #Couldn't find the port
else:
    newname = port

print(newname) #Output this to stdout
exit(0)


