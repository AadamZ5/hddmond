#!/usr/bin/python3
import os
os.chdir('/etc/hddmon')
import subprocess
import multiprocessing.connection as ipc
import proc.core
import pyudev
from pySMART import Device
import re
import urwid as ui
import additional_urwid_widgets as ui_special
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

class HddTestEntryTreeWidget(ui.TreeWidget):
    def __init__(self, node,):
        super(HddTestEntryTreeWidget, self).__init__(node)

    def get_display_text(self):
        return self._node.get_key()

class TestEntryNode(ui.TreeNode):
    def __init__(self, test: pySMART.Test_Entry):
        self.test = test
        super(TestEntryNode).__init__(self.test, key=self.test.hours)
        
    def load_widget(self):
        return HddTestEntryTreeWidget(self)


class HddWidget(ui.WidgetWrap):
    def __init__(self, hdd: HddViewModel, app):
        self.hdd = hdd
        self.__app__ = app
        self._checked = False
        self._id = ui.Text((self.hdd.status, str(self.hdd.serial)), align='left')
        self._node = ui.Text(('text',self.hdd.node), align='center')
        #self._pci = ui.Text(str(self.hdd.OnPciAddress), align='center')
        self._task = ui.Text((self.hdd.taskStatus, str(self.hdd.taskString)), align='center')
        self._port = ui.Text(('text',str(self.hdd.port)), align='center')
        self._cap = ui.Text(('text',(str(self.hdd.size))), align='center')
        if(self.hdd.isSsd):
            self._cap.set_text(str(hdd.size) + " SSD")
        self._stat = ui.Text((self.hdd.status, self.hdd.smartResult), align='center')
        self._check = ui.CheckBox(('text',''), state=self._checked)
        self._check_wrap = ui.AttrMap(self._check, 'line', focus_map=self.__app__.focus_map)
        self._more = ui.Button(('text',"Info"), on_press=self.__app__.ShowHddInfo, user_data=self) #TODO FIx
        self._morewidget = ui.AttrMap(self._more, 'line', focus_map=self.__app__.focus_map)
        self._morewidget = ui.Padding(self._morewidget, align='center')

        self._col = ui.Columns([(4,self._check_wrap), ('weight', 35, self._id), ('weight', 20, self._port), ('weight', 20, self._cap), ('weight', 25, self._node), ('weight', 15, self._task), ('weight', 10, self._stat), (10, self._morewidget)])
        self._pad = ui.Padding(self._col, align='center', left=2, right=2)
        self._main = ui.AttrMap(self._pad, None, focus_map=self.__app__.focus_map)
        self.Update(self.hdd)
        super(HddWidget, self).__init__(self._pad)

    @property
    def checked(self):
        return self._check.get_state()

    def setChecked(self, bool):
        self._check.set_state(bool, do_callback=False)

    def Update(self, newhdd=None):
        if(newhdd != None):
            self.hdd = newhdd
        
        self._id.set_text((self.hdd.status, str(self.hdd.serial)))

        if(self.hdd.status == Hdd.STATUS_TESTING) or (self.hdd.status == Hdd.STATUS_LONGTST):
            self._stat.set_text((self.hdd.status, str(self.hdd.testProgress)))
        else:
            self._stat.set_text((self.hdd.status, str(self.hdd.smartResult)))
        
        if(self.hdd.taskStatus != Hdd.TASK_NONE):
            self._task.set_text((self.hdd.taskStatus, str(self.hdd.taskString)))
            self._cap.set_text((self.hdd.taskStatus, self.hdd.size))
        else:
            self._task.set_text((self.hdd.taskStatus, str(self.hdd.taskString)))
            self._cap.set_text(('text',self.hdd.size))

    def get_attr_map(self):
        return self._main.get_attr_map()
    def set_attr_map(self, attr):
        return self._main.set_attr_map(attr)

class Application(object):
    def __init__(self):

        self.palette = [
        #keywd              #foregnd        "backgnd"
        (None,              'light gray',   'black'),
        ('heading',         'black',        'light gray'),
        ('border',          'light gray',   'black'),
        ('line',            'light gray',   'black'),
        ('options',         'dark gray',    'black'),
        ('focus heading',   'white',        'dark red'),
        ('focus border',    'yellow',  'black'),
        ('active border',   'light cyan',    'black'),
        ('focus line',      'yellow',        'black'),
        ('focus options',   'black',        'light gray'),
        ('selected',        'white',        'dark blue'),
        ('divider',         'dark gray',   'black'),
        ('text',            'light gray',        'black'),
        ('focus text',      'light gray',     'dark gray'),
        ('exit',            'light gray',       'black'),
        ('exit focus',      'light gray',       'light red'),
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
        'line': 'focus line',
        'text': 'focus text',
        'exit': 'exit focus'}

        self.commandQueue = [] #format (command, serials, extradata, callback)
        self.hddobjs = []
        self.hddEntries = ui.SimpleListWalker([])
        
        self.buildControls()

        self.loop = ui.MainLoop(self.MainFrame, self.palette, pop_ups=True, unhandled_input=self.unhandled_input)
        self.Terminal.main_loop = self.loop
        self.loop.set_alarm_in(0.5, self.checkTerminalFocus, user_data=None)
        ui.connect_signal(self.Terminal, 'closed', callback=self.reinitializeTerminal)

        self.bigBoxes = [self.HddListUi, self.SubControls, self.Htop]

        self.daemonCommGo = True
        print("Connecting to server...")
        self.daemonAddress = ('localhost', 63962)
        self.daemonKey = b'H4789HJF394615R3DFESZFEZCDLPOQ'
        try:
            client = ipc.Client(self.daemonAddress, authkey=self.daemonKey)
        except Exception as e:
            print("A connection could not be established to the testing server: \n" + str(e))
            exit(1)
        print("Connected!")
        self.daemonCommThread = threading.Thread(target=self.daemonComm, kwargs={'me': client})

        self._all_selected = False
    
    def buildControls(self):
        self.ListView = ui_special.IndicativeListBox(self.hddEntries)

        # self._col = ui.Columns([(4,self._check), ('weight', 35, self._id), ('weight', 25, self._port), ('weight', 25, self._node), ('weight', 15, self._task), ('weight', 10, self._stat), ('weight', 25, self._more)])
        #self.ListHeader = ui.Columns([(4, ui.Divider()), ('weight', 35, ui.Text("Serial")), ('weight', 25, ui.Text("Port")), ('weight',25, ui.Text("Node")), ('weight', 15, ui.Text("Task")), ('weight', 10, "Test stat"), ('weight', 25, ui.Divider())])
        #self.ListHeader = ui.Text("Temp")
        self.border = ui.LineBox(ui.AttrMap(self.ListView, None))
        self.border = ui.AttrMap(self.border, None, focus_map='focus border')
        self.HddListUi = ui.Frame(header=ui.Text("Harddrives", align='center', wrap='clip'), body=self.border)

        self.Terminal = ui.Terminal(['bash', '-c', 'htop'], encoding="utf8", escape_sequence='tab')
        self.terminalBorder = ui.LineBox(self.Terminal)
        self.terminalBorder = ui.AttrMap(self.terminalBorder, None, focus_map='focus border')
        self.Htop = ui.Frame(header=ui.Text("HTOP ('tab' to escape)", align='center', wrap='clip'), body=self.terminalBorder)

        self.ShortTest = ui.AttrMap(ui.Button(('text',"Short test"), on_press=self.commandShortTest), 'line', focus_map=self.focus_map)
        self.LongTest = ui.AttrMap(ui.Button(('text',"Long test"), on_press=self.commandLongTest), 'line', focus_map=self.focus_map)
        self.AbortTest = ui.AttrMap(ui.Button(('text',"Abort test"), on_press=self.commandAbortTest), 'line', focus_map=self.focus_map)
        self.Erase = ui.AttrMap(ui.Button(('text',"Erase disk"), on_press=self.ShowAreYouSureDialog, user_data=[["Erase drives?"], self.commandErase]), 'line', focus_map=self.focus_map)
        self.Clone = ui.AttrMap(ui.Button(('text',"Apply image"), on_press=self.ShowErrorDialog, user_data=["Cloning is not supported yet."]), 'line', focus_map=self.focus_map)
        self.ExitButton = ui.AttrMap(ui.Button(('exit',"Exit"), on_press=self.exit), 'line', focus_map=self.focus_map)

        self.scEntries = ui.SimpleListWalker([self.ShortTest, self.LongTest, self.AbortTest, ui.Divider(), self.Erase, ui.Divider(), self.Clone, ui.Divider(), self.ExitButton])
        self.SubControls = ui_special.IndicativeListBox(self.scEntries)
        self.SubControls = ui.LineBox(self.SubControls)
        self.SubControls = ui.AttrMap(self.SubControls, None, focus_map='focus border')
        self.SubControls = ui.Frame(header=ui.Text("HDD Options", align="center", wrap="clip"), body=self.SubControls)

        self.Top = ui.Columns([('weight', 70, self.HddListUi), ('weight', 30, self.SubControls)], min_width=15)

        self.MainFrame = ui.Pile([self.Top, self.Htop])
        self.MainFrame = ui.Filler(self.MainFrame, 'middle', 80)

    def unhandled_input(self, key, *args, **kwargs):
        k = str(key).lower().strip()
        if k == 'ctrl a':
            self.select_all()
        elif k == 'ctrl q':
            self.ShowAreYouSureDialog(args=[["Exit?"], self.exit])
        elif k == 'tab':
            #self.circle_focus()
            pass

    def circle_focus(self):
        for i in range(len(self.bigBoxes)):
            if self.bigBoxes[i].focus:
                nex = i + 1
                if nex >= len(self.bigBoxes):
                    nex -= 3
                self.MainFrame.set_focus_path(self.bigBoxes[nex].get_focus_path())
                break

    def select_all(self):
        self._all_selected = True
        for hw in self.hddEntries:
            if hw.checked == False:
                self._all_selected = False

        for hw in self.hddEntries:
            hw.setChecked(not self._all_selected)

    def getSelected(self):
        selected = []
        for hw in self.hddEntries:
            if hw.checked == True:
                selected.append(hw)

        return selected

    def checkTerminalFocus(self, loop, user_data):
        if self.Terminal.keygrab:
            self.terminalBorder.set_focus_map({None: 'active border'})
        else:
            self.terminalBorder.set_focus_map({None: 'focus border'})
        loop.set_alarm_in(0.5, self.checkTerminalFocus, user_data=None)

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
                if(str(h.serial) == str(hw.hdd.serial)) and not (h in foundhdds):
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
                    self.ShowErrorDialog(text=["Pipe unexpectedly closed:\n", str(e) + "\n", "The connection to the testing server may have been lost."])
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
                    self.processHddData([])
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
                    self.ShowErrorDialog(text=["Pipe unexpectedly closed:\n", str(e) + "\n", "The connection to the testing server may have been lost."])
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
        self.Terminal = ui.Terminal(['bash'], main_loop=self.loop, escape_sequence='tab')
        self.terminalBorder = ui.LineBox(self.Terminal)
        self.terminalBorder = ui.AttrMap(self.terminalBorder, None, focus_map='focus border')
        self.Htop.set_body(self.terminalBorder)
        ui.connect_signal(self.Terminal, 'closed', callback=self.reinitializeTerminal)

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
                        if(len(t) > 2):
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

    def ShowHddInfo(self, button=None, hdw=None):
        hdd = None
        for h in self.hddobjs: #Get the actual hdd.Hdd type that corresponds to our hdd.HddViewModel
            if h.serial == hdw.hdd.serial:
                hdd = h
                break

        if hdd == None:
            self.ShowErrorDialog(text=["HDD " + str(hdw.hdd.serial) + "not found.\n", "Was the hard drive removed?"])
            return

        try:
            hdd.UpdateSmart()
            hdd.UpdateTask()
        except Exception as e:
            pass
        
        labelColWidth = 11
        valueColWidth = 89

        serial = ui.Columns([('weight', labelColWidth, ui.Text("Serial:", align='left')), ('weight',valueColWidth,ui.Text(hdd.serial))])
        model = ui.Columns([('weight', labelColWidth, ui.Text("Model:", align='left')), ('weight',valueColWidth,ui.Text(hdd.model))])
        size = ui.Columns([('weight', labelColWidth, ui.Text("Size:", align='left')), ('weight',valueColWidth,ui.Text(hdd.Size))])
        medium = ui.Columns([('weight', labelColWidth, ui.Text("Type:", align='left')), ('weight',valueColWidth,ui.Text(hdd.medium))])
        currentStatus = ui.Columns([('weight', labelColWidth, ui.Text("Current Status:", align='left')), ('weight',valueColWidth,ui.Text((hdd.status,hdd.status)))])

        if hdd._smart.tests == None:
            testsNumber = ui.Columns([('weight', 10, ui.Text("Tests:", align='left')), (ui.Text("0"))])
        else:
            testsNumber = ui.Columns([('weight', 10, ui.Text("Tests:", align='left')), (ui.Text(str(len(hdd._smart.tests))))])

        pile = ui.Pile([serial,model,size,medium,testsNumber,currentStatus])
        line = ui.LineBox(ui.Filler(pile))

        title = ui.Text((hdd.status ,str(hdd.serial) + " info: "))
        title = ui.Padding(title, left=3)
        foot = ui.Button("Exit", on_press=self.resetLayout)
        foot = ui.Padding(foot, left=3, width=10)

        frame = ui.Frame(body=line, header=title, footer=foot, focus_part='footer')
        self.loop.widget = frame


    def start(self):
        self.daemonCommThread.start()
        self.loop.run()

    def stop(self):
        self.daemonCommGo = False
        self.daemonCommThread.join()
        os.system('clear')
        print("Exited")
        raise ui.ExitMainLoop()
        exit(0)





if __name__ == '__main__':
    app = Application()
    app.start()