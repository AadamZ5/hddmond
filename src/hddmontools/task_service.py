import logging

#from .task import Task
from injectable import injectable, inject

@injectable(singleton=True)
class TaskService:
    """
    Task service should be used by local devices to get the names of available tasks. 
    Outsider devices that are remotely connected specify their own tasks, and do not
    recieve special treatment.
    """

    _class_buffer = {}
    _name_buffer = {}

    def __init__(self):
        self.logger = logging.getLogger(__name__ + "." + self.__class__.__qualname__)
        self.logger.setLevel(logging.DEBUG)
        self.logger.info("Initializing TaskService...")
        self.task_types = TaskService._class_buffer
        self.display_names = TaskService._name_buffer

    def initialize(self):
        self.logger.debug("Reinitializing TaskService...")
        for key in TaskService._class_buffer.keys():
            self.task_types[key] = TaskService._class_buffer[key]
        
        for key in TaskService._name_buffer.keys():
            self.display_names[key] = TaskService._name_buffer[key]

    @staticmethod
    def register(display_name: str, task_class):
        TaskService._class_buffer[task_class.__name__] = task_class
        TaskService._name_buffer[display_name] = task_class.__name__

        # try:
        #     task_svc = inject(TaskService)
        #     task_svc.task_types[task_class.__name__] = task_class
        #     task_svc.display_names[display_name] = task_class.__name__
        # except:
        #     pass