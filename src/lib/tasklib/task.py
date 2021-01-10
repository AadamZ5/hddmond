import enum

from abc import ABC, abstractmethod

from lib.notes import Notes

class TaskResult(enum.Enum):
    FINISHED = 1,
    ERROR = 0,

class Task(ABC):

    display_name = "Task"

    @staticmethod
    def GetTaskParameterSchema(task):
        s: str = None

        if task.parameter_schema == None:
            return None

        if callable(task.parameter_schema):
            s = task.parameter_schema(task)
        else:
            s = str(task.parameter_schema)
        return s
            

    """_parameter_schema holds JSON Schema that defines the properties needed for a task to initialize. This can be callable, or just a static property."""
    parameter_schema = None

    def __init__(self, taskName, hdd):
        self.name = taskName
        self._progressString = self.name
        self._callback = None
        self.returncode = None
        self.notes = Notes()
        self.time_started = None
        self.time_ended = None

    @property
    def Progress(self):
        '''
        When overridden in a sub-class implimentation, provides the progress of a current task.
        -1 should symbolize no progress available to report.
        '''
        return -1

    @property
    def ProgressString(self):
        '''
        Returns the _progressString of a task
        '''
        return self._progressString

    @property
    def PID(self):
        '''
        When overridden in a sub-class implimentation, provides the PID of a task. 
        '''
        return 0

    @property
    @abstractmethod
    def Finished(self):
        return True

    @abstractmethod
    def start(self, progress_callback=None):
        '''
        Should be overridden in sub-classes to define the starting point of the operation.
        This is necessary for task-queues.
        '''
        pass

    @abstractmethod
    async def abort(self, wait=False):
        '''
        Should be overridden in a sub-class to provide the implimentation of aborting the task.
        If wait is true, the method should wait to return until the task is totally aborted.
        '''
        pass
