
from hddmontools.hdd_interface import HddInterface
from hddmontools.hdd import Hdd

class HddRemoteHost: #This doesnt inherit from HddInterface, because the HddRemoteReciever class already does that. This class will not be seen by Hddmon.
    """
    HddRemoteHost serves as a wrapper for a native HDD object on a client's end. The HddRemoteHost will host a connection to an HDD, which a reciever server
    will dispatch commands and data to and from. This will allow remote computers to host devices on one server.
    """
    def __init__(self, hdd:Hdd, address):
        self.hdd = hdd
        pass


class HddRemoteReciever(HddInterface):
    """
    HddRemoteReciever is used on the server side after an incoming connection is established with a client. The client will host a connection
    to their HDD using HddRemoteHost which serves as a translater or proxy for commands and data. 
    """
    def __init__(self):
        pass