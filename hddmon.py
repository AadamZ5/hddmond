#!./env/bin/python3.8
import os, sys
os.chdir('/etc/hddmon')
print(os.getcwd())
sys.path.append('/etc/hddmon')
import subprocess
import multiprocessing.connection as ipc
import proc.core
import pyudev
from pySMART import Device
import re
import urwid as ui
import additional_urwid_widgets as ui_special
import pySMART
import time
import threading
from hddmondtools.hddmon_dataclasses import HddData, TaskData, TaskQueueData
from hddmontools.hdd import Hdd, HddViewModel, HealthStatus, TaskStatus
from hddmontools.task import TaskQueue
from hddmontools.pciaddress import PciAddress
from hddmontools.portdetection import PortDetection

euid = os.geteuid()
if euid != 0:
    print("May I have root privledges? Without them 'htop' may not list disk usage correctly.")
    inp = input("Please enter yes or no: ")
    if ('y' in inp.strip().lower()):
        args = ['sudo', sys.executable] + sys.argv + [os.environ]
        # the next line replaces the currently-running process with the sudo
        os.execlpe('sudo', *args)
    else:
        print("Not elevated.")
        time.sleep(1.25)



debug = False
def logwrite(s:str, endl='\n'):
    if(debug):
        fd = open("./main.log", 'a')
        fd.write(s)
        fd.write(endl)
        fd.close()

class HddTestsWidget(ui.WidgetWrap):
    def __init__(self, tests=None):
        self._tests = (tests if tests != None else [])
        self._rows_ = []

        for t in self._tests:
            label = ui.Text(str(t))
            self._rows_.append(label)

        self._listwalker = ui.SimpleListWalker()
        self._list = ui_special.IndicativeListBox

class TaskQueueWidget(ui.WidgetWrap):

    @property
    def paused(self):
        return self._tq.Pause

    def __init__(self, serial, taskqueue: TaskQueueData, task_up_cb=None, task_dn_cb=None, task_del_cb=None, pause_cb=None):
        self._rows_ = []
        self._tq = taskqueue
        self._t_u_cb = task_up_cb
        self._t_d_cb = task_dn_cb
        self._t_r_cb = task_del_cb
        self._p_cb = pause_cb
        self._serial = serial
        self._gen_rows()
        self._listwalker = ui.SimpleFocusListWalker(self._rows_)
        self._list = ui_special.IndicativeListBox(self._listwalker)
        self._pause_button = ui.Button(('Pause' if not self._tq.paused else 'Unpause'), on_press=self._pause, user_data=self.paused)
        self._pile = ui.Pile([('pack',self._pause_button), self._list])
        #self._pile = ui.Divider()
        self._box = ui.LineBox(self._pile)
        super(TaskQueueWidget, self).__init__(self._box)

    def _gen_rows(self):
        self._rows_.clear()
        for i in range(len(self._tq.queue)):
            task = self._tq.queue[i]
            n = ui.Text(str(i+1) + ": ")
            bup = ui.Button('▲', on_press=self._taskdown, user_data=i)
            bdn = ui.Button('▼', on_press=self._taskup, user_data= i)
            babrt = ui.Button('X', on_press=self._taskdel, user_data=i)
            name = ui.Text(task.name)
            col = ui.Columns([('pack',n), name, (5,bup),(5,bdn),(5,babrt)])
            self._rows_.append(col)
        _offset = len(self._rows_)
        self._rows_.append(ui.Divider())
        self._rows_.append(ui.Text(('options','▼ completed tasks ▼'), align='center'))
        for i in range(len(self._tq.completed)):
            oldt = self._tq.completed[i]
            n = ui.Text(('options',str(i+1) + ": "))
            name = ui.Text(('options',str(oldt)))
            col = ui.Columns([('pack',n), name])
            self._rows_.append(col)

        self._listwalker = ui.SimpleFocusListWalker(self._rows_)


    def _taskup(self, button, index=None, *args, **kwargs):
        if(self._t_u_cb != None and callable(self._t_u_cb)):
            self._t_u_cb(index=index, callback=self._cb_u, serial=self._serial)

    def _taskdown(self, button, index=None, *args, **kwargs):
        if(self._t_d_cb != None and callable(self._t_d_cb)):
            self._t_d_cb(index=index, callback=self._cb_d, serial=self._serial)

    def _taskdel(self, button, index=None, *args, **kwargs):
        if(self._t_r_cb != None and callable(self._t_r_cb)):
            self._t_r_cb(index=index, callback=self._cb_r, serial=self._serial)

    def _cb_u(self, *args, **kwargs):
        data = args[0]
        pass

    def _cb_d(self, *args, **kwargs):
        data = args[0]
        pass

    def _cb_r(self, *args, **kwargs):
        data = args[0]
        pass

    def _cb_p(self, *args, **kwargs):
        data = args[0]
        pass        

    def _pause(self, button, pause):
        if(self._p_cb != None and callable(self._p_cb)):
            self._p_cb(callback=self._cb_p, serial=self._serial, pause=(not self._tq.paused))

    def _update(self, taskQueue: TaskQueueData):
        self._tq = taskQueue
        self._pause_button.set_label(('Pause' if not self._tq.paused else 'Unpause'))
        self._rows_.clear()
        self._gen_rows()

class HddWidget(ui.WidgetWrap):
    def __init__(self, hdd: HddData, app):
        self.hdd = hdd
        self.__app__ = app
        self._checked = False
        self._id = ui.Text((self.hdd.status, str(self.hdd.serial)), align='left')
        self._node = ui.Text(('text',self.hdd.node), align='center')
        #self._pci = ui.Text(str(self.hdd.OnPciAddress), align='center')
        self._task = ui.Text((self.hdd.status, str(self.hdd.task_queue.current_task.string_rep if self.hdd.task_queue.current_task != None else "Idle")), align='center')
        self._port = ui.Text(('text',str(self.hdd.port)), align='center')
        self._cap = ui.Text(('text',(str(self.hdd.capacity))), align='center')
        self._stat = ui.Text((self.hdd.status, self.hdd.assessment), align='center')
        self._check = ui.CheckBox(('text',''), state=self._checked)
        self._check_wrap = ui.AttrMap(self._check, 'line', focus_map=self.__app__.focus_map)
        self._more = ui.Button(('text',"Info"), on_press=self.__app__.ShowHddInfo, user_data=self) #TODO FIx
        self._morewidget = ui.AttrMap(self._more, 'line', focus_map=self.__app__.focus_map)
        self._morewidget = ui.Padding(self._morewidget, align='center')

        self._col = ui.Columns([(4,self._check_wrap), ('weight', 35, self._id), ('weight', 20, self._port), ('weight', 20, self._cap), ('weight', 15, self._node), ('weight', 25, self._task), ('weight', 10, self._stat), (10, self._morewidget)])
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

        if(self.hdd.status == HealthStatus.ShortTesting) or (self.hdd.status == HealthStatus.LongTesting):
            self._stat.set_text((self.hdd.status, str(self.hdd.task_queue.current_task.progress)))
        else:
            self._stat.set_text((self.hdd.status, str(self.hdd.assessment)))
        
        if(self.hdd.status != TaskStatus.Idle):
            self._task.set_text((self.hdd.status, str(self.hdd.task_queue.current_task.string_rep) + (" (" + str(len(self.hdd.task_queue.queue)) + ")" if len(self.hdd.task_queue.queue) > 0 else "")))
            self._cap.set_text((self.hdd.status, self.hdd.size))
        else:
            self._task.set_text((self.hdd.status, "Idle" + (" (" + str(len(self.hdd.task_queue.queue)) + ")" if len(self.hdd.task_queue.queue) > 0 else "")))
            self._cap.set_text(('text',self.hdd.size))

    def get_attr_map(self):
        return self._main.get_attr_map()
    def set_attr_map(self, attr):
        return self._main.set_attr_map(attr)

class Commander:
    def __init__(self, address, key):
        self.daemonAddress = address
        self.daemonKey = key
        self.commandQueue = []
        self._daemon_comm = True
        self.connection = None
        try:
            self.connection = ipc.Client(self.daemonAddress, authkey=self.daemonKey)
        except Exception as e:
            print("A connection could not be established to the testing server: \n" + str(e))
            exit(1)
        print("Connected!")
        self._curr_cmd = None
        self._queue_thread = None
        self._daemon_thread = threading.Thread(target=self.daemonComm, name='commanding_thread')

    def send_command(self, command, data={}, callback=None, *args, **kwargs):
        if('connection' in self.__dict__) and (self.connection.closed != True):
            cb = callback
            self.commandQueue.append((str(command), data, cb))
            if(len(self.commandQueue) == 1 and self._curr_cmd == None): #We added the first task of this chain-reaction. Kick off the queue.
                self._create_queue_thread()
            return True
        else:
            return False

    def _create_queue_thread(self):
        self._queue_thread = threading.Thread(target=self.daemonComm)
        self._queue_thread.start()

    def stop(self):
        self._daemon_comm = False
        self.commandQueue.clear()
        try:
            if('connection' in self.__dict__):
                self.connection.close()
            else:
                pass
        except Exception as e:
            pass

    def daemonComm(self):
        while self._daemon_comm and ('connection' in self.__dict__) and (len(self.commandQueue) > 0 or self._curr_cmd != None ):
            if(len(self.commandQueue) == 0):
                pass
            else:
                if not len(self.commandQueue) > 0:
                    continue
                self._curr_cmd = self.commandQueue.pop()
                cmd = (self._curr_cmd[0],self._curr_cmd[1]) #(command, data, callback)
                if(len(self._curr_cmd) >2):
                    callback = self._curr_cmd[2]
                else:
                    callback = None
                self.connection.send(cmd)
                try:
                    data = self.connection.recv()#blocking call
                except EOFError:
                    data = None
                    del self.connection
                    break
                if(data != None):
                    if(callback) and callable(callback):
                        callback(data)
        
commander = Commander(('localhost', 63962), b'H4789HJF394615R3DFESZFEZCDLPOQ')

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
        (HealthStatus.Failing, 'light red',        'black'),
        (HealthStatus.Default, 'light gray', 'black'),
        (HealthStatus.Passing, 'light green', 'black'),
        (HealthStatus.ShortTesting, 'yellow', 'black'),
        (HealthStatus.Warn, 'black', 'yellow'),
        (HealthStatus.Unknown, 'light gray', 'dark red'),
        (HealthStatus.LongTesting, 'light magenta', 'black'),
        (TaskStatus.Erasing, 'light cyan', 'black'),
        (TaskStatus.Idle, 'dark gray', 'black'),
        (TaskStatus.External, 'dark blue', 'black'),
        (TaskStatus.Error, 'dark red', 'black'),
        (TaskStatus.Imaging, 'black', 'dark blue'),
        (TaskStatus.ShortTesting, 'yellow', 'black'),
        (TaskStatus.LongTesting, 'light magenta', 'black'),]
        
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
        self.images = []
        self.buildControls()

        self.loop = ui.MainLoop(self.MainFrame, self.palette, pop_ups=True, unhandled_input=self.unhandled_input)
        self.Terminal.main_loop = self.loop
        self.loop.set_alarm_in(0.5, self._update, user_data=None)
        ui.connect_signal(self.Terminal, 'closed', callback=self._reinitializeTerminal)

        self.bigBoxes = [self.HddListUi, self.SubControls, self.Htop]
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

        self.ShortTest = ui.AttrMap(ui.Button(('text',"Short test"), on_press=self._send_command, user_data={'command': 'shorttest', 'data': self._getSelectedSerials, 'loading_message': 'Starting short test(s)...', 'callback': self.resetLayout}), 'line', focus_map=self.focus_map)
        self.LongTest = ui.AttrMap(ui.Button(('text',"Long test"), on_press=self._send_command, user_data={'command': 'longtest', 'data': self._getSelectedSerials, 'loading_message': 'Starting long test(s)...', 'callback': self.resetLayout}), 'line', focus_map=self.focus_map)
        self.AbortTest = ui.AttrMap(ui.Button(('text',"Abort test"), on_press=self._send_command, user_data={'command': 'aborttest', 'data': self._getSelectedSerials, 'loading_message': 'Aborting test(s)...', 'callback': self.resetLayout}), 'line', focus_map=self.focus_map)
        self.Erase = ui.AttrMap(ui.Button(('text',"Erase disk"), on_press=self.ShowAreYouSureDialog, user_data=[["Erase drives?"], self._erase]), 'line', focus_map=self.focus_map)
        self.Clone = ui.AttrMap(ui.Button(('text',"Apply image"), on_press=self.GetTheImages, user_data={'callback': self.GotTheImages}), 'line', focus_map=self.focus_map)
        self.AbortTask = ui.AttrMap(ui.Button(('text',"Abort task"), on_press=self.ShowAreYouSureDialog, user_data=[["Abort task?\n", 'This will terminate external processes!'], self._abort_task]), 'line', focus_map=self.focus_map)
        self.ExitButton = ui.AttrMap(ui.Button(('exit',"Exit"), on_press=self.exit), 'line', focus_map=self.focus_map)

        self.scEntries = ui.SimpleListWalker([self.ShortTest, self.LongTest, self.AbortTest, ui.Divider(), self.Erase, self.Clone, self.AbortTask, ui.Divider(), self.ExitButton])
        self.SubControls = ui_special.IndicativeListBox(self.scEntries)
        self.SubControls = ui.LineBox(self.SubControls)
        self.SubControls = ui.AttrMap(self.SubControls, None, focus_map='focus border')
        self.SubControls = ui.Frame(header=ui.Text("HDD Options", align="center", wrap="clip"), body=self.SubControls)

        self.Top = ui.Columns([('weight', 70, self.HddListUi), ('weight', 30, self.SubControls)], min_width=15)

        self.MainFrame = ui.Pile([self.Top, self.Htop])
        self.MainFrame = ui.Filler(self.MainFrame, 'middle', 80)

    def _update(self, loop, userargs, *args, **kwargs):
        self._poll_daemon()
        self._checkTerminalFocus(loop, userargs)
        loop.set_alarm_in(0.5, self._update)

    def _poll_daemon(self, *args, **kwargs):
        commander.send_command('hdds', callback=self.processHddData)

    def unhandled_input(self, key, *args, **kwargs):
        k = str(key).lower().strip()
        if k == 'ctrl a':
            self._select_all()
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

    def _select_all(self):
        self._all_selected = True
        for hw in self.hddEntries:
            if hw.checked == False:
                self._all_selected = False

        for hw in self.hddEntries:
            hw.setChecked(not self._all_selected)

    def _getSelected(self):
        selected = []
        for hw in self.hddEntries:
            if hw.checked == True:
                selected.append(hw)

        return selected

    def _getSelectedSerials(self):
        serials = []
        for hw in self.hddEntries:
            if hw.checked == True:
                serials.append(hw.hdd.serial)

        return {'serials': serials}

    def _checkTerminalFocus(self, loop, user_data):
        if self.Terminal.keygrab:
            self.terminalBorder.set_focus_map({None: 'active border'})
        else:
            self.terminalBorder.set_focus_map({None: 'focus border'})
        #loop.set_alarm_in(0.5, self._checkTerminalFocus, user_data=None)

    def _send_command(self, button=None, userargs={}):
        
        command = userargs.get('command', None)
        if command is None:
            return
        data = userargs.get('data', None)
        if callable(data):
            data = data()
        callback = userargs.get('callback', None)
        loadingmsg = userargs.get('loading_message', None)
        commander.send_command(command, data=data, callback=callback)
        self.ShowLoadingDialog(text=[loadingmsg if loadingmsg != None else 'Loading...'])
        for hw in self._getSelected():
            hw.setChecked(False)

    def _erase(self, button=None, *args, **kwargs):
        self._send_command(userargs={'command': 'erase', 'data': self._getSelectedSerials, 'callback': self.resetLayout, 'loading_message': 'Starting erase task(s)...'})

    def _abort_task(self, button=None, *args, **kwargs):
        self._send_command(userargs={'command': 'aborttask', 'data': self._getSelectedSerials, 'callback': self.resetLayout, 'loading_message': 'Aborting task(s)...'})

    def GetTheImages(self, *args, **kwargs):
        self.ShowLoadingDialog(text=['Getting images...'])
        self.loop.draw_screen()
        commander.send_command('getimages', callback=self.GotTheImages)

    def GotTheImages(self, *args, **kwargs):
        self.processImages(args[0][1])
        self.ShowImagePickDialog(args=[self.images, self.commandImage])
        

    def commandImage(self, *args, **kwargs):
        serialList = self._getSelectedSerials()
        image = None
        if(len(args) > 0):
            image = args[0]
        if(len(serialList) == 0):
            self.ShowErrorDialog(text=['No hard drives selected'])
            return
        if(image == None):
            return
        commander.send_command('image', data={'image': image.name, 'serials': serialList['serials']}, callback=self.resetLayout)
        self.ShowLoadingDialog(text=['Starting image(s)...'])

    def processHddData(self, response):
        #data is (response, data)
        data = response[1]
        hdds = data.get('hdds', None)
        if hdds == None:
            return
        self.hddobjs = hdds
        localhdds = list(hdds).copy()
        foundhdds = []

        for hw in self.hddEntries:#look for hdds in here.

            found = False
            for h in localhdds:
                if(str(h.serial) == str(hw.hdd.serial)) and not (h in foundhdds):
                    hvm = HddViewModel.FromHdd(h)
                    hw.Update(hvm) #Update the widget with the new hdd info
                    foundhdds.append(h)
                    found = True
                    break 
            
            if found == False: #Found = false, remove the widget.
                self.hddEntries.remove(hw)
        
        for h in foundhdds:#Hdd objects found, remove from the localhdds list
            for hr in localhdds:
                if hr.serial == h.serial:
                    localhdds.remove(hr)

        for hrem in localhdds: #Process the leftover hdds for which we didn't have a widget currently representing
            hddwidget = HddWidget(hrem, self)
            self.hddEntries.append(hddwidget)

    def processImages(self, data):
        images = data.get('images', None)
        if images == None:
            self.ShowErrorDialog(text=['No images were recieved.'])
            return
        self.images = images
        self.images.reverse()

    def _reinitializeTerminal(self, loop, **kwargs):
        self.Terminal = ui.Terminal(['bash'], main_loop=self.loop, escape_sequence='tab')
        self.terminalBorder = ui.LineBox(self.Terminal)
        self.terminalBorder = ui.AttrMap(self.terminalBorder, None, focus_map='focus border')
        self.Htop.set_body(self.terminalBorder)
        ui.connect_signal(self.Terminal, 'closed', callback=self._reinitializeTerminal)

    def resetLayout(self, button=None, t=None):
        #t should be (bool, truecallback, falsecallback, data) or None
        self.MainFrame = ui.Pile([self.Top, self.Htop])
        self.loop.widget = self.MainFrame

        if(t): #t != None
            if(type(t) == tuple):
                if(len(t) > 1):
                    if(t[0]): #if bool is true
                        if(t[1]):
                            if(len(t) > 3):
                                t[1](t[3])
                            else:
                                t[1]() #true callback
                    else:
                        if(len(t) > 2): #if there even is a false callback
                            if(t[2]): #if the third item isn't None
                                if(len(t) > 3):
                                    t[2](t[3])
                                else:
                                    t[2]() #false callback
            else:
                pass

    def exit(self, button=None, args=None):
        self.ShowExitDialog()
        self.loop.draw_screen()
        self.stop()

    def ShowLoadingDialog(self, button=None, text = ['']):

        # Header
        header_text = ui.Text(('banner', 'Please wait'), align = 'center')
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
        
        labelColWidth = 15
        valueColWidth = 85

        serial = ui.Columns([('weight', labelColWidth, ui.Text("Serial:", align='left')), ('weight',valueColWidth,ui.Text(hdd.serial))])
        model = ui.Columns([('weight', labelColWidth, ui.Text("Model:", align='left')), ('weight',valueColWidth,ui.Text(hdd.model))])
        size = ui.Columns([('weight', labelColWidth, ui.Text("Size:", align='left')), ('weight',valueColWidth,ui.Text(hdd.Size))])
        medium = ui.Columns([('weight', labelColWidth, ui.Text("Type:", align='left')), ('weight',valueColWidth,ui.Text(hdd.medium))])
        currentStatus = ui.Columns([('weight', labelColWidth, ui.Text("Current Status:", align='left')), ('weight',valueColWidth,ui.Text((hdd.status,str(hdd.status))))])

        if hdd._smart.tests == None:
            testsNumber = ui.Columns([('weight', labelColWidth, ui.Text("Tests:", align='left')), ('weight',valueColWidth,(ui.Text("0", align='left')))])
            testsList = ui.Columns([('weight', labelColWidth, ui.Text("...", align='left')), ('weight', valueColWidth, ui.Text(''))])
        else:
            testsNumber = ui.Columns([('weight', labelColWidth, ui.Text("Tests:", align='left')), ('weight',valueColWidth,(ui.Text(str(len(hdd._smart.tests)), align='left')))])
            testObjs = []
            for t in hdd._smart.tests:
                testObjs.append(ui.Text(str(t)))
            testsList = ui.Columns([('weight', labelColWidth, ui.Text("...", align='left')), ('weight', valueColWidth, ui.BoxAdapter(ui.ListBox(ui.SimpleListWalker(testObjs)), 10))])


        def task_up(*args, **kwargs):
            index = kwargs.get('index', None)
            cb = kwargs.get('callback', None)
            serial = kwargs.get('serial', None)
            action = 'up'
            commander.send_command('modifyqueue', data={'index': index, 'action': action, 'serial': serial}, callback=cb)

        def task_dn(*args, **kwargs):
            index = kwargs.get('index', None)
            cb = kwargs.get('callback', None)
            serial = kwargs.get('serial', None)
            action = 'down'
            commander.send_command('modifyqueue', data={'index': index, 'action': action, 'serial': serial}, callback=cb)

        def task_rm(*args, **kwargs):
            index = kwargs.get('index', None)
            cb = kwargs.get('callback', None)
            serial = kwargs.get('serial', None)
            action = 'remove'
            commander.send_command('modifyqueue', data={'index': index, 'action': action, 'serial': serial}, callback=cb)

        def pause(*args, **kwargs):
            cb = kwargs.get('callback', None)
            serial = kwargs.get('serial', None)
            pause = kwargs.get('pause', None)
            commander.send_command('pausequeue', data={'serials': [serial,], 'pause': pause}, callback=cb)

        taskqueues = TaskQueueWidget(hdd.serial, hdd.TaskQueue, task_up_cb=task_up, task_dn_cb=task_dn, task_del_cb=task_rm, pause_cb=pause)
        taskqueues = ui.BoxAdapter(taskqueues, 12)
        taskqueues = ui.Columns([('weight', labelColWidth, ui.Text("Queued tasks:", align='left')), ('weight', valueColWidth, ui.Padding(taskqueues, min_width=15, width=('relative', 30)))])

        blacklist = ui.Button("Blacklist drive", on_press=self._send_command, user_data={'command': 'blacklist', 'data': {'serials': [hdd.serial,]}, 'callback': self.resetLayout})
        blacklist = ui.Padding(blacklist, width=('relative', labelColWidth))

        ex = ui.Button("Exit", on_press=self.resetLayout)
        ex = ui.Padding(ex, width=('relative', labelColWidth))

        pile = ui.Pile([serial,model,size,medium,testsNumber,testsList,currentStatus,taskqueues,blacklist,ui.Divider(),ex])
        line = ui.LineBox(ui.Filler(pile))

        title = ui.Text((hdd.status, str(hdd.serial) + " info: "))
        title = ui.Padding(title, left=3)

        frame = ui.Frame(body=line, header=title, focus_part='body')
        self.loop.widget = frame

    def ShowImagePickDialog(self, button=None, args = []):
        
        #args is a [[DiskImage, DiskImage], callback]
        text = 'Which image?'

        callback = None
        if(len(args) > 1):
            yescallback = args[1]
            
        if(len(args) > 2):
            nocallback = args[2]
        else:
            nocallback = None

        imgs = []
        for image in args[0]:
            button = ui.Button(image.name, on_press=self.resetLayout, user_data=(True, yescallback, nocallback, image))
            imgs.append(button)

        # Header
        header_text = ui.Text(('banner', 'Choose an option'), align = 'center')
        header = ui.AttrMap(header_text, 'banner')

        # Body
        cancel = ui.Button('Cancel', self.resetLayout, user_data=(False, yescallback, nocallback))
        cancel = ui.AttrWrap(cancel, 'selectable', 'focus')
        cancel = ui.Filler(cancel, valign='middle')

        body_text = ui.Text(text, align = 'center')
        body_filler = ui.Filler(body_text, valign = 'middle')
        body_list = ui_special.IndicativeListBox(ui.SimpleFocusListWalker(imgs))
        body_contents = ui.Pile([body_filler, body_list, cancel])
        body_padding = ui.Padding(
            body_contents,
            left = 1,
            right = 1
        )
        body = ui.LineBox(body_padding)

        # Footer
        cancel = ui.Button('Cancel', self.resetLayout, user_data=(False, yescallback, nocallback))
        cancel = ui.AttrWrap(cancel, 'selectable', 'focus')
        footer = ui.Columns([cancel])
        footer = ui.GridFlow([footer], 20, 1, 1, 'center')

        # Layout
        layout = ui.Frame(
            body,
            header = header,
            focus_part = 'body'
        )

        w = ui.Overlay(
            ui.LineBox(layout),
            self.Top,
            align = 'center',
            width = 75,
            valign = 'middle',
            height = 30
        )
        self.MainFrame = ui.Pile([w, self.Htop])
        self.loop.widget = self.MainFrame

    def start(self):
        self.loop.run()

    def stop(self):
        os.system('clear')
        commander.stop()
        print("Exited")
        raise ui.ExitMainLoop()
        exit(0)

if __name__ == '__main__':
    #commander = Commander(('localhost', 63962), b'H4789HJF394615R3DFESZFEZCDLPOQ')
    app = Application()
    app.start()