'''
This file stores the code for processing commands and connections from 
'''

import threading
import multiprocessing.connection as ipc
from socket import timeout
from .genericserver import GenericServer

class MultiprocSock(GenericServer):
    def __init__(self):
        self._loopgo = True
        self.serverAddress = ('localhost', 63962)
        self.server = None
        self.serverThread = None
        self.clientlist = []

        super(MultiprocSock, self).__init__()

    def serverLoop(self, *args, **kwargs):
        print("Server running")
        while self._loopgo:
            try:
                client = self.server.accept()
            except timeout as e:
                #print("Listen wait timeout: " + str(e))
                client = None
            except Exception as e:
                print("An exception occurred while listening for clients: " + str(e))
                client = None

            if client != None:
                clientAddress = str(self.server.last_accepted)
                print("Connection from" + clientAddress)
                #should recieve a tuple with the following:
                #(command, data)
                #ie:
                #('erase', [Serial1, Serial2, Serial3])
                newClientThread = threading.Thread(target=self.client_loop, kwargs={'client': client}, name='mps_client')
                self.clientlist.append((client, clientAddress, newClientThread))
                newClientThread.start()

        print("Server loop stopped")

    def client_loop(self, client=None):
        print("Split client into seperate thread")
        futuremsg = None
        while ('client' in locals()) and self._loopgo:
            if(futuremsg):
                msg = futuremsg
                futuremsg = None
            else:
                try:
                    msg = client.recv()#blocking call
                except EOFError as e:
                    print("Pipe unexpectedly closed:\n" + str(e))
                    msg = None
                    del client
                    break
                
            #The message type is a tuple of (command, data)
            if(type(msg) == tuple):
                command = ''
                readCmd = True
                try:
                    command = msg[0]
                    data = msg[1]
                except Exception as e:
                    print("Error while retrieving data from tuple in client message.\n" + str(e))
                    readCmd = False
                
                if readCmd:
                    r = self.find_action(command, **data)
                    if r != None:
                        client.send(('success', r))
                    else:
                        client.send(('error', 'Unknown command'))
            else:
                pass #Message wasn't a tuple
        print("Client connection ended")

    def broadcast_data(self, data, *args, **kwargs):
        pass

    def start(self):
        self._loopgo = True
        self.server = ipc.Listener(address=self.serverAddress, authkey=b'H4789HJF394615R3DFESZFEZCDLPOQ')
        self.server._listener._socket.settimeout(3.0)
        self.serverThread = threading.Thread(target=self.serverLoop, name='mps_loop')
        self.serverThread.start()

    def stop(self):
        for c in self.clientlist:
            client = c[0]
            addr = c[1]
            thread = c[2]
            thread.join()
