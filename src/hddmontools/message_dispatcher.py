
import random
import string
import datetime
import time
import socket

class MessageDispatcher:
    def __init__(self, socket: socket.socket, incoming_msg_callback=None, event_callback=None):
        self.pending_messages = {} #Dict of {message_key: callback}
        self.recieved_waiting = {} #Dict of {message_key: data_string}
        self._event_callback = event_callback
        self._incoming_msg_callback  = incoming_msg_callback
        self._socket = socket
        #self._server_loop() #TODO Needs to be in a thread unfortunately

    def _server_loop(self):
        while True:
            self._socket.recv(1024) #Should be a {'message_key': m_key, 'data': some_data}
            #TODO parse the data somehow!

    def _process_msg(self, whole_message):
        pass

    def send(self, message, callback=None):
        """
        Sends a message, and then returns a message key.
        If callback is not supplied, the message will be stored until recieve is called to obtain it.
        """
        m_key = ''.join(random.choices(string.ascii_letters + string.digits, k=5))
        self.pending_messages[m_key] = callback
        #TODO: Socket send {"message_key": m_key, "data": some_data}
        #TODO: Encode the data somehow! use JSONPickle?
        self._socket.send(message)
        return m_key

    def recv(self, key: str):
        """
        Checks to see if a message has returned.
        Returns `None` if no message is ready, and will Except if no message by that key is pending.
        """
        if key in self.pending_messages:
            return None
        elif key in self.recieved_waiting:
            data = self.recieved_waiting[key]
            del self.recieved_waiting[key]
            return data
        else:
            raise Exception("No message found")

    def send_and_recv(self, message, timeout_ms=None):
        """
        Sends a message and blocks until a response, or an optional timeout.
        """
        key = self.send(message)
        time_start = datetime.datetime.now()
        while True:
            data = self.recv(key)
            if data != None:
                return data
            else:
                if timeout_ms != None:
                    if datetime.datetime.now() - time_start > timeout_ms:
                        return None
                time.sleep(0.001)

    def send_event(self, message):
        """
        Sends a rhetorical message, one that need not a response. 
        """
        #TODO: Socket send!