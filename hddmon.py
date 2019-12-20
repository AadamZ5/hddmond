#!/usr/bin/python3
import os
import subprocess
import multiprocessing.connection as ipc
import proc.core
import pyudev
from pySMART import Device
import re
import urwid as ui
from hdd import Hdd, HddViewModel
import pySMART
import time
import threading
import sasdetection
import portdetection

debug = False
def logwrite(s:str, endl='\n'):
    if(debug):
        fd = open("./main.log", 'a')
        fd.write(s)
        fd.write(endl)
        fd.close()


class HddInfo(ui.WidgetWrap):
    def __init__(self, hdd: Hdd, app):
        self.hdd = hdd
        self.__app__ = app
        self._title = ui.Text("HDD Info")
        self._tests = ui.SimpleFocusListWalker(hdd._smart.tests)
        self._teststree = ui.TreeListBox(self._tests)
        self._exit = ui.Button("Exit", on_press=self.exit)
        self._main = ui.Frame(self._teststree, header=self._title)
        super(HddInfo, self).__init__(self._title)

    def show(self, *args, **kwargs):
        self._oldw = self.__app__.loop.widget
        self.__app__.loop.widget = self

    def exit(self, *args, **kwargs):
        self.__app__.loop.widget = self._oldw


class HddWidget(ui.WidgetWrap):
    def __init__(self, hdd: HddViewModel, app):
        self.hdd = hdd
        self.__app__ = app
        self._checked = False
        self._id = ui.Text((self.hdd.status, str(self.hdd.serial)), align='left')
        self._node = ui.Text(self.hdd.node, align='center')
        #self._pci = ui.Text(str(self.hdd.OnPciAddress), align='center')
        self._task = ui.Text((self.hdd.taskStatus, self.hdd.taskString), align='center')
        self._port = ui.Text(str(self.hdd.port), align='center')
        self._cap = ui.Text(str(self.hdd.size), align='center')
        if(self.hdd.isSsd):
            self._cap.set_text(str(hdd.size) + " SSD")
        self._stat = ui.Text((self.hdd.status, self.hdd.smartResult), align='center')
        self._check = ui.CheckBox('', state=self._checked)
        self._more = ui.Button("Info", on_press=self.ShowInfo)

        self._col = ui.Columns([(4,self._check), ('weight', 35, self._id), ('weight', 20, self._port), ('weight', 20, self._cap), ('weight', 25, self._node), ('weight', 15, self._task), ('weight', 10, self._stat), ('weight', 25, self._more)])
        self._pad = ui.Padding(self._col, align='center', left=2, right=2)
        self.Update(self.hdd)
        super(HddWidget, self).__init__(self._pad)

    @property
    def checked(self):
        return self._check.get_state()

    def Update(self, newhdd):
        self.hdd = newhdd
        self._id.set_text((self.hdd.status, str(self.hdd.serial)))

        if(self.hdd.status == Hdd.STATUS_TESTING) or (self.hdd.status == Hdd.STATUS_LONGTST):
            self._stat.set_text((self.hdd.status, str(self.hdd.testProgress)))
        else:
            self._stat.set_text((self.hdd.status, str(self.hdd.smartResult)))
        
        if(self.hdd.taskStatus != Hdd.TASK_NONE):
            self._task.set_text((self.hdd.taskStatus, self.hdd.taskString))
            self._cap.set_text((self.hdd.taskStatus, self.hdd.size))
        elif(self.hdd.taskStatus == Hdd.TASK_NONE):
            self._task.set_text((self.hdd.taskStatus, self.hdd.taskString))
            self._cap.set_text(self.hdd.size)

    def ShowInfo(self, *args, **kwargs):
        h = (h.serial for h in self.__app__.hddobjs)
        if h:
            hinfo = HddInfo(h, self.__app__)


class Application(object):
    def __init__(self):

        self.palette = [
        #keywd              #foregnd        "backgnd"
        (None,              'light gray',   'black'),
        ('heading',         'black',        'light gray'),
        ('border',          'light gray',   'black'),
        ('line',            'black',        'light gray'),
        ('options',         'dark gray',    'black'),
        ('focus heading',   'white',        'dark red'),
        ('focus border',    'light green',  'black'),
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
        (Hdd.TASK_NONE, 'dark gray', 'black'),
        (Hdd.TASK_EXTERNAL, 'dark blue', 'black'),
        (Hdd.TASK_ERROR, 'dark red', 'black')]
        
        self.focus_map = {
        'heading': 'focus heading',
        'border': 'focus border', 
        'options': 'focus options',
        'line': 'focus line'}

        self.commandQueue = [] #format (command, serials, extradata, callback)
        self.hddobjs = []
        self.hddEntries = ui.SimpleListWalker([])
        self.ListView = ui.ListBox(self.hddEntries)

        # self._col = ui.Columns([(4,self._check), ('weight', 35, self._id), ('weight', 25, self._port), ('weight', 25, self._node), ('weight', 15, self._task), ('weight', 10, self._stat), ('weight', 25, self._more)])
        #self.ListHeader = ui.Columns([(4, ui.Divider()), ('weight', 35, ui.Text("Serial")), ('weight', 25, ui.Text("Port")), ('weight',25, ui.Text("Node")), ('weight', 15, ui.Text("Task")), ('weight', 10, "Test stat"), ('weight', 25, ui.Divider())])
        #self.ListHeader = ui.Text("Temp")
        #self.border = ui.LineBox(ui.ListBox([self.ListHeader, self.ListView]))
        self.border = ui.LineBox(self.ListView)
        self.HddListUi = ui.Frame(header=ui.Text("Harddrives", align='center', wrap='clip'), body=self.border)

        self.Terminal = ui.Terminal(['bash', '-c', 'htop'])
        self.terminalBorder = ui.LineBox(self.Terminal)
        self.Htop = ui.Frame(header=ui.Text("HTOP (Ctrl-A to escape)", align='center', wrap='clip'), body=self.terminalBorder)

        self.ShortTest = ui.Button("Short test", on_press=self.commandShortTest)
        self.LongTest = ui.Button("Long test", on_press=self.commandLongTest)
        self.AbortTest = ui.Button("Abort test", on_press=self.commandAbortTest)
        self.Erase = ui.Button("Erase disk", on_press=self.ShowAreYouSureDialog, user_data=[['Erase drives?'], self.commandErase])
        self.Clone = ui.Button("Apply image", on_press=self.ShowErrorDialog, user_data=["Cloning is not supported yet."])

        self.SubControls = ui.ListBox([self.ShortTest, self.LongTest, self.AbortTest, ui.Divider(), self.Erase, ui.Divider(), self.Clone, ui.Divider(), ui.Button("Exit", on_press=self.exit)])
        self.SubControls = ui.LineBox(self.SubControls)
        self.SubControls = ui.Frame(header=ui.Text("HDD Options", align="center", wrap="clip"), body=self.SubControls)

        self.Top = ui.Columns([('weight', 70, self.HddListUi), ('weight', 30, self.SubControls)], min_width=15)

        self.MainFrame = ui.Pile([self.Top, self.Htop])

        self.loop = ui.MainLoop(ui.Filler(self.MainFrame, 'middle', 80), self.palette, pop_ups=True)
        self.Terminal.main_loop = self.loop
        ui.connect_signal(self.Terminal, 'closed', callback= self.reinitializeTerminal)

        self.daemonCommGo = True
        print("Connecting to server...")
        self.daemonAddress = ('localhost', 63962)
        self.daemonKey = b'H4789HJF394615R3DFESZFEZCDLPOQ'
        client = ipc.Client(self.daemonAddress, authkey=self.daemonKey)
        print("Connected!")
        self.daemonCommThread = threading.Thread(target=self.daemonComm, kwargs={'me': client})
    
    def commandShortTest(self, *args, **kwargs):
        serialList = []
        for hw in self.hddEntries:
            if hw.checked:
                serialList.append(hw.hdd.serial)

        command = ('shorttest', serialList, None)
        self.commandQueue.append(command)

    def commandLongTest(self, *args, **kwargs):
        serialList = []
        for hw in self.hddEntries:
            if hw.checked:
                serialList.append(hw.hdd.serial)

        command = ('longtest', serialList, None)
        self.commandQueue.append(command)

    def commandAbortTest(self, *args, **kwargs):
        serialList = []
        for hw in self.hddEntries:
            if hw.checked:
                serialList.append(hw.hdd.serial)

        command = ('aborttest', serialList, None)
        self.commandQueue.append(command)

    def commandErase(self, *args, **kwargs):
        serialList = []
        for hw in self.hddEntries:
            if hw.checked:
                serialList.append(hw.hdd.serial)

        command = ('erase', serialList, None)
        self.commandQueue.append(command)

    def processHddData(self, hdds):
        logwrite("Checking!!!")
        logwrite("List: " + str(hdds))
        self.hddobjs = hdds
        localhdds = list(hdds).copy()
        foundhdds = []

        for hw in self.hddEntries:#look for hdds in here.

            logwrite("Checking " + str(hw.hdd.serial))
            found = False
            for h in localhdds:
                logwrite("\t against " + h.serial)
                if(str(h.serial) == str(hw.hdd.serial)):
                    logwrite("\t===FOUND===")
                    hvm = HddViewModel.FromHdd(h)
                    hw.Update(hvm) #Update the widget with the new hdd info
                    foundhdds.append(h)
                    found = True
                    break 
            
            if found == False: #Found = false, remove the widget.
                logwrite("Removed " + str(hw.hdd.serial))
                self.hddEntries.remove(hw)
        
        logwrite("Found HDDs: " + str(foundhdds))
        for h in foundhdds:#Hdd objects found, remove from the localhdds list
            for hr in localhdds:
                if hr.serial == h.serial:
                    localhdds.remove(hr)

        logwrite("Leftover HDDs: " + str(localhdds))
        for hrem in localhdds: #Process the leftover hdds for which we didn't have a widget currently representing
            hvm = HddViewModel.FromHdd(hrem)
            hddwidget = HddWidget(hvm, self)
            self.hddEntries.append(hddwidget)

    
    def daemonComm(self, me=None):
        while self.daemonCommGo and ('me' in locals()):
            if(len(self.commandQueue) == 0):
                me.send(('listen', None, None))
                try:
                    data = me.recv()#blocking call
                except EOFError as e:
                    self.ShowErrorDialog(text=["Pipe unexpectedly closed:\n", str(e)])
                    data = None
                    del me
                    break
                except FileNotFoundError as e:
                    self.ShowErrorDialog(text=["Server sent a device that doesnt exist:\n", str(e)])
                    data = None
                except pyudev.DeviceNotFoundByFileError as e:
                    self.ShowErrorDialog(text=["Server sent a device that doesnt exist:\n", str(e)])
                    data = None
                except Exception as e:
                    self.ShowErrorDialog(text=["Error\n", str(e)])
                    data = None
                if(data):
                    logwrite("Got data: " + str(data))
                    self.processHddData(data)
            else:
                t = self.commandQueue.pop()
                cmd = (t[0],t[1],t[2])
                if(len(t) >3):
                    callback = t[4]
                else:
                    callback = None
                me.send(cmd)
                try:
                    data = me.recv()#blocking call
                except EOFError as e:
                    self.ShowErrorDialog(text=["Pipe unexpectedly closed:\n", str(e)])
                    data = None
                    del me
                    break
                if(data != None):
                    if(callback):
                        callback(data)
                        
            time.sleep(1)
        try:
            me.close()
        except Exception as e:
            self.ShowErrorDialog(text=["Error while closing connection:\n", str(e)])

    def reinitializeTerminal(self, loop, **kwargs):
        self.Terminal.touch_term(self.Terminal.width, self.Terminal.height)

    def resetLayout(self, button, t=None):
        #t should be (bool, callback) or None
        self.MainFrame = ui.Pile([self.Top, self.Htop])
        self.loop.widget = self.MainFrame

        if(t): #t != None
            if(type(t) == tuple):
                if(len(t) > 1):
                    if(t[0]): #if bool is true
                        if(t[1]):
                            t[1]() #true callback
                    else:
                        if(t[2]):
                            t[2]() #false callback
            else:
                pass

    def exit(self, button=None, args=None):
        self.ShowExitDialog()
        self.loop.draw_screen()
        self.stop()

    def ShowExitDialog(self, button=None):

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
            self.Top,
            align = 'center',
            width = 40,
            valign = 'middle',
            height = 10
        )

        self.MainFrame = ui.Pile([w, self.Htop])
        self.loop.widget = self.MainFrame

    def ShowErrorDialog(self, button=None, text = ['']):

        # Header
        header_text = ui.Text(('banner', 'Error'), align = 'center')
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
        footer = ui.Button('Okay', self.resetLayout, user_data=True)
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
            self.Top,
            align = 'center',
            width = 40,
            valign = 'middle',
            height = 10
        )

        self.MainFrame = ui.Pile([w, self.Htop])
        self.loop.widget = self.MainFrame

    def ShowYesNoDialog(self, button=None, args = []):
        
        #args is a [['Line1', 'Line2'], callback]
        text = args[0]
        
        callback = None
        if(len(args) > 1):
            yescallback = args[1]
            nocallback = args[2]

        # Header
        header_text = ui.Text(('banner', 'Choose an option'), align = 'center')
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
        yes = ui.Button('Yes', self.resetLayout, user_data=(True, yescallback, nocallback))
        yes = ui.AttrWrap(yes, 'selectable', 'focus')
        no = ui.Button('No', self.resetLayout, user_data=(False, yescallback, nocallback))
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
            self.Top,
            align = 'center',
            width = 40,
            valign = 'middle',
            height = 10
        )
        self.MainFrame = ui.Pile([w, self.Htop])
        self.loop.widget = self.MainFrame

    def ShowAreYouSureDialog(self, button=None, args = []):
        
        #args is a [['Line1', 'Line2'], callback]
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
        yes = ui.Button('Yes', self.resetLayout, user_data=(True, callback))
        yes = ui.AttrWrap(yes, 'selectable', 'focus')
        no = ui.Button('No', self.resetLayout, user_data=(False, callback))
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
            self.Top,
            align = 'center',
            width = 40,
            valign = 'middle',
            height = 10
        )
        self.MainFrame = ui.Pile([w, self.Htop])
        self.loop.widget = self.MainFrame

    def start(self):
        self.daemonCommThread.start()
        self.loop.run()

    def stop(self):
        self.daemonCommGo = False
        self.daemonCommThread.join()
        os.system('clear')
        raise ui.ExitMainLoop()
        exit(0)





if __name__ == '__main__':
    app = Application()
    app.start()