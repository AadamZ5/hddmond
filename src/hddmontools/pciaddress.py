import logging

logger = logging.getLogger(__name__)

class PciAddress():
    def __init__(self, segment, bus, device, function):
        self.segment = str(segment)[0:4]
        self.bus = str(bus)[0:2]
        self.device = str(device)[0:2]
        self.function = str(function)[0:2]

    def __eq__(self, other):
        if other == None:
            return False

        if (self.segment == other.segment) and (self.bus == other.bus) and (self.device == other.device) and (self.function == other.function):
            return True
        else:
            return False

    @property
    def Address(self):
        return self.segment + ":" + self.bus + ":" + self.device + "." + self.function

    def __str__(self):
        return "[" + self.segment + ":" + self.bus + ":" + self.device + "." + self.function + "]"

    @staticmethod
    def ParseAddr(addr: str):
        logger.debug(f"Trying to parse PCI address {addr}...")
        p = None
        
        addr = str(addr).strip()
        addr.replace('[', '').replace(']', '')
        pci_seg_bus_devfun = addr.split(':')

        if(len(pci_seg_bus_devfun) >= 3):
            try:
                #ex          ['0000', '00', '01.0', ?, ?, ?... ]
                seg = str(pci_seg_bus_devfun[0])
                bus = str(pci_seg_bus_devfun[1])
                devfun = pci_seg_bus_devfun[2].split('.') #The device and function numbers are split by a '.' instead of a ':'....
                dev = str(devfun[0])
                fun = str(devfun[1])
                p = PciAddress(seg, bus, dev, fun)
                logger.debug(f"Parsed address as {p}")
            except IndexError as e:
                logger.error(f"Couldn't parse address {addr} into a PCI address.")
                return None

        elif(len(pci_seg_bus_devfun) == 2):
            try:
                #ex          [00', '01.0']   
                seg = "0000"  #assume segment to be 0   
                bus = str(pci_seg_bus_devfun[0])          
                devfun = pci_seg_bus_devfun[1].split('.') #The device and function numbers are split by a '.' instead of a ':'....
                dev = str(devfun[0])
                fun = str(devfun[1])
                p = PciAddress(seg, bus, dev, fun)
                logger.debug(f"Parsed address as {p}")
            except IndexError as e:
                logger.error(f"Couldn't parse address {addr} into a PCI address.")
                return None
        else:
            logger.error(f"Couldn't parse address {addr} into a PCI address.")
            return None
        
        return p