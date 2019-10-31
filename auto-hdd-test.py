#!/usr/bin/python3
import os
import subprocess
import pyudev
from pySMART import Device
import re
import npyscreen

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
monitor.filter_by(subsystem='usb')



def TestHdd(device : pyudev.Device):
    print(device.device_node)
    



udevObserver = pyudev.MonitorObserver(monitor, callback=TestHdd)
udevObserver.start()


# This application class serves as a wrapper for the initialization of curses
# and also manages the actual forms of the application

class MyTestApp(npyscreen.NPSAppManaged):
    def onStart(self):
        self.registerForm("MAIN", MainForm())

# This form class defines the display that will be presented to the user.



class myEmployeeForm(npyscreen.Form):
    def afterEditing(self):
        self.parentApp.setNextForm(None)
        
    def create(self):
        self.myName        = self.add(npyscreen.TitleText, name='Name')
        self.myDepartment = self.add(npyscreen.TitleSelectOne, scroll_exit=True, max_height=3, name='Department', values = ['Department 1', 'Department 2', 'Department 3'])
        self.myDate        = self.add(npyscreen.TitleDateCombo, name='Date Employed')

class MyApplication(npyscreen.NPSAppManaged):
    def onStart(self):
        self.addForm('MAIN', myEmployeeForm, name='New Employee')

if __name__ == '__main__':
    TestApp = MyApplication().run()
