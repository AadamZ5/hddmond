import asyncio
import threading

from typing import Coroutine

import strawberry

from lib.tasklib.taskqueue_interface import TaskQueueInterface
from lib.tasklib.task import Task

@strawberry.type(description="The task queue holds pending and in-progress tasks")
class TaskQueue(TaskQueueInterface): #TODO: Use asyncio for polling and looping!
    '''
    A container that manages and handles a queue of multiple tasks.
    '''

    def __getstate__(self):
        state = self.__dict__.copy()
        state['_queue_thread'] = None #Can't pickle thread objects
        state['_task_change_callback'] = None #Don't pickle callback objects
        return state

    @property
    def Pause(self):
        return self._pause

    @Pause.setter
    def Pause(self, value: bool):
        if (self._pause == True and value == False):
            self._pause = value
            if(self.CurrentTask == None):
                self._create_queue_thread()
        else:
            self._pause = value
        self._taskchanged_cb(action='pausechange', data={'paused': self._pause})

    def _get_paused(root):
        return root.Pause

    _paused: bool = strawberry.field(description="If the task queue is paused or not", name="paused", resolver=_get_paused)

    @property
    def Error(self):
        return self._error

    @Error.setter
    def Error(self, value: bool):
        self._error = value
        self._taskchanged_cb(action='errorchange', data={'error': self._error})

    def _get_error(root):
        return root.Error

    _error: bool = strawberry.field(description="True if a pending task encountered an error", name="error", resolver=_get_error)

    @property
    def Full(self):
        return len(self.Queue) >= self.maxqueue

    def _get_full(root):
        return root.Full

    _full: bool = strawberry.field(description="If the queue is full, if applicable", name="full")

    def __init__(self, maxqueue=8, between_task_wait=1, continue_on_error=True, task_change_callback=None, queue_preset=None):
        self.maxqueue = maxqueue
        self.CurrentTask = None
        self._currentcb = None
        self.between_task_wait = between_task_wait
        self.continue_on_error = continue_on_error
        self._pause = False
        self._error = False
        self._queue_thread = None
        if(queue_preset == None):
            queue_preset = []
        else:
            if(len(queue_preset) > self.maxqueue):
                self.Queue = (queue_preset[0:self.maxqueue-1]).copy() #Only take the maximum allowed tasks from the preset.
        self.Queue = queue_preset #list of (preexec_cb, task, callback)
        self.history = []
        self._task_change_callback = task_change_callback
        self._loop = asyncio.get_event_loop()

    def AddTask(self, task: Task, preexec_cb=None, index=None):
        '''
        Appends a task to the task queue, if it is not full.
        Returns a bool True if successfull.
        '''
        if not (self.Full):
            cb = task._callback 
            task._callback = self._taskcb #Hijack the callback so we can catch when the task is done.
            if(index != None):
                if(index >= self.maxqueue):
                    raise IndexError("Index out of range 0-" + str(self.maxqueue-1))
                else:
                    self.Queue.insert(index, (preexec_cb, task, cb))
            else:
                self.Queue.append((preexec_cb, task, cb))
            if(len(self.Queue) == 1 and self.CurrentTask == None): #We added the first task of this chain-reaction. Kick off the queue.
                self._create_queue_thread()
            self._taskchanged_cb(action='taskadded', data={'taskqueue': self})
            return True
        else:
            return False

    def _taskcb(self, returncode, *args, **kwargs):

        #   _taskcb(...) is called when a task finished, no matter the return code. This method is injected into the task's _callback attribute during the AddTask(...) method, and the original callback is stored.
        #   This method is responsible for continuing the chain of task running, if any tasks are left. Also, this method is responsible for pausing the queue if a task fails, and the continue_on_error attribute is False.

        self.history.insert(0, self.CurrentTask)#First element is always most recent task.

        if(self._currentcb != None and callable(self._currentcb)): #Call the original callback associated with the completed task
            self._currentcb(returncode)

        if(int(returncode) != 0):
            self.Error = True
            if(self.continue_on_error == False):
                self.Pause = True

        self.CurrentTask = None
        self._currentcb = None
        self._taskchanged_cb(action='taskfinished', data={'task': self.CurrentTask})
        if(self.Pause == True):
            return
        else:
            self._create_queue_thread()

    def _task_progresscb(self, progress=None, string=None):
        """
        Helper method to notify the progress of the current task.
        """
        self._taskchanged_cb(action='taskprogress', data={'taskqueue': self})

    def _create_queue_thread(self):
        """
        Helper method to create the queue thread if none exists in the moment.
        """
        if threading.current_thread() != threading.main_thread():
            async def thread_shim():
                nonlocal self
                asyncio.get_event_loop().create_task(self._launch_new_task())
            asyncio.run_coroutine_threadsafe(thread_shim())
        else:
            loop = asyncio.get_event_loop()
            self._queue_thread = loop.create_task(self._launch_new_task()) #This async task should exit soon after the start() function of the task exits. This async task is just to offload the sleep between tasks, and detach from the last finished thread.
    
    async def _launch_new_task(self): 

        #   This method holds the logic for determining to run another task.

        if(len(self.Queue) != 0) and self.Pause != True:
            await asyncio.sleep(self.between_task_wait)
            tup = self.Queue.pop(0)
            pcb = tup[0]
            t = tup[1]
            cb = tup[2]
            if(pcb != None and isinstance(pcb, Coroutine)):
                await pcb()
            elif(pcb != None and callable(pcb)):
                pcb()
            self.CurrentTask = t
            self._currentcb = cb
            self._taskchanged_cb(action='tasklistmod', data={'taskqueue': self})
            self.CurrentTask.start(progress_callback=self._task_progresscb)
        else:
            return

    def GetAllNotes(self):
        '''
        Returns a complete list of all task notes from the current session in no particular order.
        '''
        allNotes = {}
        if self.CurrentTask != None:
            allNotes.update(self.CurrentTask.notes.entries)
        for t in self.history:
            allNotes.update(t.notes.entries)
        for _tuple in self.Queue:
            t = _tuple[1]
            allNotes.update(t.notes.entries)

        return allNotes
        
    def PushUp(self, current_index):
        '''
        Pushes a task up in the queue
        '''
        lastpause = self.Pause
        self.Pause = True
        last_index = len(self.Queue)-1 #Don't shove above our max index
        if(current_index >= last_index):
            return
        try:
            t = self.Queue[current_index]
            del self.Queue[current_index]
        except IndexError:
            return

        self.Queue.insert(current_index+1, t)
        self.Pause = lastpause
        self._taskchanged_cb(action='tasklistmod', data={'taskqueue': self})

    def PushDown(self, current_index):
        '''
        Pushes a task down in the queue
        '''
        lastpause = self.Pause
        self.Pause = True
        if(current_index <= 0): #Dont shove below 0 index
            return
        try:
            t = self.Queue[current_index]
            del self.Queue[current_index]
        except IndexError:
            return

        self.Queue.insert(current_index-1, t)
        self.Pause = lastpause
        self._taskchanged_cb(action='tasklistmod', data={'taskqueue': self})

    def SetIndex(self, current_index, new_index):
        '''
        Sets the index of a task in the queue within the bounds of the current list size.
        '''
        lastpause = self.Pause
        self.Pause = True
        if(new_index < 0): #Dont shove below 0 index
            return
        last_index = len(self.Queue)-1 
        if(new_index > last_index): #Don't shove above our max index
            return
        t = self.Queue[current_index]
        del self.Queue[current_index]
        self.Queue.insert(new_index, t)
        self.Pause = lastpause
        self._taskchanged_cb(action='tasklistmod', data={'taskqueue': self})

    def RemoveTask(self, index):
        '''
        Removes a task at index.
        '''
        lastpause = self.Pause
        self.Pause = True
        if index < 0 or index > self.maxqueue-1 or index > len(self.Queue)-1:
            return False
        del self.Queue[index]
        self.Pause = lastpause
        self._taskchanged_cb(action='tasklistmod', data={'taskqueue': self})

    def AbortCurrentTask(self, pause=True):
        '''
        Aborts the current task.
        '''
        if(self.CurrentTask != None):
            self.Pause = pause
            t = self.CurrentTask
            self.CurrentTask.abort()
            self._taskchanged_cb(action='taskabort', data={'task': t})
        
    def _taskchanged_cb(self, *args, **kw):

        #   Helper method to notify when some aspect of the task queue is changed.

        if not hasattr(self, '_task_change_callback'):
            return

        if self._task_change_callback != None and callable(self._task_change_callback):
            if threading.current_thread() != threading.main_thread():

                #! Important! Since some tasks use threads to call back, higher-up async stuff will fail!
                #  Use loop.call_soon_threadsafe or asyncio.run_coroutine_threadsafe to schedule async tasks back in the main loop.

                async def _callback_shim():
                    nonlocal self
                    nonlocal args
                    nonlocal kw
                    self._task_change_callback(*args, **kw)

                asyncio.run_coroutine_threadsafe(_callback_shim(), self._loop)
            else:
                if(isinstance(self._task_change_callback, Coroutine)):
                    asyncio.get_event_loop().create_task(self._task_change_callback(*args, **kw))
                else:
                    self._task_change_callback(*args, **kw)