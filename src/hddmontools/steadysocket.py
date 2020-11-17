from socket import socket
import threading

class SteadySocket:
    def __init__(self, socket: socket, buffer_size=1024, timeout_ms=5000):
        self._socket = socket
        self.buff_size = buffer_size
        self.timeout = timeout_ms
        self._outgoing_queue = []
        self._incoming_queue = []

        self._handshook = False
        self._loopgo = True

        self._socket_thread = threading.Thread(name="steady_socket", target=self._listen)
    
    def _listen(self):

        while self._loopgo and not self._handshook:
            self._recv_protocol(self._socket.recv(16))
        
        while self._loopgo and self._handshook:
            self._recv_transmission(None)


    def _init_protocol(self):
        self._socket.send(bytes([0x5])) # 0x5 = Enquiry
        in_bytes = self._socket.recv(16)
        if len(in_bytes) <= 0:
            return #No bytes recieved, we should exit.
        if in_bytes[0] != 0x6: #0x6 = Acknowledge
            return #Wrong byte back, we should exit.

        in_bytes = self._socket.recv(16) #Wait for 0x5 Enquiry back

    def _recv_protocol(self, first_message):
        if len(first_message) <= 0:
            return #No bytes recieved, we should exit.
        if first_message[0] != 0x5: #0x5 = Enquiry
            return #Wrong byte back, we should exit.
        
        self._socket.send(bytes([0x6]))
        in_bytes = self._socket.recv()
        pass

    def _recv_transmission(self, transmission):
        pass

    def start(self):
        pass
