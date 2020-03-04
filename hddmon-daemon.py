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
from hddmontools.hdd import Hdd, HealthStatus, TaskStatus, HddManager
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

class ListModel:
    """
    Data model that holds hdd list.
    """

    def __init__(self):
        self.updateInterval = 3
        self.hdds = []
        self.blacklist_hdds = self.load_blacklist_file()
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
        

        self.serverAddress = ('localhost', 63963)

        self.clientlist = [] #list of (client, addr, thread)
        

    def update_blacklist_file(self):
        import json
        dict_list = self.blacklist_hdds

        old_list = self.load_blacklist_file()
        
        need_to_add = dict_list.copy()

        #Look for matching entries so we don't create duplicates
        for new in need_to_add:
            existing = False
            for old in old_list:

                for k in new.keys():
                    if k in old:
                        if new[k] != old[k]:
                            pass #Keys aren't the same. Not the same entry.
                    else:
                        pass #Missing a key, they are not equal. Add our new entry.
                    existing = True #This only gets set true if all the keys exist and match
                    break

                if existing == True: #We found an entry with a matching key.
                    break
                            
            if existing:
                need_to_add.remove(new)
        
        old_list.extend(need_to_add)

        with open('blacklist.json', 'w+') as fd:
            json.dump(old_list, fd)
        
        self.blacklist_hdds = self.load_blacklist_file()
        

    def load_blacklist_file(self):
        import json
        dict_list = []
        if not os.path.exists('blacklist.json'):
            return []

        with open('blacklist.json', 'r') as fd:
            dict_list = json.load(fd)

        return dict_list

    def check_in_blacklist(self, hdd: Hdd):
        for d in self.blacklist_hdds:
            serial = d.get('serial', None)
            model = d.get('model', None)
            node = d.get('node', None)
            if serial == hdd.serial or model == hdd.model or node == hdd.node:
                return True
                break
        return False
            
            

    def eraseBySerial(self, *args, **kw): #Starts an erase operation on the drives matching the input serials
        r = False
        l = threading.Lock()
        l.acquire()
        serials = []
        if('serials' in kw):
            serials = kw['serials']

        for s in serials:
            for h in self.hdds:
                if h.serial == s:
                    r = h.Erase()
                    if r == True:
                        print("Started erase on " + str(h.serial))
                    else:
                        print("Couldn't start erase on " + str(h.serial))
                    break;
        l.release()
        return r

    def shortTestBySerial(self, *args, **kw): #Starts a short test on the drives matching the input serials
        l = threading.Lock()
        l.acquire()
        serials = []
        if('serials' in kw):
            serials = kw['serials']
            
        for s in serials:
            for h in self.hdds:
                if h.serial == s:
                    h.ShortTest()
                    break;
        l.release()
        return True

    def longTestBySerial(self, *args, **kw): #Starts a long test on the drives matching the input serials
        l = threading.Lock()
        l.acquire()
        serials = []
        if('serials' in kw):
            serials = kw['serials']
            
        for s in serials:
            for h in self.hdds:
                if h.serial == s:
                    h.LongTest()
                    break;
        l.release()
        return True

    def abortTestBySerial(self, *args, **kw): #Stops a test on the drives matching the input serials
        l = threading.Lock()
        l.acquire()
        serials = []
        if('serials' in kw):
            serials = kw['serials']
            
        for s in serials:
            for h in self.hdds:
                if h.serial == s:
                    h.AbortTest()
                    break;
        l.release()
        return True

    def imageBySerial(self, *args, **kw): #applies an image on the drives matching the input serials
        l = threading.Lock()
        l.acquire()
        im = None
        image = None
        serials = []
        if('serials' in kw):
            serials = kw['serials']
        if('image' in kw):
            image = kw['image']
            
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

    def abortTaskBySerial(self, *args, **kw):
        l = threading.Lock()
        l.acquire()
        serials = []
        if('serials' in kw):
            serials = kw['serials']
            
        for s in serials:
            for h in self.hdds:
                if h.serial == s:
                    h.TaskQueue.AbortCurrentTask()
                    break;
        l.release()
        return True

    def modifyTaskQueue(self, *args, **kw):
        l = threading.Lock()
        l.acquire()

        serial = kw.get('serial', None)
        action = kw.get('action', None)
        index = kw.get('index', None)

        if(serial == None):
            return (False, 'No serial supplied')

        if(index == None):
            return (False, 'No index supplied')

        try:
            index = int(index)
        except TypeError:
            return (False, 'Index needs to be an integer')

        for h in self.hdds:
            if h.serial == serial:
                if(action == 'up'):
                    h.TaskQueue.PushUp(index)
                elif(action == 'down'):
                    h.TaskQueue.PushDown(index)
                elif(action == 'remove'):
                    h.TaskQueue.RemoveTask(index)
                break;

        l.release()
        return True

    def blacklist(self, *a, **k):
        l = threading.Lock()
        l.acquire()
        serials = k.get('serials', None)

        if serials == None or type(serials) != list:
            return (False, "No serials specified")

        for s in serials:
            for h in self.hdds:
                if s == h.serial:
                    self.blacklist_hdds.append({'serial': h.serial, 'model': h.model})
                    self.hdds.remove(h)
                    break

        self.update_blacklist_file()
        l.release()
        return True

    def pauseQueue(self, *a, **k):
        l = threading.Lock()
        l.acquire()
        serials = k.get('serials', None)
        pause = k.get('pause', True)

        if serials == None or type(serials) != list:
            return (False, "No serials specified")

        for s in serials:
            for h in self.hdds:
                if s == h.serial:
                    h.TaskQueue.Pause = pause
                    break;

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
                
            #The message type is a tuple of (command, data)

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
                        if(self.eraseBySerial(**data)):
                            client.send(('success', command))
                        else:
                            client.send('error')

                    elif command == 'shorttest':
                        if(self.shortTestBySerial(**data)):
                            client.send(('success', command))
                        else:
                            client.send('error')

                    elif command == 'longtest':
                        if(self.longTestBySerial(**data)):
                            client.send(('success', command))
                        else:
                            client.send('error')

                    elif command == 'aborttest':
                        if(self.abortTestBySerial(**data)):
                            client.send(('success', command))
                        else:
                            client.send('error')

                    elif command == 'getimages':
                        client.send(('images', self.images))

                    elif command == 'image':
                        if(self.imageBySerial(**data)):
                            client.send(('success', command))
                        else:
                            client.send('error')

                    elif command == 'aborttask':
                        if(self.abortTaskBySerial(**data)):
                            client.send(('success', command))
                        else:
                            client.send('error')

                    elif command == 'hdds':
                        client.send((command, self.hdds))

                    elif command == 'modifyqueue':
                        if(self.modifyTaskQueue(**data)):
                            client.send(('success', command))

                    elif command == 'pausequeue':
                        if(self.pauseQueue(**data)):
                            client.send(('success', command))

                    elif command == 'blacklist':
                        if(self.blacklist(**data)):
                            client.send(('success', command))

                    else:
                        client.send(('error', 'Unknown command'))
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
                        hdd.TaskQueue.AddTask(ExternalTask(task.pid, processExitCallback=hdd._taskCompletedCallback))
                        hdd.CurrentTaskStatus = TaskStatus.External
                hdd.refresh()
            self.stuffRunning = busy
            time.sleep(1)

    def updateDevices(self, bootNode: str):
        """
        Checks the system's existing device list and gatheres already connected hdds.
        Does not check for already existing devices. It's a good idea to clear the current
        device list first.
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
        if(self.check_in_blacklist(hdd)):
            del hdd
            return False

        t = self.findProcAssociated(hdd.name)
        if(t != None):
            hdd.TaskQueue.AddTask(ExternalTask(t.pid, processExitCallback=hdd._taskCompletedCallback))
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
            h.TaskQueue.Pause = True
            if(h.CurrentTaskStatus != TaskStatus.External) and (h.CurrentTaskStatus != TaskStatus.Idle):
                if(h.CurrentTaskStatus == TaskStatus.External) or (h.CurrentTaskStatus == TaskStatus.LongTesting) or (h.CurrentTaskStatus == TaskStatus.ShortTesting):
                    print("Detaching task " + str(h.TaskQueue.CurrentTask.name) + " on " + h.serial)
                    h.TaskQueue.CurrentTask.detach()
                else:
                    print("Aborting task " + str(h.TaskQueue.CurrentTask.name) + " (PID: " + str(h.TaskQueue.CurrentTask.PID) + ") on " + h.serial)
                    h.TaskQueue.CurrentTask.abort()
            if(h.status == HealthStatus.LongTesting or h.status == HealthStatus.ShortTesting):
                print("Detaching from SMART test on " + h.serial)
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