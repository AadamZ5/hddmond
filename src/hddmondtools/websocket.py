import asyncio
from asyncio import AbstractEventLoop
import threading
import websockets
from .genericserver import GenericServer
import jsonpickle


class ClientDataMulticaster: #This is used to keep track of all clients connected, to allow multicasting. 
    def __init__(self):
        self._client_data = {} #{client: data[]}

    def register(self, address):
        #print("Registering websocket at " + str(address) + " to broadcast list")
        self._client_data.update({address: []})
        return self._client_data[address]

    def broadcast(self, data):
        for k in self._client_data.keys():
            self._client_data[k].append(data)

    def unregister(self, address):
        #print("Unregistering websocket at " + str(address) + " from broadcast list")
        try:
            del self._client_data[address]
        except KeyError:
            print("Error: Tried to delete a websocket that was never registered!")
            pass


class WebsocketServer(GenericServer):
    def __init__(self):
        self.loop = asyncio.get_event_loop()

        # self.ssl_context = ssl._create_unverified_context(ssl.PROTOCOL_TLS_SERVER)
        # self.localhost_pem = pathlib.Path(__file__).with_name("localhost.pem")
        # self.ssl_context.load_cert_chain(self.localhost_pem)

        self.loopthread = None
        self.ws = None

        self.clientlist = {} #{address: websocket, ...}
        self.clientdata_multicast = ClientDataMulticaster()
        

        super(WebsocketServer, self).__init__()

    async def register(self, websocket):
        self.clientlist.update({websocket.remote_address: websocket})

    async def unregister(self, websocket_addr):
        del self.clientlist[websocket_addr]
        self.clientdata_multicast.unregister(websocket_addr)

    async def consumer_handler(self, ws, path, *args, **kwargs):
        await self.register(ws)
        async for message in ws:
            m = {}
            try:
                m = jsonpickle.loads(message)
            except Exception:
                print("Error decoding message from " + str(ws.remote_address) + ". Message: " + str(message))
                send = jsonpickle.dumps({"error": "Couldn't parse JSON data!"}, unpicklable=False, make_refs=False)
                await ws.send(send)
            
            if(m != None):
                command = m.get('command', None)
                data = m.get('data', dict())

                if command != None:
                    r = self.find_action(str(command), **data) #The main application will register functions to various commands. See if we can find one registered for the command sent.
                    r_json = jsonpickle.dumps(r, unpicklable=False, make_refs=False) #Note, if no function is found, we will just JSON pickle `None` which will just send a `null` back to the client.
                    await ws.send(r_json) 
                else:
                    send = jsonpickle.dumps({"error": "No command to process!"}, unpicklable=False, make_refs=False)
                    await ws.send(send)

            else:
                send = jsonpickle.dumps({"error": "No data to parse!"}, unpicklable=False, make_refs=False)
                await ws.send(send)

        await self.unregister(ws.remote_address)
        
    async def producer_handler(self, ws, path, *args, **kw):
        data_list = self.clientdata_multicast.register(ws.remote_address)
        while True:
            if(len(data_list) <= 0):
                await asyncio.sleep(0.5)
            else:
                await ws.send(data_list.pop(0))

    async def handler(self, ws, path, *args, **kw):
        c_task = asyncio.ensure_future(self.consumer_handler(ws, path, *args, **kw))
        p_task = asyncio.ensure_future(self.producer_handler(ws, path, *args, **kw))
        done, pending = await asyncio.wait([c_task, p_task,], return_when=asyncio.FIRST_COMPLETED)
        for task in pending: #This executes when the async call above finishes.
            task.cancel() #Cancel any remaining task. 

    def _make_server(self, loop: AbstractEventLoop):
        asyncio.set_event_loop(loop)
        self.ws = loop.run_until_complete(websockets.serve(self.handler, "0.0.0.0", 8765))
        loop.run_forever()

    def broadcast_data(self, data, *a, **kw):
        data_s = jsonpickle.dumps(data, unpicklable=False, make_refs=False)
        self.clientdata_multicast.broadcast(data_s)

    def start(self):
        self.loopthread = threading.Thread(target=self._make_server, name='websocket_loop', args=(self.loop,))
        self.loopthread.start()

    def stop(self):
        self.ws.close()
        self.loop.call_soon_threadsafe(self.loop.stop) #https://stackoverflow.com/questions/46093238/python-asyncio-event-loop-does-not-seem-to-stop-when-stop-method-is-called?answertab=votes#tab-top
        self.loopthread.join()