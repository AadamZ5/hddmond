
class PciAddress():
    def __init__(self, segment, bus, device, function):
        self.segment = str(segment)[0:4]
        self.bus = str(bus)[0:2]
        self.device = str(device)[0:2]
        self.function = str(function)[0:2]

    def __eq__(self, other):
        if (self.segment == other.segment) and (self.bus == other.bus) and (self.device == other.device) and (self.function == other.function):
            return True
        else:
            return False

    @property
    def Address(self):
        return self.segment + ":" + self.bus + ":" + self.device + "." + self.function

    def __str__(self):
        return "[" + self.segment + ":" + self.bus + ":" + self.device + "." + self.function + "]"