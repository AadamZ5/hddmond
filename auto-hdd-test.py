#!/usr/bin/python3
import os
import subprocess
import pyudev
from pySMART import Device
import re

print("Hello world!")

bootPartNode = subprocess.Popen("df -h | grep '/$' | sed 's/\\(^\\/dev\\/\\w*\\).*/\\1/'", shell=True, stdout=subprocess.PIPE).stdout.read() #Thanks https://askubuntu.com/questions/542351/determine-boot-disk
bootPartNode = bootPartNode.decode().rstrip()
print("Boot partition is " + bootPartNode)
bootDiskNode = re.sub(r'[0-9]+', '', bootPartNode)
print("Boot disk is " + bootDiskNode)

context = pyudev.Context()
for device in context.list_devices(subsystem='block'):
    print(device.device_node, end="")
    if(device.device_node == bootDiskNode):
        print("  BOOT DISK")
    elif(device.device_node == bootPartNode):
        print(" BOOT PART")
    else:
        print()

print("Monitoring UDEV events...")
monitor = pyudev.Monitor.from_netlink(context)
monitor.filter_by(subsystem='block')



def TestHdd(device : pyudev.Device):
    print(device.device_node)
    

udevObserver = pyudev.MonitorObserver(monitor, callback=TestHdd)



exit()