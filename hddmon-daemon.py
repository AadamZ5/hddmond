#!/usr/bin/python3
import os, sys
os.chdir('/etc/hddmon')
sys.path.append('/etc/hddmon')
import subprocess
import multiprocessing.connection as ipc
import proc.core
import pyudev
from pySMART import Device
import re
from hddmontools.hdd import Hdd, HealthStatus, TaskStatus
from hddmontools.task import ExternalTask
from hddmontools.image import DiskImage, Partition
import pySMART
import time
import threading
import hddmontools.sasdetection
import hddmontools.portdetection
import signal
from socket import timeout
import graphqlclient
import websockets

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

class WebsocketServer:

    def __init__(self):
        pass

    def webserver_loop(self):
        pass

class ListModel:
    """
    Data model that holds hdd list.
    """

    def __init__(self):
        self.updateInterval = 3
        self.hdds = []
        self.images = []
        self.monitor = pyudev.Monitor.from_netlink(context)
        self.monitor.filter_by(subsystem='block', device_type='disk')
        self.PortDetector = hddmontools.portdetection.PortDetection()
        self.AutoShortTest = False
        self.updateDevices(bootDiskNode)
        self.loadDiskImages()
        self._loopgo = True
        self.stuffRunning = False
        self.updateThread = threading.Thread(target=self.updateLoop, name="HddUpdateThread")
        self.gclient = graphqlclient.GraphQLClient('http://172.23.2.202:4000')
        
        self.serverAddress = ('localhost', 63963) #63962 for stable, 63963 for testing

        self.clientlist = [] #list of (client, addr)
        

    def eraseBySerial(self, serials = []): #Starts an erase operation on the drives matching the input serials
        r = False
        l = threading.Lock()
        l.acquire()
        for s in serials:
            for h in self.hdds:
                if h.serial == s:
                    r = h.Erase()
                    if r == True:
                        print("Started erase on " + str(h.serial) + " with PID " + str(h.CurrentTask.PID))
                    else:
                        print("Couldn't start erase on " + str(h.serial))
                    break;
        l.release()
        return r

    def shortTestBySerial(self, serials = []): #Starts a short test on the drives matching the input serials
        l = threading.Lock()
        l.acquire()
        for s in serials:
            for h in self.hdds:
                if h.serial == s:
                    h.ShortTest()
                    break;
        l.release()
        return True

    def longTestBySerial(self, serials = []): #Starts a long test on the drives matching the input serials
        l = threading.Lock()
        l.acquire()
        for s in serials:
            for h in self.hdds:
                if h.serial == s:
                    h.LongTest()
                    break;
        l.release()
        return True

    def abortTestBySerial(self, serials = []): #Stops a test on the drives matching the input serials
        l = threading.Lock()
        l.acquire()
        for s in serials:
            for h in self.hdds:
                if h.serial == s:
                    h.AbortTest()
                    break;
        l.release()
        return True

    def imageBySerial(self, serials = [], image=None): #applies an image on the drives matching the input serials
        l = threading.Lock()
        l.acquire()
        im = None
        for i in self.images:
            if str(image) == i.name:
                im = i
                break

        if im == None:
            print("Couldn't find image " + str(image))
            return False

        for s in serials:
            for h in self.hdds:
                if h.serial == s:
                    print("Starting image on " + h.serial + " with image " + im.name)
                    h.Image(im)
                    break
        l.release()
        return True

    def serverLoop(self):
        print("Server running")
        while self._loopgo:
            try:
                client = self.server.accept()
            except timeout as e:
                #print("Listen wait timeout: " + str(e))
                client = None
            except Exception as e:
                print("An exception occurred while listening for clients: " + str(e))
                client = None

            if client != None:
                clientAddress = str(self.server.last_accepted)
                print("Connection from" + clientAddress)
                #should recieve a tuple with the following:
                #(command, data)
                #ie:
                #('erase', [Serial1, Serial2, Serial3])
                newClientThread = threading.Thread(target=self.client_loop, kwargs={'client': client})
                self.clientlist.append((client, clientAddress, newClientThread))
                newClientThread.start()

        print("Server loop stopped")

    def websocket_loop(self):
        pass

    def client_loop(self, client=None):
        print("Split client into seperate thread")
        futuremsg = None
        while ('client' in locals()) and self._loopgo:
            if(futuremsg):
                msg = futuremsg
                futuremsg = None
            else:
                try:
                    #print("Waiting for msg")
                    msg = client.recv()#blocking call
                except EOFError as e:
                    print("Pipe unexpectedly closed:\n" + str(e))
                    msg = None
                    del client
                    break
                
            #print("Got message: " + str(msg))
            if(type(msg) == tuple):
                command = ''
                readCmd = True
                try:
                    command = msg[0]
                    data = msg[1]
                except Exception as e:
                    print("Error while retrieving data from tuple in client message.\n" + str(e))
                    readCmd = False

                #print(str(client) + ": " + str(command) + ", " + str(data))
                
                if readCmd:
                    if command == '':
                        client.send('error')

                    elif command == 'erase':
                        if(self.eraseBySerial(data)):
                            client.send(('success', command))
                        else:
                            client.send('error')

                    elif command == 'shorttest':
                        if(self.shortTestBySerial(data)):
                            client.send(('success', command))
                        else:
                            client.send('error')

                    elif command == 'longtest':
                        if(self.longTestBySerial(data)):
                            client.send(('success', command))
                        else:
                            client.send('error')

                    elif command == 'aborttest':
                        if(self.abortTestBySerial(data)):
                            client.send(('success', command))
                        else:
                            client.send('error')

                    elif command == 'getimages':
                        client.send(('images', self.images))

                    elif 'image' in command and not command == 'getimages':
                        image = command.split()[1]
                        if(self.imageBySerial(data, image)):
                            client.send(('success', command))
                        else:
                            client.send('error')
                    elif command == 'listen':
                        #print("Sent: " + str(self.hdds))
                        if(len(self.hdds) == 0):
                            client.send(None)
                        else:
                            client.send(('hdds', self.hdds))

                    else:
                        client.send('error')
                        pass #Unknown command
            else:
                pass #Message wasn't a tuple
        print("Client connection ended")

    def updateLoop(self):
        '''
        This loop should be run in a separate thread. Good luck not doing that.
        '''
        print("Update thread running")
        smart_coldcall_interval = 30.0 #seconds
        while self._loopgo:
            busy = False
            for hdd in self.hdds:
                if not (hdd.status == HealthStatus.LongTesting) or (hdd.status == HealthStatus.ShortTesting):
                    if(time.time() - hdd._smart_last_call > smart_coldcall_interval): #If we're not testing, occasionally check to see if a test was started externally.
                        print("smart cold-call to " + str(hdd.serial))
                        try:
                            hdd.UpdateSmart()
                            hdd._smart_last_call = time.time()
                        except Exception as e:
                            logwrite("Exception raised!:" + str(e))
                            print("Exception raised!:" + str(e))
                if(hdd.CurrentTaskStatus != TaskStatus.Idle): #If there is a task operating on the drive's data
                    busy = True
                else:
                    task = self.findProcAssociated(hdd.name)
                    if(task != None):
                        hdd.CurrentTask = ExternalTask(task.pid, processExitCallback=hdd._taskCompletedCallback)
                        hdd.CurrentTaskStatus = TaskStatus.External
                hdd.refresh()
            self.stuffRunning = busy
            time.sleep(1)

    def updateDevices(self, bootNode: str):
        """
        Checks the system's existing device list and gatheres already connected hdds.
        """
        #This should be run at the beginning of the program, or only if the hdd array is cleared.
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
        t = self.findProcAssociated(hdd.name)
        if(t != None):
            hdd.CurrentTask = ExternalTask(t.pid, processExitCallback=hdd._taskCompletedCallback)
            hdd.CurrentTaskStatus = TaskStatus.External
        hdd.refresh()
        self.hdds.append(hdd)
        if(self.AutoShortTest == True) and (hdd.status != HealthStatus.ShortTesting and hdd.status != HealthStatus.LongTesting):
            hdd.ShortTest()

    def removeHddHdd(self, hdd: Hdd):
        self.removeHddStr(hdd.node)
    
    def removeHddStr(self, node: str):
        for h in self.hdds:
            if (h.node == node):
                try:
                    self.hdds.remove(h)
                except KeyError as e:
                    print("Error removing hdd by node!:\n" + str(e))
                break

    def deviceAdded(self, action, device: pyudev.Device):
        print("Udev: " + str(action) + " " + str(device))
        if(action == 'add') and (device != None):
            hdd = Hdd.FromUdevDevice(device)
            self.PortDetector.Update()
            hdd.OnPciAddress = self.PortDetector.GetPci(hdd._udev.sys_path)
            hdd.Port = self.PortDetector.GetPort(hdd._udev.sys_path, hdd.OnPciAddress, hdd.serial)
            self.addHdd(hdd)
        elif(action == 'remove') and (device != None):
            self.removeHddStr(device.device_node)

    def findProcAssociated(self, name):
        #print("Looking for " + str(name) + " in process cmdline list...")
        plist = proc.core.find_processes()
        for p in plist:
            for cmdlet in p.cmdline:
                if name in cmdlet and not 'smartct' in p.exe:
                    print("Found process " + str(p) + " containing name " + str(name) + " in cmdline.")
                    return p
        #print("No process found for " + str(name) + ".")
        return None

    def loadDiskImages(self):
        print("Loading disk images")
        directories = os.listdir('/home/partimag/')
        for name in directories:
            directory = os.path.join('/home/partimag',name)
            print("Found " + directory)
            if(os.path.isdir(directory)):
                try:
                    i = DiskImage(name, directory)
                    self.images.append(i)
                except Exception as e:
                    print("Error adding image at " + directory + ":\n" + str(e))

    def start(self):
        self._loopgo = True
        self.observer = pyudev.MonitorObserver(self.monitor, self.deviceAdded)
        self.observer.start()
        self.server = ipc.Listener(address=self.serverAddress, authkey=b'H4789HJF394615R3DFESZFEZCDLPOQ')
        self.server._listener._socket.settimeout(3.0)
        self.updateThread = threading.Thread(target=self.updateLoop)
        self.updateThread.start()
        self.serverLoop()

    def stop(self):
        self._loopgo = False
        self.server.close()
        self.observer.stop()
        self.updateThread.join()
        for h in self.hdds:
            if(h.CurrentTaskStatus != TaskStatus.External) and (h.CurrentTaskStatus != TaskStatus.Idle):
                if(h.CurrentTaskStatus == TaskStatus.External):
                    print("Detaching external process " + str(h.CurrentTask.PID) + " on " + h.serial)
                    h.CurrentTask.detach()
                else:
                    print("Aborting task " + str(h.CurrentTask.name) + " (PID: " + str(h.CurrentTask.PID) + ") on " + h.serial)
                    h.CurrentTask.abort()
            if(h.status == HealthStatus.LongTesting or h.status == HealthStatus.ShortTesting):
                print("Detaching test on " + h.serial)
                h.test.detach()

    def signal_close(self, signalNumber, frame):
        print("Got signal " + str(signalNumber) + ", quitting.")
        self.stop()

    def signal_hangup(self, signalNumber, frame):
        print("Got signal " + str(signalNumber) + ", no action will be taken.")
        pass

    def signal_info(self, signalNumber, frame):
        print("Got signal " + str(signalNumber) + ", refreshing devices.")
        self._loopgo = False
        self.stop()
        self.hdds.clear()
        self.images.clear()
        self.updateDevices(bootDiskNode)
        self.loadDiskImages()
        self.start()


if __name__ == '__main__':
    hd = ListModel()
    signal.signal(signal.SIGINT, hd.signal_close)
    signal.signal(signal.SIGQUIT, hd.signal_close)
    signal.signal(signal.SIGTERM, hd.signal_close)
    #signal.signal(signal.SIGKILL, hd.signal_close) #We should let this kill the program instead of trying to handle it
    signal.signal(signal.SIGHUP, hd.signal_hangup)
    signal.signal(signal.SIGUSR1, hd.signal_info)
    hd.start()
    exit(0)
else:
    print("This program is intended to be run from the cli")
    logwrite("This program is intended to be run from the cli")
    exit(55)