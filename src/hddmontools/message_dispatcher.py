
import random
import string
import datetime
import time
import socket
import json
import jsonpickle
import threading
class MessageDispatcher:
    def __init__(self, socket: socket.socket, incoming_msg_callback=None, event_callback=None, polling_interval_seconds=5):
        """
        incoming_msg_callback should be supplied expecting kwargs `data`, and should return a response.
        The returned value is what will be sent back as a response.

        event_callback is for when data that doesn't need a response is sent (such as updates)
        It is called with kwargs `event` and `data`
        """
        self.pending_messages = {} #Dict of {message_key: callback}
        self.recieved_waiting = {} #Dict of {message_key: data_string}
        self._event_callback = event_callback
        self._incoming_msg_callback  = incoming_msg_callback
        self._socket = socket
        self._socket.settimeout(100)
        self._poll_interval = datetime.timedelta(seconds=polling_interval_seconds)
        self._last_msg_recieved_at = datetime.datetime.now()
        self._ping_counter = 0
        self._loop_go = True
        self._server_loop_thread = threading.Thread(name="MessageDispatcher_" + str(self._socket), target=self._server_loop)

    def start(self):
        self._server_loop_thread.start()

    def stop(self):
        self._loop_go = False
        if(threading.current_thread().name != self._server_loop_thread.name):
            self._server_loop_thread.join()

    def _send_ping(self):
        send = jsonpickle.dumps({"ping": "ping", "datetime": datetime.datetime.now()}) #They really only watch for `ping`
        try:
            self._socket.send(bytes(send, 'utf-8'))
        except socket.error:
            self._loop_go = False
            self._event_callback(event='lost_connection', data='The connection has been dropped')


    def _send_pong(self):
        send = jsonpickle.dumps({"pong": "pong", "datetime": datetime.datetime.now()}) #They really only watch for `pong`
        try:
            self._socket.send(bytes(send, 'utf-8'))
        except socket.error:
            self._loop_go = False
            self._event_callback(event='lost_connection', data='The connection has been dropped')

    def _server_loop(self):
        while self._loop_go:
            if self._ping_counter > 5:
                #Sir, we have a problem.
                self._loop_go = False
                self._event_callback(event='lost_connection', data='The connection has been dropped')
                break

            if (datetime.datetime.now() - self._last_msg_recieved_at) >= self._poll_interval:
                self._send_ping()
                self._ping_counter += 1
            try:
                m_bytes = self._socket.recv(1024) 
            except socket.timeout:
                pass
            else:
                try:
                    m = jsonpickle.loads(str(m_bytes, 'utf-8'))
                except json.decoder.JSONDecodeError:
                    #Uh oh!
                    pass
                else:
                    self._last_msg_recieved_at = datetime.datetime.now()
                    data = m.get('data', None)#Data is user specified data, not our special attribute metadata
                    if "message_key" in m: #Should be a {'message_key': m_key, 'data': some_data}
                        #Determine if this is a returning message, or a new one.
                        key = m["message_key"]
                        if (key in self.pending_messages):
                            if(callable(self.pending_messages[key])):
                                self.pending_messages[key](data=data)
                            else:
                                self.recieved_waiting[key] = data
                                del self.pending_messages[key]
                        else:
                            ret_data = self._process_msg(key=key, data=data)
                            ret_data_pickle = jsonpickle.dumps(ret_data)
                            try:
                                self._socket.send(bytes(ret_data_pickle, 'utf-8'))
                            except socket.error:
                                self._loop_go = False
                                self._event_callback(event='lost_connection', data='The connection has been dropped')
                    elif "event" in m: #Events do not need responded to
                        if(callable(self._event_callback)):
                            self._event_callback(data=data)
                    elif "pong" in m:
                        self._ping_counter = 0
                        self._last_msg_recieved_at = datetime.datetime.now()
                    elif "ping" in m:
                        self._last_msg_recieved_at = datetime.datetime.now()
                        self._send_pong()
        print("A messenger exited.")


    def _process_msg(self, key, data):
        if(callable(self._incoming_msg_callback)):
            ret_data = self._incoming_msg_callback(data=data)
        else:
            ret_data = None

        return {"message_key": key, "data": ret_data}

    def send(self, message, callback=None):
        """
        Sends a message, and then returns a message key.
        If callback is not supplied, the message will be stored until recieve is called to obtain it.
        callback will be called with kwarg `data` assigned to the returned data.

        If you supply a callback, you should not worry about saving the returned key.
        The opposite is true if you do not supply a callback.
        """
        m_key = ''.join(random.choices(string.ascii_letters + string.digits, k=5))
        while (m_key in self.pending_messages) or (m_key in self.recieved_waiting): #Make sure we don't generate a key we already have, a rare chance. 
            m_key = ''.join(random.choices(string.ascii_letters + string.digits, k=5))
        
        self.pending_messages[m_key] = callback

        send = jsonpickle.dumps({"message_key": m_key, "data": message})
        try:
            self._socket.send(bytes(send, 'utf-8'))
        except socket.error:
            self._loop_go = False
            self._event_callback(event='lost_connection', data='The connection has been dropped')
            return None
        else:
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
        timeout = datetime.timedelta(milliseconds=timeout_ms)
        key = self.send(message)
        time_start = datetime.datetime.now()
        while True:
            data = self.recv(key)
            if data != None:
                return data
            else:
                if timeout_ms != None:
                    if (datetime.datetime.now() - time_start) > timeout:
                        return None
                time.sleep(0.001)

    def send_event(self, message):
        """
        Sends a rhetorical message, one that need not a response. 
        """
        send = jsonpickle.dumps({"event": 'event', "data": message})
        try:
            self._socket.send(bytes(send, 'utf-8'))
        except socket.error:
            self._loop_go = False
            self._event_callback(event='lost_connection', data='The connection has been dropped')
            return None