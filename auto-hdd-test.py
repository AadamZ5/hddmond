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
    raise ui.ExitMainLoop()


class HddWidget(ui.WidgetWrap):
    def __init__(self, hdd: Hdd):
        self.hdd = hdd
        self.checked = False
        _id = ui.Text((self.hdd.status, str(self.hdd.serial)), align='left')
        _stat = ui.Text((self.hdd.status, self.hdd._smart.assessment), align='right')
        self._check = ui.CheckBox('', state=self.checked, on_state_change=self._stateChanged)
        _col = ui.Columns([(4,self._check), _id, _stat])
        _lin = ui.LineBox(_col, tlcorner='', trcorner='', lline='', rline='', blcorner='', brcorner='', tline='')
        ui.AttrMap(_lin, 'divider')
        _pad = ui.Padding(_lin, align='center', left=2, right=2)
        super(HddWidget, self).__init__(_pad)
    
    def _stateChanged(self, state: bool, udata):
        self.checked = self._check.get_state()

class ListModel:
    """
    Data model that holds hdd list and widgets.
    """


    def __init__(self):
        self.hdds = {}
        self.hddEntries = ui.SimpleListWalker([])
        self.monitor = pyudev.Monitor.from_netlink(context)
        self.monitor.filter_by(subsystem='block', device_type='disk')
        self.observer = pyudev.MonitorObserver(self.monitor, self.deviceAdded)
        self.observer.start()
        self.updateDevices(bootDiskNode)

    def updateDevices(self, bootNode: str):
        """
        Checks the system's existing device list and gatheres already connected hdds.
        """

        #Check to see if this device path already exists in our application.
        print(pySMART.DeviceList().devices)
        for d in pySMART.DeviceList().devices:

            add = True
            if("/dev/" + d.name == bootNode): #Check if this is our boot drive.
                add = False

            for hdd in self.hdds:
                print("Testing: /dev/" + d.name + " == " + bootNode)
                if(hdd.node == "/dev/" + d.name) : #This device path exists. Do not add it.
                    add = False
                    break

            if(add): #If we didn't find it already in our list, go ahead and add it.
                self.addHdd(Hdd.FromSmartDevice(d))
                print("Added /dev/"+d.name)
            
    def addHdd(self, hdd: Hdd):
        hddWdget = HddWidget(hdd)
        self.hdds.update({hdd: hddWdget})
        self.hddEntries.append(hddWdget)

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

def refresh():
    loop.draw_screen()

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
    (Hdd.STATUS_UNKNOWN, 'light gray', 'dark red')]
    
focus_map = {
    'heading': 'focus heading',
    'options': 'focus options',
    'line': 'focus line'}


listModel = ListModel()


ListView = ui.ListBox(listModel.hddEntries)
border = ui.LineBox(ListView)
HddList = ui.Frame(header=ui.Text("Harddrives", align='center', wrap='clip'), body=border)


SubControls = ui.ListBox([])
SubControls = ui.LineBox(SubControls)
SubControls = ui.Frame(header=ui.Text("HDD Options", align="center", wrap="clip"), body=SubControls)

Controls = ui.ListBox([ui.Button("Exit", on_press=exit_program)])
Controls = ui.LineBox(Controls)
Controls = ui.Frame(header=ui.Text("Options", align='center', wrap='clip'), body=Controls)

CommandCenter = ui.Pile([Controls, SubControls])

Master = ui.Columns([('weight', 70, HddList), ('weight', 30, CommandCenter)], min_width=10)

loop = ui.MainLoop(ui.Filler(Master, 'middle', 80), palette)
ui.connect_signal(listModel.hddEntries, 'modified', callback=refresh)
loop.run()
