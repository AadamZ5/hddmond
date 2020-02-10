class WebsocketServer:
    def __init__(self):
        self.websocket = websockets.serve(self.ws_serve, "localhost", 4000)

        pass

    def _pickle(self, obj):
        pass

    def ws_serve(self, websocket, path, *args, **kwargs):
        print("Websocket connection " + str(websocket))
        websocket.send("Hello world!")