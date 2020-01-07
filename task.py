from abc import ABC, abstractmethod, abstractproperty
import subprocess
import proc

class Task(ABC, subprocess.Popen, proc.core.Process):
    def __init__(self):


    @property
    def pid(self):
        return self.proc.pid()

    @property
    def uptime(self):


    