
import random
import string
import datetime
import time
import socket
import json
import jsonpickle
import pickle
import threading
class MessageDispatcher:
    #TODO: Implement chunck sizing and resending upon error!
    @property
    def running(self):
        return self._loop_go

    def __init__(self, socket: socket.socket, incoming_msg_callback=None, event_callback=None, polling_interval_seconds=5):
        """
        incoming_msg_callback should be supplied expecting kwargs `data`, and should return a response.
        The returned value is what will be sent back as a response.

        event_callback is for when data that doesn't need a response is sent (such as updates)
        It is called with kwargs `event` and `data`
        """
        self.pending_messages = {} #Dict of {message_key: (sent_data, callback)}
        self.recieved_waiting = {} #Dict of {message_key: data_string}
        self._event_callback = event_callback
        self._incoming_msg_callback  = incoming_msg_callback
        self._socket = socket
        self._socket.settimeout(1000)
        self._socket.setblocking(False)
        self._poll_interval = datetime.timedelta(seconds=polling_interval_seconds)
        self._last_msg_recieved_at = datetime.datetime.now()
        self._last_ping = datetime.datetime.now()
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
        send = pickle.dumps({"ping": "ping", "datetime": datetime.datetime.now()}) #They really only watch for `ping`
        
        if self._send_all_bytes(send):
            return None
        else:
            return None


    def _send_pong(self):
        send = pickle.dumps({"pong": "pong", "datetime": datetime.datetime.now()}) #They really only watch for `pong`
        
        if self._send_all_bytes(send):
            return None
        else:
            return None

    def _server_loop(self):
        while self._loop_go:

            #Check if we've been pinging
            if self._ping_counter > 5:
                #Sir, we have a problem.
                print("Ping counter over 5")
                self._loop_go = False
                self._event_callback(event='lost_connection', data='The connection has been dropped')
                return

            #Check if we should be concerned about last message time
            if ((datetime.datetime.now() - self._last_msg_recieved_at) >= self._poll_interval) and ((datetime.datetime.now() - self._last_ping) >= self._poll_interval):
                self._send_ping()
                self._ping_counter += 1
                self._last_ping = datetime.datetime.now()
                print(f"{self._ping_counter} Sent ping...")

            #Try and get a message
            in_bytes = bytearray()
            try:
                m_bytes = self._socket.recv(512) 
                
                if len(m_bytes) > 0:
                    print(f"First data in! Bytes_len: {len(m_bytes)}")
                    #We got some data. Prepare to recieve more.
                    self._last_msg_recieved_at = datetime.datetime.now()

                    in_bytes.extend(m_bytes)
                    while len(m_bytes) > 0:
                        #self._socket.setblocking()
                        try:
                            m_bytes = self._socket.recv(512) 
                        except socket.error:
                            m_bytes = bytes([])

                        if(len(m_bytes) > 0):
                            print(f"More data! Bytes_len: {len(m_bytes)}")
                            in_bytes.extend(m_bytes)
                        else:
                            print("No new bytes in")
                    print(f"Done recieving. Got {len(in_bytes)} bytes.")
                else:
                    time.sleep(0.001)#Is this efficient?
            except socket.timeout:
                print("Socket timeout")
                pass
            except socket.error:
                #print("Socket error")
                pass
            else:
                if len(in_bytes) <= 0:
                    continue

                try:
                    m = pickle.loads(in_bytes)
                except json.decoder.JSONDecodeError as e:
                    print(f"Had an error while decoding JSON from socket in messenger.\n\t{str(e)}")
                    print(str(m_bytes))
                    
                    pass
                except EOFError:
                    print("Ran out of input while trying to decode data.")
                except pickle.UnpicklingError:
                    print("Couldn't unpickle truncated data")
                else:
                    self._last_msg_recieved_at = datetime.datetime.now()
                    data = m.get('data', None)#Data is user specified data, not our special attribute metadata
                    if "message_key" in m: #Should be a {'message_key': m_key, 'data': some_data}
                        #Determine if this is a returning message, or a new one.
                        key = m["message_key"]
                        if (key in self.pending_messages):
                            if(callable(self.pending_messages[key][1])):
                                self.pending_messages[key][1](data=data)
                            else:
                                self.recieved_waiting[key] = data
                                del self.pending_messages[key]
                        else:
                            print(f"Got a new message with key {key}.")
                            ret_data = self._process_msg(key=key, data=data)
                            print(f"Returning data {str(ret_data)}")
                            ret_data_pickle = pickle.dumps(ret_data)
                            self._send_all_bytes(ret_data_pickle)
                    elif "event" in m: #Events do not need responded to
                        if(callable(self._event_callback)):
                            self._event_callback(**data)
                    elif "pong" in m:
                        self._ping_counter = 0
                        self._last_msg_recieved_at = datetime.datetime.now()
                    elif "ping" in m:
                        self._last_msg_recieved_at = datetime.datetime.now()
                        self._send_pong()
            finally:
                self._socket.setblocking(False)
        print("Messenger {0} exited.".format(str(self._socket)))


    def _process_msg(self, key, data):
        if(callable(self._incoming_msg_callback)):
            ret_data = self._incoming_msg_callback(data=data)
        else:
            ret_data = None

        return {"message_key": key, "data": ret_data}

    def _send_all_bytes(self, data: bytes):
        #print(f"Sending data: {str(data)}")
        length = len(data)
        sent = 0
        #print(f"Sent {sent}/{length}")
        try:
            while sent < length:
                sent += self._socket.send(data[sent:])
                #print(f"Sent {sent}/{length}")
            #print("Done")
            return True
        except socket.error:
            self._loop_go = False
            self._event_callback(event='lost_connection', data='The connection has been dropped')
            return False

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
        
        self.pending_messages[m_key] = (message, callback)

        send = pickle.dumps({"message_key": m_key, "data": message})
 
        if self._send_all_bytes(send):
            return m_key
        else:
            return None

    def retry_send(self, used_key):
        if not used_key in self.pending_messages:
            return None

        m_key = used_key
        message = self.pending_messages[m_key][0]

        send = pickle.dumps({"message_key": m_key, "data": message})
        
        if self._send_all_bytes(send):
            return m_key
        else:
            return None

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

    def send_and_recv(self, message, timeout_ms=None, retry_delay=1000):
        """
        Sends a message and blocks until a response, or an optional timeout.
        """
        timeout = datetime.timedelta(milliseconds=timeout_ms)
        retry_interval = datetime.timedelta(milliseconds=retry_delay)
        
        key = self.send(message)
        time_start = datetime.datetime.now()
        last_retry = datetime.datetime.now()
        while True:
            data = self.recv(key)
            if data != None:
                return data
            else:
                if timeout_ms != None:
                    if (datetime.datetime.now() - time_start) > timeout:
                        print("Timeout while waiting for message {0} ({1})".format(key, message))
                        return None
                if (datetime.datetime.now() - last_retry) > retry_interval:
                    self.retry_send(key)
                    last_retry = datetime.datetime.now()
                time.sleep(0.001)

    def send_event(self, message):
        """
        Sends a rhetorical message, one that need not a response. 
        """
        send = pickle.dumps({"event": 'event', "data": message})
        
        if self._send_all_bytes(send):
            return None
        else:
            return False