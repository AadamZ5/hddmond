#!/usr/bin/python3
import os
import subprocess
import pyudev
from pySMART import Device
import re
import urwid as ui
from hdd import Hdd
import hddctl
import pySMART
import time
import threading
import sasdetection

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

def exit_program(key):
    listModel.stop()
    raise ui.ExitMainLoop()


class HddWidget(ui.WidgetWrap):
    def __init__(self, hdd: Hdd):
        self.hdd = hdd
        self._checked = False
        self._id = ui.Text((self.hdd.status, str(self.hdd.serial)), align='left')
        self._node = ui.Text(self.hdd.node, align='center')
        self._stat = ui.Text((self.hdd.status, self.hdd._smart.assessment), align='center')
        self._check = ui.CheckBox('', state=self._checked, on_state_change=self._stateChanged)
        self._col = ui.Columns([(4,self._check), ('weight', 50, self._id), ('weight', 25, self._node), ('weight', 25, self._stat)])
        self._pad = ui.Padding(self._col, align='center', left=2, right=2)
        super(HddWidget, self).__init__(self._pad)
    
    def ShortTest(self):
        self.hdd.ShortTest()
        self._id.set_text((self.hdd.status, str(self.hdd.serial)))
        self._stat.set_text((self.hdd.status, str(self.hdd.GetTestProgressString())))

    @property
    def checked(self):
        return self._check.get_state()

    def LongTest(self):
        self.hdd.LongTest()
        self._id.set_text((self.hdd.status, str(self.hdd.serial)))
        self._stat.set_text((self.hdd.status, str(self.hdd.GetTestProgressString())))
        
    def AbortTest(self):
        self.hdd.AbortTest()
        self.hdd.refresh()

    def UpdateTestProgress(self):
        self.hdd.refresh()
        self._id.set_text((self.hdd.status, str(self.hdd.serial)))

        if(self.hdd.status == Hdd.STATUS_TESTING) or (self.hdd.status == Hdd.STATUS_LONGTST):
            self._stat.set_text((self.hdd.status, str(self.hdd.GetTestProgressString())))
        else:
            self._stat.set_text((self.hdd.status, str(self.hdd._smart.assessment)))
        

    def _stateChanged(self, state: bool, udata):
        self._checked = state
        

class ListModel:
    """
    Data model that holds hdd list and widgets.
    """


    def __init__(self):
        self.updateInterval = 3
        self.hdds = {}
        self.hddEntries = ui.SimpleListWalker([])
        self.monitor = pyudev.Monitor.from_netlink(context)
        self.monitor.filter_by(subsystem='block', device_type='disk')
        self.observer = pyudev.MonitorObserver(self.monitor, self.deviceAdded)
        self.observer.start()
        self.updateDevices(bootDiskNode)
        self._loopgo = True
        self.updateThread = threading.Thread(target=self._updateLoop)
        self.updateThread.start()

    def stop(self):
        self._loopgo = False
        self.updateThread.join()

    def updateUi(self, loop, user_data=None):
        for hw in self.hddEntries:
            hw.UpdateTestProgress()
        loop.set_alarm_in(self.updateInterval, self.updateUi)

    def ShortTest(self, button):
        for hw in self.hddEntries:
            if(hw.checked):
                hw.ShortTest()

    def LongTest(self, button):
        for hw in self.hddEntries:
            if(hw.checked):
                hw.LongTest()
        
    def AbortTest(self, button):
        for hw in self.hddEntries:
            if(hw.checked):
                hw.AbortTest()

    def EraseDisk(self, button):
        ui.PopUpLauncher(EraseAreYouSure)
        pass

    def _updateLoop(self):
        while self._loopgo:
            for hdd in list(self.hdds.keys()):
                if(hdd.status == Hdd.STATUS_LONGTST) or (hdd.status == Hdd.STATUS_TESTING):
                    hdd.UpdateSmart()
            time.sleep(1.5)

    def updateDevices(self, bootNode: str):
        """
        Checks the system's existing device list and gatheres already connected hdds.
        """
        #Check to see if this device path already exists in our application.
        print(pySMART.DeviceList().devices)
        for d in pySMART.DeviceList().devices:

            notFound = True
            if("/dev/" + d.name == bootNode): #Check if this is our boot drive.
                notFound = False

            for hdd in self.hdds:
                print("Testing: /dev/" + d.name + " == " + bootNode)
                if(hdd.node == "/dev/" + d.name) : #This device path exists. Do not add it.
                    notFound = False
                    break

            if(notFound): #If we didn't find it already in our list, go ahead and add it.
                self.addHdd(Hdd.FromSmartDevice(d))
                print("Added /dev/"+d.name)
            
    def addHdd(self, hdd: Hdd):
        hddWdget = HddWidget(hdd)
        self.hdds.update({hdd: hddWdget})
        self.hddEntries.append(hddWdget)
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
        #loop.stop()
        #print("DEVICE " + str(action) + ": " + str(device))
        if(action == 'add') and (device != None):
            #print("Adding device at " + str(device.device_node))
            hdd = Hdd.FromUdevDevice(device)
            self.addHdd(hdd)
            
        elif(action == 'remove') and (device != None):
            self.removeHddStr(device.device_node)
        #loop.start()

palette = [
    #keywd              #foregnd        "backgnd"
    (None,              'light gray',   'black'),
    ('heading',         'black',        'light gray'),
    ('line',            'black',        'light gray'),
    ('options',         'dark gray',    'black'),
    ('focus heading',   'white',        'dark red'),
    ('focus line',      'black',        'dark red'),
    ('focus options',   'black',        'light gray'),
    ('selected',        'white',        'dark blue'),
    ('divider',         'dark gray',   'black'),
    (Hdd.STATUS_FAILING, 'light red',        'black'),
    (Hdd.STATUS_DEFAULT, 'light gray', 'black'),
    (Hdd.STATUS_PASSING, 'light green', 'black'),
    (Hdd.STATUS_TESTING, 'yellow', 'black'),
    (Hdd.STATUS_UNKNOWN, 'light gray', 'dark red'),
    (Hdd.STATUS_LONGTST, 'light magenta', 'black')]
    
focus_map = {
    'heading': 'focus heading',
    'options': 'focus options',
    'line': 'focus line'}


listModel = ListModel()


ListView = ui.ListBox(listModel.hddEntries)
border = ui.LineBox(ListView)
HddList = ui.Frame(header=ui.Text("Harddrives", align='center', wrap='clip'), body=border)

ShortTest = ui.Button("Short test", on_press=listModel.ShortTest)
LongTest = ui.Button("Long test", on_press=listModel.LongTest)
AbortTest = ui.Button("Abort test", on_press=listModel.AbortTest)
Erase = ui.Button("Erase disk", on_press=listModel.EraseDisk)

EraseAreYouSure = ui.Frame(ui.ListBox([ui.Text("Erase disks?"), ui.Button("Yes"), ui.Button("No")]), header="Are you sure?")

SubControls = ui.ListBox([ShortTest,LongTest,AbortTest, ui.Divider(), Erase])
SubControls = ui.LineBox(SubControls)
SubControls = ui.Frame(header=ui.Text("HDD Options", align="center", wrap="clip"), body=SubControls)

Controls = ui.ListBox([ui.Button("Exit", on_press=exit_program)])
Controls = ui.LineBox(Controls)
Controls = ui.Frame(header=ui.Text("Options", align='center', wrap='clip'), body=Controls)

CommandCenter = ui.Pile([Controls, SubControls])

Master = ui.Columns([('weight', 70, HddList), ('weight', 30, CommandCenter)], min_width=10)

loop = ui.MainLoop(ui.Filler(Master, 'middle', 80), palette)
ui.connect_signal(listModel.hddEntries, 'modified', callback=listModel.updateUi, user_arg=loop)
loop.set_alarm_in(1, listModel.updateUi)

if __name__ == '__main__':
    loop.run()