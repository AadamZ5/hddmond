class GenericServer:
    def __init__(self):
        self._commandlist = {} #dict of {key: command}
    
    def register_command(self, command: str, action: object):
        self._commandlist.update({command: action})

    def find_action(self, command: str, *a, **kw):
        c = self._commandlist.get(command, None)
        if c == None:
            return None
        if callable(c):
            return c(command, *a, **kw)
        else:
            return None

    def broadcast_data(self, data, *a, **kw):
        raise NotImplementedError(str(type(self)) + ": This method should be overridden!")

    def start(self, *a, **k):
        pass

    def stop(self, *a, **k):
        pass