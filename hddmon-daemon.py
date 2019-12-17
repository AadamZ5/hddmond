#!/usr/bin/python3
import os
import subprocess
import multiprocessing.connection as ipc
import proc.core
import pyudev
from pySMART import Device
import re
import urwid as ui
from hdd import Hdd
import pySMART
import time
import threading
import sasdetection
import portdetection

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

debug = False
def logwrite(s:str, endl='\n'):
    if debug:
        fd = open("./main.log", 'a')
        fd.write(s)
        fd.write(endl)
        fd.close()

class ListModel:
    """
    Data model that holds hdd list and widgets.
    """


    def __init__(self):
        self.updateInterval = 3
        self.hdds = []
        self.monitor = pyudev.Monitor.from_netlink(context)
        self.monitor.filter_by(subsystem='block', device_type='disk')
        self.observer = pyudev.MonitorObserver(self.monitor, self.deviceAdded)
        self.observer.start()
        self.PortDetector = portdetection.PortDetection()
        self.updateDevices(bootDiskNode)
        self._loopgo = True
        self.stuffRunning = False
        self.updateThread = threading.Thread(target=self.updateLoop)

        self.serverAddress = ('localhost', 63962)
        self.server = ipc.Listener(address=self.serverAddress, authkey=b'H4789HJF394615R3DFESZFEZCDLPOQ')
        self.serverThread = threading.Thread(target=self.serverLoop)

        self.clientlist = [] #list of (client, addr)
        

    def eraseBySerial(self, serials = []):
        for s in serials:
            for h in self.hdds:
                if h.serial == s:
                    h.Erase()
                    break;

        return True

    def shortTestBySerial(self, serials = []):
        for s in serials:
            for h in self.hdds:
                if h.serial == s:
                    h.ShortTest()
                    break;

        return True

    def longTestBySerial(self, serials = []):
        for s in serials:
            for h in self.hdds:
                if h.serial == s:
                    h.LongTest()
                    break;

        return True

    def abortTestBySerial(self, serials = []):
        for s in serials:
            for h in self.hdds:
                if h.serial == s:
                    h.AbortTest()
                    break;

        return True

    def imageBySerial(self, serials = [], image=None):
        pass
        return False

    def serverLoop(self):
        while self._loopgo:
            client = self.server.accept()
            clientAddress = str(self.server.last_accepted)
            print("Connection from" + clientAddress)
            #should recieve a tuple with the following:
            #(command, data)
            #ie:
            #('erase', [Serial1, Serial2, Serial3])
            newClientThread = threading.Thread(target=self.listenToClient, kwargs={'client': client})
            self.clientlist.append((client, clientAddress, newClientThread))
            newClientThread.start()

    def listenToClient(self, client=None):
        print("Stemmed client into seperate thread")
        futuremsg = None
        while 'client' in locals():
            if(futuremsg):
                msg = futuremsg
                futuremsg = None
            else:
                try:
                    print("Waiting for msg")
                    msg = client.recv()#blocking call
                except EOFError as e:
                    print("Pipe unexpectedly closed:\n" + str(e))
                    msg = None
                    del client
                    break
                
            print("Got message: " + str(msg))
            if(type(msg) == tuple):
                command = ''
                readCmd = True
                try:
                    command = msg[0]
                    data = msg[1]
                except Exception as e:
                    print("Error while retrieving data from tuple in client message.\n" + str(e))
                    readCmd = False

                print(str(client) + ": " + str(command) + ", " + str(data))
                
                if readCmd:
                    if command == '':
                        client.send('error')

                    elif command == 'erase':
                        if(self.eraseBySerial(data)):
                            client.send('success')
                        else:
                            client.send('error')

                    elif command == 'shorttest':
                        if(self.shortTestBySerial(data)):
                            client.send('success')
                        else:
                            client.send('error')

                    elif command == 'longtest':
                        if(self.longTestBySerial(data)):
                            client.send('success')
                        else:
                            client.send('error')

                    elif command == 'aborttest':
                        if(self.abortTestBySerial(data)):
                            client.send('success')
                        else:
                            client.send('error')

                    elif command == 'image':
                        pass #Complicated logic response
                    elif command == 'listen':
                        while True:
                            client.send(list(self.hdds))
                            try:
                                lmsg = client.recv()#blocking call
                            except EOFError as e:
                                print("Pipe unexpectedly closed:\n" + str(e))
                                lmsg = None
                                del client
                                break

                            if(lmsg != 'again'):
                                futuremsg = lmsg
                                break
                            else:
                                time.sleep(1)

                    else:
                        pass #Unknown command
            else:
                pass #Message wasn't a tuple
        print("Client connection ended")
            


    def stop(self):
        self._loopgo = False
        self.updateThread.join()

    def ShortTest(self, button=None):
        for hw in self.hddEntries:
            if(hw.checked):
                hw.ShortTest()

    def LongTest(self, button=None):
        for hw in self.hddEntries:
            if(hw.checked):
                hw.LongTest()
        
    def AbortTest(self, button=None):
        for hw in self.hddEntries:
            if(hw.checked):
                hw.AbortTest()

    def EraseDisk(self, button=None):
        for hw in self.hddEntries:
            if(hw.checked):
                hw.Erase()

    def updateLoop(self):
        '''
        This loop should be run in a separate thread.
        '''
        while self._loopgo:
            busy = False
            for hdd in self.hdds:
                if(hdd.status == Hdd.STATUS_LONGTST) or (hdd.status == Hdd.STATUS_TESTING): #If we're testing, queue the smart data to update the progress
                    try:
                        hdd.UpdateSmart()
                    except Exception as e:
                        logwrite("Exception raised!:" + str(e))
                    busy = True
                if(hdd.CurrentTaskStatus != Hdd.TASK_NONE): #If there is a task operating on the drive's data
                    try:
                        hdd.UpdateTask()
                    except Exception as e:
                        logwrite("Exception raised!:" + str(e))
                    busy = True
                hdd.refresh()
            self.stuffRunning = busy
            time.sleep(5)

    def updateDevices(self, bootNode: str):
        """
        Checks the system's existing device list and gatheres already connected hdds.
        """
        #This should be run at the beginning of the program
        #Check to see if this device path already exists in our application.
        print(pySMART.DeviceList().devices)
        for d in pySMART.DeviceList().devices:
            
            notFound = True
            if("/dev/" + d.name == bootNode): #Check if this is our boot drive.
                notFound = False

            for hdd in self.hdds:
                print("Testing: /dev/" + d.name + " == " + hdd.node)
                if(hdd.node == "/dev/" + d.name) : #This device path exists. Do not add it.
                    notFound = False
                    break
            
            if(notFound): #If we didn't find it already in our list, go ahead and add it.
                h = Hdd.FromSmartDevice(d)
                h.OnPciAddress = self.PortDetector.GetPci(h._udev.sys_path)
                h.Port = self.PortDetector.GetPort(h._udev.sys_path, h.OnPciAddress, h.serial)
                self.addHdd(h)
                print("Added /dev/"+d.name)
        print("Added existing devices")

            
    def addHdd(self, hdd: Hdd):
        hdd.CurrentTask = self.findProcAssociated(hdd.node)
        self.hdds.append(hdd)
        #hddWdget.ShortTest()

    def removeHddHdd(self, hdd: Hdd):
        for h in self.hdds.keys():
            if (h.node == hdd.node):
                removeWidget = self.hdds[h]
                try:
                    del self.hdds[h]
                except KeyError as e:
                    pass
                self.hddEntries.remove(removeWidget)
                break
    
    def removeHddStr(self, node: str):
        for h in self.hdds.keys():
            if (h.node == node):
                removeWidget = self.hdds[h]
                try:
                    del self.hdds[h]
                except KeyError as e:
                    pass
                self.hddEntries.remove(removeWidget)
                break

    def deviceAdded(self, action, device: pyudev.Device):
        if(self._forked == True):
            return
        if(action == 'add') and (device != None):
            hdd = Hdd.FromUdevDevice(device)
            self.PortDetector.Update()
            hdd.OnPciAddress = self.PortDetector.GetPci(hdd._udev.sys_path)
            hdd.Port = self.PortDetector.GetPort(hdd._udev.sys_path, hdd.OnPciAddress, hdd.serial)
            self.addHdd(hdd)
        elif(action == 'remove') and (device != None):
            self.removeHddStr(device.device_node)

    def findProcAssociated(self, node):
        plist = proc.core.find_processes()
        for p in plist:
            if node in p.cmdline:
                return p
        return None

    def start(self):
        self.serverThread.start()
        print("Server running")
        self.updateThread.start()
        print("Update thread running")

if __name__ == '__main__':
    hd = ListModel()
    hd.start()