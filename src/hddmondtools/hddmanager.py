#!../env/bin/python
import os, sys
sys.path.append(os.path.join(os.path.dirname(os.path.abspath(__file__)), os.path.pardir))
import subprocess
import multiprocessing.connection as ipc
import proc.core
import pyudev
from pySMART import Device
from hddmontools.hdd import Hdd, HddInterface
from hddmontools.task_service import TaskService
from hddmontools.task import ExternalTask, Task, ImageTask, EraseTask
from hddmontools.test import Test
from hddmontools.image import DiskImage, Partition
import pySMART
import time
import threading
import hddmontools.sasdetection
import hddmontools.portdetection
import signal
from socket import timeout
from .websocket import WebsocketServer
from .multiproc_socket import MultiprocSock
from .hddmon_dataclasses import HddData, TaskQueueData, TaskData, ImageData
from .genericdatabase import GenericDatabase
from hddmontools.hdd_remote import HddRemoteRecieverServer, HddRemoteReciever
from injectable import inject

import inspect

class ListModel:
    """
    Data model that holds hdd list.
    """

    def __init__(self, taskChangedCallback = None, database: GenericDatabase = None):
        self.updateInterval = 3 #Interval for scanning for running SMART tests
        self.task_change_outside_callback = taskChangedCallback #callback for when any hdd's task stuff calls back
        self.task_svc = inject(TaskService)
        self.task_svc.initialize()
        self.hdds = [] #The list of hdd's (HddInterface class)
        self.blacklist_hdds = self.load_blacklist_file() #The list of hdd's to ignore when seen
        self._udev_context = pyudev.Context() #The UDEV context. #TODO: Autowire?
        self.monitor = pyudev.Monitor.from_netlink(self._udev_context) #The monitor that watches for UDEV object actions (uses C bindings)
        self.monitor.filter_by(subsystem='block', device_type='disk') #Filter the incoming object actions
        self.remote_hdd_server = inject(HddRemoteRecieverServer)
        self.remote_hdd_server.register_devchange_callback(self.remote_hdd_callback)
        self.AutoShortTest = False #Do auto short test on new detected drives?
        self._loopgo = True #Condition for the SMART scan loop
        self.stuffRunning = False #Is stuff running? I don't know
        self.database = database #The database #TODO: Autowire!

        if self.database != None:
            if( not self.database.connect()):
                self.database = None
    
    def remote_hdd_callback(self, action, device: HddInterface):
        if('add' in action):
            
            if device.serial in (h.serial for h in self.hdds):
                print("Got a remote device that already exists locally. Rejecting...")
                device.disconnect()
            else:
                print("Incomming connection from remote device {0}".format(device.serial))
                self.hdds.append(device)
                if self.task_change_outside_callback != None and callable(self.task_change_outside_callback):
                    self.task_change_outside_callback({'update': 'add', 'data': HddData.FromHdd(device)})
        elif('remove' in action):
            if device in self.hdds:
                self.hdds.remove(device)
            if self.task_change_outside_callback != None and callable(self.task_change_outside_callback):
                self.task_change_outside_callback({'update': 'remove', 'data': HddData.FromHdd(device)})                    

    def task_change_callback(self, hdd: Hdd, *args, **kwargs):

        #####
        #
        # The task queue will call this callback on any registered hdd when something changes.
        # A list of possible "action"s are:
        #
        #   pausechange     (data is {paused: bool})
        #   taskadded       (data is {task: Task})
        #   taskfinished    (data is {task: Task, returncode: Int})
        #   tasklistmod     (data is {tasklist: Task[]})
        #   taskabort       (data is {})
        #
        #####

        Tqd = TaskQueueData.FromTaskQueue(hdd.TaskQueue)
        
        data = kwargs.get('data', None)
        action = kwargs.get('action', None)

        if(data == None) or (action == None):
            return

        data.update({'serial': hdd.serial})

        if(action == "taskfinished"):
            self.database_task_finished(hdd, Tqd)

        if self.task_change_outside_callback != None and callable(self.task_change_outside_callback):
            self.task_change_outside_callback({'update': action, 'data': {'serial': hdd.serial, 'taskqueue': Tqd}})

    def database_task_finished(self, hdd:Hdd, task_queue_data: TaskQueueData):
        if self.database == None:
            return

        if not (len(task_queue_data.completed) > 0):
            return

        t = task_queue_data.completed[0]

        self.database.add_task(hdd.serial, t)
        if 'test' in t.name.lower():
            self.database.insert_attribute_capture(HddData.FromHdd(hdd))
            print("Captured SMART data into database from {0}".format(hdd.serial))

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
            
    def sendHdds(self, *args, **kw):
        serial = kw.get('serial', None)

        if serial != None:
            for h in self.hdds:
                if (h.serial == serial):
                    return {'hdd': HddData.FromHdd(h)}
            #This runs if the return statement doesn't execute
            return {'error': 'No hdd found with serial {0}'.format(serial)}

        else:
            hdddata = []
            for h in self.hdds:
                hdddata.append(HddData.FromHdd(h))
            return {'hdds': hdddata}
        return {'error': 'No hdd(s) found for constraints!'}

    def sendTaskTypes(self, *args, **kw):
        """
        Returns each HDD's supported task types
        """

        hdd_dict = {}
        for h in self.hdds:
            type_display_dict = h.get_available_tasks()
            hdd_dict[h.serial] = type_display_dict
        
        return hdd_dict

    def taskBySerial(self, *args, **kw):
        l = threading.Lock()
        l.acquire()
        serials = []
        task_obj = None
        parameter_data = dict()

        #This function can be used to multicast tasks to HDDs. Since
        #we allow remote HDDs to connect, which may have a different
        #task set, we have to check per-HDD what tasks are available.


        #Get the serials to task
        if('serials' in kw):
            serials = kw['serials']

        #Get the parameters for the task
        if('parameters' in kw):
            parameter_data = kw['parameters']

        hdds_to_task = []
        for h in self.hdds:
            if h.serial in serials:
                hdds_to_task.append(h)

        if('task' in kw):
            task_name = kw['task']
        else:
            return {'error': 'No task was specified!'}

        
        
        errors = []
        for h in hdds_to_task:
            if not (task_name in h.get_available_tasks().values()):
                errors.append({h.serial: "Task {0} doesn't exist for {1}".format(task_name, h.serial)})
            else:
                response = h.add_task(task_name=task_name, parameters=parameter_data)
                if response != None and 'need_parameters' in response:
                    response['serials'] = serials
                    return response
                else:
                    print("Queued task {0} on {1}".format(task_name, h.serial))
            
        l.release()
        return {'errors': errors}

    def abortTaskBySerial(self, *args, **kw):
        l = threading.Lock()
        l.acquire()
        serials = []
        if('serials' in kw):
            serials = kw['serials']
            
        for s in serials:
            for h in self.hdds:
                if h.serial == s:
                    name = h.TaskQueue.CurrentTask.name if h.TaskQueue.CurrentTask != None else ''
                    h.TaskQueue.AbortCurrentTask()
                    print("Sent abort to current task {0} on {1}".format(name, h.serial))
                    break;
        l.release()
        return True

    def modifyTaskQueue(self, *args, **kw):
        l = threading.Lock()
        l.acquire()

        serial = kw.get('serial', None)
        action = kw.get('action', None)
        index = kw.get('index', None)
        newindex = kw.get('newindex', None)

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
                elif(action == 'set'):
                    if(newindex == None):
                        return (False, 'No new index given with \'set\' operation')
                    h.TaskQueue.SetIndex(index, newindex)
                else:
                    return (False, 'Unknown modifyqueue action \'' + str(action) + '\'')
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

    def sendBlacklist(self, *a, **k):
        return {'blacklist': self.load_blacklist_file()}

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

    def updateLoop(self):
        '''
        This loop should be run in a separate thread. Watches for external processes and smart tests not initialized by this program.
        '''
        print("Loop running")
        smart_coldcall_interval = 30.0 #seconds
        while self._loopgo:
            busy = False
            for hdd in self.hdds:
                if not isinstance(hdd, Hdd): #Only perform on local Hdd devices
                    continue

                if not (isinstance(hdd.TaskQueue.CurrentTask, Test)): #Check if the current task is a test or not
                    if(time.time() - hdd._smart_last_call > smart_coldcall_interval): #If we're not testing, occasionally check to see if a test was started externally.
                        #print("smart cold-call to " + str(hdd.serial))
                        try:
                            hdd.update_smart()
                            hdd._smart_last_call = time.time()
                        except Exception as e:
                            print("Exception raised during SMART refresh!: " + str(e))
                if(hdd.TaskQueue.CurrentTask != None): #If there is a task operating on the drive's data
                    busy = True
                else:
                    task = self.findProcAssociated(hdd.name)
                    if(task != None):
                        hdd.TaskQueue.AddTask(ExternalTask(hdd, task.pid))
            self.stuffRunning = busy
            time.sleep(1)

    def updateDevices(self, ignoreNodes = []):
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
            if("/dev/" + d.name in ignoreNodes): #Check if this is our boot drive.
                notFound = False

            for hdd in self.hdds:
                #print("Testing: /dev/" + d.name + " == " + hdd.node)
                if(hdd.node == "/dev/" + d.name) : #This device path exists. Do not add it.
                    notFound = False
                    break
            
            if(notFound): #If we didn't find it already in our list, go ahead and add it.
                h = Hdd.FromSmartDevice(d)
                if self.addHdd(h):
                    print("Added /dev/"+d.name)
                else:
                    print("Skipped adding /dev/"+d.name)

        print("Finished adding existing devices")
            
    def addHdd(self, hdd: Hdd):
        if(self.check_in_blacklist(hdd)):
            del hdd
            return False

        t = self.findProcAssociated(hdd.name)
        if(t != None):
            hdd.TaskQueue.AddTask(ExternalTask(hdd, t.pid))
        self.hdds.append(hdd)
        if(self.AutoShortTest == True) and (not isinstance(hdd.TaskQueue.CurrentTask, Test)):
            hdd.ShortTest()
        hdd.add_task_changed_callback(self.task_change_callback)

        if(self.database != None):
            self.database.update_hdd(HddData.FromHdd(hdd))
            hdd.seen = self.database.see_hdd(hdd.serial)

        if self.task_change_outside_callback != None and callable(self.task_change_outside_callback):
            self.task_change_outside_callback({'update': 'add', 'data': HddData.FromHdd(hdd)})
        
        return True

    def removeHddHdd(self, hdd: Hdd):
        self.removeHddStr(hdd.node)
    
    def removeHddStr(self, node: str):
        for h in self.hdds:
            if (h.node == node):
                try:
                    if self.task_change_outside_callback != None and callable(self.task_change_outside_callback):
                        self.task_change_outside_callback({'update': 'remove', 'data': HddData.FromHdd(h)})
                    if(self.database != None):
                        self.database.update_hdd(HddData.FromHdd(h))
                    self.hdds.remove(h)
                except KeyError as e:
                    print("Error removing hdd by node!:\n" + str(e))
                break

    def deviceAdded(self, action, device: pyudev.Device):
        print("Udev: " + str(action) + " " + str(device))
        if(action == 'add') and (device != None):
            hdd = Hdd.FromUdevDevice(device)
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

    def start(self):
        

        self.observer = pyudev.MonitorObserver(self.monitor, self.deviceAdded)
        self.observer.start()
        self._loopgo = True

        self.remote_hdd_server.start()

        self.updateDevices()
        print("Done initializing.")
        self.updateLoop()

    def stop(self):
        print("Stopping hddmanager...")
        self._loopgo = False
        print("Stopping udev observer...")
        self.observer.stop()
        print("Stopping HDDs...")
        for h in self.hdds:
            print("\tShutting down {0}...".format(h.serial))
            h.disconnect()

        print("Disconnecting database...")
        if self.database != None:
            self.database.disconnect()

        print("Remote hdds...")
        self.remote_hdd_server.stop()

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
        self.updateDevices()
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