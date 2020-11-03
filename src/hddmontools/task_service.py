#from .task import Task
from injectable import injectable, inject

@injectable(singleton=True)
class TaskService:
    """
    Task service should be used by local devices to get the names of available tasks. 
    Outsider devices that are remotely connected specify their own tasks, and do not
    recieve special treatment.
    """

    def __init__(self):
        self.task_types = {}
        self.display_names = {}

    @staticmethod
    def register(display_name: str, task_class):
        try:
            task_svc = inject(TaskService)
            task_svc.task_types[task_class.__name__] = task_class
            task_svc.display_names[display_name] = task_class.__name__
        except:
            pass