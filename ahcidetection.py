import subprocess
from pciaddress import PciAddress

class AhciDevice():
    def __init__(self):
        self.PciAddress = None

        dmesg = subprocess.run(['dmesg'], stdout=subprocess.PIPE, stderr=subprocess.PIPE, universal_newlines=True)
        if dmesg.returncode == 0:
            output = str(dmesg.stdout)
            lines = output.splitlines()

            ahciAddress = ""

            for line in lines:
                if "ahci" in line and "port" in line and "slots" in line:
                    ahciAddress = line
                    break
            
            if ahciAddress.strip() != "":
                #ex
                #  0        1       2       3          4      5      6   7   8   9  10  11   12   13   14   15
                #  [    1.244882] ahci 0000:00:1f.2: AHCI 0001.0300 32 slots 4 ports 6 Gbps 0x33 impl SATA mode

                cols = ahciAddress.strip().split()
                #print(cols)
                pcistring = cols[3]
                pci_seg_bus_devfun = pcistring.split(':')
#               ['0000', '00', '1f.2', '']          <----------<|
                #print(pci_seg_bus_devfun)
                seg = str(pci_seg_bus_devfun[0])          #     |
                bus = str(pci_seg_bus_devfun[1])          #     ^
                devfun = pci_seg_bus_devfun[2].split('.') #The device and function numbers are split by a '.' instead of a ':'....
                dev = str(devfun[0])
                fun = str(devfun[1])

                self.PciAddress = PciAddress(seg,bus,dev,fun)


class AhciDetective():
    def __init__(self):
        self.AhciDevice = AhciDevice()

    def GetPortFromSysPath(self, syspath):

#     0    1     2        3           4        5     6        7          8      9   10
#EX1:   '/sys/devices/pci0000:00/0000:00:1f.2/ata2/host2/target2:0:0/2:0:0:0/block/sdb        <== For a drive on the internal SATA controller!

#     0    1     2        3           4             5        6       7          8             9         10      11   12
#EX2:   '/sys/devices/pci0000:00/0000:00:01.0/0000:01:00.0/host0/port-0:3/end_device-0:3/target0:0:3/0:0:3:0/block/sdc'   <== For a drive on the LSI SAS controller!

        cols = syspath.split('/')
        #print(cols[5])
        if "ata" in cols[5]:
            #print("Found drive on internal SATA bus")
            return cols[5]
        else:
            return None

    def Update(self):
        pass



