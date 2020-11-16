from socket import socket

class SteadySocket:
    def __init__(self, socket: socket, buffer_size=1024, timeout_ms=5000):
        self._socket = socket
        self.buff_size = buffer_size
        self.timeout = timeout_ms
        self._outgoing_queue = []
        self._incoming_queue = []
    
    def _init_protocol(self):
        self._socket.send(bytes([0x5]))
        pass

    def _recv_protocol(self):
        
        pass

    def start(self):
        pass
