import threading
import datetime
import subprocess
import time

from subprocess import TimeoutExpired
from proc.tree import get_process_tree
from injectable import autowired, Autowired

from lib.tasklib.task import Task
from lib.image import ImageManager

### ImageTask needs some serious TLC. Clonezilla isn't reliable for this task. TODO: Research Partclone for this task.
class ImageTask(Task):

    display_name = "Image"

    @staticmethod
    @autowired
    def parameter_schema(task, i_s: Autowired(ImageManager), **kw):

        images_comma_separated = ', '.join('"{0}"'.format(str(image.name)) for image in i_s.discovered_images)
    
        schema = """{{
    "default": {{
        "image_name": null
    }},
    "description": "Parameters that are needed for the Image task",
    "examples": [
        {{
            "image_name": "hp_g1_26k"
        }}
    ],
    "required": [
        "image_name"
    ],
    "title": "Image task parameters",
    "properties": {{
        "image_name": {{
            "default": "",
            "description": "This is the name of the data image that should be applied to the HDD(s) in question.",
            "examples": [
                "hp_g1_26k"
            ],
            "title": "Image name",
            "enum": [
                {0}
            ],
            "type": "string"
        }}
    }},
    "additionalProperties": true
}}""".format(images_comma_separated)
        return schema
        

    def __getstate__(self):
        state = self.__dict__.copy()
        state['_pollingThread'] = None
        state['_subproc'] = None
        return state

    def __setstate__(self, state):
        self.__dict__.update(state)

    @property
    def PID(self):
        return self._PID

    @property
    def Finished(self):
        return self._returncode != None

    @autowired
    def __init__(self, hdd, i_s: Autowired(ImageManager), **kw):

        image_name = kw.get("image_name", None)
        self._image = None
        for dimage in i_s.discovered_images:
            if dimage.name == image_name:
                self._image = dimage
                break;
        
        if self._image == None:
            raise Exception("No imaged matched {0}!".format(image_name))

        #self._partitions = image.partitions.copy()
        self._diskname = hdd.node
        self._subproc = None
        self._PID = None
        self._returncode = None
        self._partclone_procview = None
        self._md5sum_procview = None
        self._proctree = None
        self._cloning = False
        self._checking = False
        self._poll = True
        self._pollingInterval = kw.get("pollingInterval", 5)
        self._pollingThread = threading.Thread(target=self._monitor, name=str(self._diskname) + "_cloneTask")
        super(ImageTask, self).__init__("Image " + self._image.name, hdd)
        self._callback = kw.get("callback", None)
        self._progress_cb = None
        
    def start(self, progress_callback=None):
        self.time_started = datetime.datetime.now(datetime.timezone.utc)
        self._subproc = subprocess.Popen(['/usr/sbin/ocs-sr', '-e1', 'auto', '-e2', '-nogui', '-batch', '-r', '-irhr', '-ius', '-icds', '-j2', '-k1', '-cmf', '-scr', '-p', 'true', 'restoredisk', self._image.name, self._diskname], stdin=subprocess.PIPE, stdout=subprocess.PIPE, stderr=subprocess.PIPE, universal_newlines=True)        
        self._PID = self._subproc.pid
        self._proctree = get_process_tree().find(pid=self.PID, recursive=True)
        self._progressString = "Loading " + self._image.name
        self._pollingThread.start()
        self._progress_cb = progress_callback
        self.notes.add("Imaging task started on this storage device. " + str(len(self._image.partitions)) + " to clone.", note_taker="hddmond")

    def _call_progress_cb(self):
        if(self._progress_cb != None) and callable(self._progress_cb):
            self._progress_cb(None, self._progressString)

    def _monitor(self):
        for i in range(len(self._image.partitions)): #The partclone.ntfs process will spawn once for each partition. Watch for partclone.ntfs as many times as there are partitions to clone.

            while self._poll == True and self._partclone_procview == None and self._md5sum_procview == None: #Watch for the creation of the partclone.ntfs process
                time.sleep(self._pollingInterval)
                self._check_subproc()
                
                self._proctree.update_descendants()
                p = self._proctree.find(exe_name='partclone.ntfs', recursive=True)
                m = self._proctree.find(exe_name='md5sum', recursive=True)
                if p != None:
                    self._partclone_procview = p
                    self._progressString = "Cloning " + self._image.name + ":" + str(i+1) + "/" + str(len(self._image.partitions))
                    self.notes.add("Cloning partition " + str(i+1) + "/" + str(len(self._image.partitions)) + " of " + self._image.name, note_taker="hddmond")
                    self._call_progress_cb()
                    self._cloning = True
                if m != None:
                    self._md5sum_procview = p
                    self._progressString = "Checking " + self._image.name
                    self.notes.add("Checking " + self._image.name + ".", note_taker="hddmond")
                    self._call_progress_cb()
                    self._checking = True

            while self._cloning == True and self._poll == True and self._md5sum_procview == None: #Wait for the end of the partclone.ntfs process, or skip these loops if we see the md5sum process. Possibility to incorrectly count partitions
                time.sleep(self._pollingInterval/4) #Increased pollrate to catch the death of the process.
                self._check_subproc()
                if(self._partclone_procview.is_alive == False):
                    self._partclone_procview = None
                    self._cloning = False
                    

        while self._poll == True and self._md5sum_procview == None: #Watch for the creation of the md5sum process
            time.sleep(self._pollingInterval)
            self._check_subproc()
            self._proctree.update_descendants()
            p = self._proctree.find(exe_name='md5sum', recursive=True)
            if p != None:
                self._md5sum_procview = p
                self._progressString = "Checking " + self._image.name
                self.notes.add("Checking " + self._image.name + ".", note_taker="hddmond")
                self._call_progress_cb()
                self._checking = True

        while self._checking == True and self._poll == True: #Wait for the end of the md5sum process
            time.sleep(self._pollingInterval/4)
            self._check_subproc()
            if(self._md5sum_procview.is_alive == False):
                self._checking = False

        while self._poll:
            time.sleep(self._pollingInterval)
            self._check_subproc()

        self.returncode = self._returncode
        self.time_started = datetime.datetime.now(datetime.timezone.utc)
        if(self._returncode == 0):
            self.notes.add("Finished imaging " + self._image.name + ".", note_taker="hddmond")
        else:
            self.notes.add("Failed imaging " + self._image.name + ".", note_taker="hddmond")
            self.notes.add("stderr:\n" + str(self.err if self.err else "Unkown error"), note_taker="hddmond")

        if(self._callback != None and callable(self._callback)):
            self._callback(self._returncode)

    def _check_subproc(self):
        try:
            self._subproc.communicate(timeout=1)
        except TimeoutExpired:
            pass
        self._returncode = self._subproc.poll()
        if(self._returncode != None): #Return code should be None until the process has exited.
            try:
                self.err = self._subproc.stderr.read()
                self.out = self._subproc.stdout.read()
            except ValueError:
                self.err = None
                self.out = None
                pass
            self._poll = False  
            
    def abort(self, wait=False):
        
        self._poll = False
        if(self._subproc):
            self._subproc.terminate()
        self.notes.add("Image task aborted.", note_taker="hddmond")
        # if(self._callback != None and callable(self._callback)):
        #     self._callback(self._returncode)
        if wait == True:
            print("\tWaiting for {0} to stop...".format(self._pollingThread.name))
            try:
                self._pollingThread.join()
            except RuntimeError:
                pass
        
#TaskService.register(ImageTask.display_name, ImageTask)