from abc import ABC, abstractmethod
import functools
import inspect

class ApiInterface(ABC):
    
    def __init__(self):
        self._commandlist = {} #dict of {command_name: command}
        self._description_list = {} #dict of {command_name: description}
        self._ufc = 0 # Un-identified function counter

    def register(self, _func=None, *, command=None):
        _cmd = command
        def decorator_register(func):
            return self.register_command(func, _cmd)

        if _func is None:
            return decorator_register
        else:
            return self.register_command(_func, command=command) 

    def register_command(self, func: object, command: str=None, description: str=None):

        if not callable(func):
            raise TypeError(f"The object {repr(func)} is not a callable function!")

        #Get the name of the command if they didn't supply one
        if command == None:
            try:
                command = func.__name__ 
            except AttributeError: #This could happen if some insane person decided to register a lambda function.
                command = f"__function{self._ufc}__"
                self._ufc += 1

        #Try and get a description if they didn't supply one
        if description == None:
            description = inspect.getdoc(func)
            if description == None:
                description = "N/A"

        self._commandlist.update({command: func})
        self._description_list.update({command: description})
        return func

    def find_action(self, command: str, *a, **kw):
        c = self._commandlist.get(command, None)
        if c == None:
            return None
        if callable(c):
            return c(command, *a, **kw)
        else:
            return None

    @abstractmethod
    def broadcast_data(self, data, *a, **kw):
        """
        Broadcasts data to all connected clients.
        """
        raise NotImplementedError(str(type(self)) + ": This method should be overridden!")

    @abstractmethod
    def start(self, *a, **k):
        """
        Starts the server
        """
        raise NotImplementedError(str(type(self)) + ": This method should be overridden!")

    @abstractmethod
    def stop(self, *a, **k):
        """
        Stops the server
        """
        raise NotImplementedError(str(type(self)) + ": This method should be overridden!")