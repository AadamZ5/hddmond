#!/usr/bin/python3
import os
import subprocess
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



def exit_program():
    app.stop()
    raise ui.ExitMainLoop()



class HddWidget(ui.WidgetWrap):
    def __init__(self, hdd: Hdd):
        self.hdd = hdd
        self._checked = False
        self._id = ui.Text((self.hdd.status, str(self.hdd.serial)), align='left')
        self._node = ui.Text(self.hdd.node, align='center')
        #self._pci = ui.Text(str(self.hdd.OnPciAddress), align='center')
        self._task = ui.Text((self.hdd.CurrentTaskStatus, self.hdd.GetTaskProgressString()), align='center')
        self._port = ui.Text(str(self.hdd.Port), align='center')
        self._stat = ui.Text((self.hdd.status, self.hdd._smart.assessment), align='center')
        self._check = ui.CheckBox('', state=self._checked, on_state_change=self._stateChanged)
        self._more = ui.Button("Info")
        self._col = ui.Columns([(4,self._check), ('weight', 35, self._id), ('weight', 25, self._port), ('weight', 25, self._node), ('weight', 15, self._task), ('weight', 10, self._stat), ('weight', 25, self._more)])
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

    def Erase(self):
        self.hdd.Erase()

    def UpdateProgress(self):
        self.hdd.refresh()
        self._id.set_text((self.hdd.status, str(self.hdd.serial)))

        if(self.hdd.status == Hdd.STATUS_TESTING) or (self.hdd.status == Hdd.STATUS_LONGTST):
            self._stat.set_text((self.hdd.status, str(self.hdd.GetTestProgressString())))
        else:
            self._stat.set_text((self.hdd.status, str(self.hdd._smart.assessment)))
        
        if(self.hdd.CurrentTaskStatus == Hdd.TASK_ERASING):
            self._task.set_text((self.hdd.CurrentTaskStatus, self.hdd.GetTaskProgressString()))

    def _stateChanged(self, state: bool, udata):
        self._checked = state
        
class Dialog(ui.WidgetWrap):
    pass

class PopupOk():
    """A dialog that appears with nothing but a close button """
    signals = ['close']
    def __init__(self, text=[]):
        close_button = ui.Button("that's pretty cool")
        ui.connect_signal(close_button, 'click',
            lambda button:self._emit("close"))
        pile = ui.Pile([ui.Text(
            "^^  I'm attached to the widget that opened me. "
            "Try resizing the window!\n"), close_button])
        fill = ui.Filler(pile)
        super(PopupOk, self).__init__(ui.AttrWrap(fill, 'popbg'))


class ButtonPopup(ui.PopUpLauncher):
    def __init__(self):
        super(ButtonPopup, self).__init__(ui.Button("click-me"))
        ui.connect_signal(self.original_widget, 'click',
            lambda button: self.open_pop_up())

    def create_pop_up(self):
        pop_up = PopupOk()
        ui.connect_signal(pop_up, 'close',
            lambda button: self.close_pop_up())
        return pop_up

    def get_pop_up_parameters(self):
        return {'left':0, 'top':1, 'overlay_width':32, 'overlay_height':7}


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
        self.PortDetector = portdetection.PortDetection()
        self.updateDevices(bootDiskNode)
        self._loopgo = True
        self.updateThread = threading.Thread(target=self._updateLoop)
        self.updateThread.start()

    def stop(self):
        self._loopgo = False
        self.updateThread.join()

    def updateUi(self, loop, user_data=None):
        for hw in self.hddEntries:
            hw.UpdateProgress()
        loop.set_alarm_in(self.updateInterval, self.updateUi)

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

    def _updateLoop(self):
        while self._loopgo:
            for hdd in list(self.hdds.keys()):
                if(hdd.status == Hdd.STATUS_LONGTST) or (hdd.status == Hdd.STATUS_TESTING):
                    hdd.UpdateSmart()
                if(hdd.CurrentTaskStatus == Hdd.TASK_ERASING):
                    hdd.UpdateTask()
            time.sleep(1.5)

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
        if(action == 'add') and (device != None):
            hdd = Hdd.FromUdevDevice(device)
            self.PortDetector.Update()
            hdd.OnPciAddress = self.PortDetector.GetPci(hdd._udev.sys_path)
            hdd.Port = self.PortDetector.GetPort(hdd._udev.sys_path, hdd.OnPciAddress, hdd.serial)
            self.addHdd(hdd)
        elif(action == 'remove') and (device != None):
            self.removeHddStr(device.device_node)


class Application(object):
    def __init__(self):

        self.palette = [
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
        (Hdd.STATUS_LONGTST, 'light magenta', 'black'),
        (Hdd.TASK_ERASING, 'light cyan', 'black'),
        (Hdd.TASK_NONE, 'dark gray', 'black')]
        
        self.focus_map = {
        'heading': 'focus heading',
        'options': 'focus options',
        'line': 'focus line'}

        self.listModel = ListModel()

        self.ListView = ui.ListBox(self.listModel.hddEntries)

        # self._col = ui.Columns([(4,self._check), ('weight', 35, self._id), ('weight', 25, self._port), ('weight', 25, self._node), ('weight', 15, self._task), ('weight', 10, self._stat), ('weight', 25, self._more)])
        #self.ListHeader = ui.Columns([(4, ui.Divider()), ('weight', 35, ui.Text("Serial")), ('weight', 25, ui.Text("Port")), ('weight',25, ui.Text("Node")), ('weight', 15, ui.Text("Task")), ('weight', 10, "Test stat"), ('weight', 25, ui.Divider())])
        #self.ListHeader = ui.Text("Temp")
        #self.border = ui.LineBox(ui.ListBox([self.ListHeader, self.ListView]))
        self.border = ui.LineBox(self.ListView)
        self.HddList = ui.Frame(header=ui.Text("Harddrives", align='center', wrap='clip'), body=self.border)

        self.ShortTest = ui.Button("Short test", on_press=self.listModel.ShortTest)
        self.LongTest = ui.Button("Long test", on_press=self.listModel.LongTest)
        self.AbortTest = ui.Button("Abort test", on_press=self.listModel.AbortTest)
        self.Erase = ui.Button("Erase disk", on_press=self.ShowAreYouSureDialog, user_data=[['Erase drives?'], self.listModel.EraseDisk])

        self.SubControls = ui.ListBox([self.ShortTest,self.LongTest,self.AbortTest, ui.Divider(), self.Erase])
        self.SubControls = ui.LineBox(self.SubControls)
        self.SubControls = ui.Frame(header=ui.Text("HDD Options", align="center", wrap="clip"), body=self.SubControls)

        self.Controls = ui.ListBox([ui.Button("Exit", on_press=self.exit)])
        self.Controls = ui.LineBox(self.Controls)
        self.Controls = ui.Frame(header=ui.Text("Options", align='center', wrap='clip'), body=self.Controls)

        self.CommandCenter = ui.Pile([self.Controls, self.SubControls])

        self.Master = ui.Columns([('weight', 70, self.HddList), ('weight', 30, self.CommandCenter)], min_width=15)

        self.loop = ui.MainLoop(ui.Filler(self.Master, 'middle', 80), self.palette, pop_ups=True)
        ui.connect_signal(self.listModel.hddEntries, 'modified', callback=self.listModel.updateUi, user_arg=self.loop)
        self.loop.set_alarm_in(1, self.listModel.updateUi)

    def reset_layout(self, button, t=None):
        #t should be (bool, callback) or None

        self.loop.widget = self.Master

        if(t):
            if(len(t) > 1):
                if(t[0]):
                    t[1]()

    def exit(self, button, args=None):
        self.ShowExitDialog(None)
        self.loop.draw_screen()
        exit_program()

    def ShowExitDialog(self, button):

        # Header
        header_text = ui.Text(('banner', 'Please wait'), align = 'center')
        header = ui.AttrMap(header_text, 'banner')

        # Body
        body_text = ui.Text("Exiting, please wait...", align = 'center')
        body_filler = ui.Filler(body_text, valign = 'middle')
        body_padding = ui.Padding(
            body_filler,
            left = 1,
            right = 1
        )
        body = ui.LineBox(body_padding)

        # Footer
        #footer = ui.Button('Okay', self.reset_layout)
        # footer = ui.AttrWrap(footer, 'selectable', 'focus')
        # footer = ui.GridFlow([footer], 8, 1, 1, 'center')

        # Layout
        layout = ui.Frame(
            body,
            header = header,
            #footer = footer,
            focus_part = 'footer'
        )

        w = ui.Overlay(
            ui.LineBox(layout),
            self.Master,
            align = 'center',
            width = 40,
            valign = 'middle',
            height = 10
        )

        self.loop.widget = w

    def ShowErrorDialog(self, button, text = ['']):

        # Header
        header_text = ui.Text(('banner', 'Error'), align = 'center')
        header = ui.AttrMap(header_text, 'banner')

        # Body
        body_text = ui.Text(text, align = 'center')
        body_filler = ui.Filler(body_text, valign = 'top')
        body_padding = ui.Padding(
            body_filler,
            left = 1,
            right = 1
        )
        body = ui.LineBox(body_padding)

        # Footer
        footer = ui.Button('Okay', self.reset_layout, user_data=True)
        footer = ui.AttrWrap(footer, 'selectable', 'focus')
        footer = ui.GridFlow([footer], 8, 1, 1, 'center')

        # Layout
        layout = ui.Frame(
            body,
            header = header,
            footer = footer,
            focus_part = 'footer'
        )

        w = ui.Overlay(
            ui.LineBox(layout),
            self.Master,
            align = 'center',
            width = 40,
            valign = 'middle',
            height = 10
        )

        self.loop.widget = w

    def ShowAreYouSureDialog(self, button, args = []):
        
        #args is a [['Text', 'lines'], callback]
        text = args[0]
        
        callback = None
        if(len(args) > 1):
            callback = args[1]

        # Header
        header_text = ui.Text(('banner', 'Are you sure?'), align = 'center')
        header = ui.AttrMap(header_text, 'banner')

        # Body
        body_text = ui.Text(text, align = 'center')
        body_filler = ui.Filler(body_text, valign = 'middle')
        body_padding = ui.Padding(
            body_filler,
            left = 1,
            right = 1
        )
        body = ui.LineBox(body_padding)

        # Footer
        yes = ui.Button('Yes', self.reset_layout, user_data=(True, callback))
        yes = ui.AttrWrap(yes, 'selectable', 'focus')
        no = ui.Button('No', self.reset_layout, user_data=(False, callback))
        no = ui.AttrWrap(no, 'selectable', 'focus')
        footer = ui.Columns([yes, no])
        footer = ui.GridFlow([footer], 20, 1, 1, 'center')

        # Layout
        layout = ui.Frame(
            body,
            header = header,
            footer = footer,
            focus_part = 'footer'
        )

        w = ui.Overlay(
            ui.LineBox(layout),
            self.Master,
            align = 'center',
            width = 40,
            valign = 'middle',
            height = 10
        )

        self.loop.widget = w

    def start(self):
        self.loop.run()

    def stop(self):
        self.listModel.stop()
        ui.ExitMainLoop()





if __name__ == '__main__':
    app = Application()
    app.start()