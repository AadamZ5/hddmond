import ahcidetection
import sasdetection
import subprocess
from pciaddress import PciAddress

class PortDetection():
    def __init__(self):
        self.ahcidet = ahcidetection.AhciDetective()
        self.sasdet = sasdetection.SasDetective()

        lspci = subprocess.run(['lspci'], stdout=subprocess.PIPE, stderr=subprocess.PIPE, universal_newlines=True)
        lines = str(lspci.stdout).splitlines()

        pcisToParse = []

        for line in lines:
            if "PCI bridge" in line:
                pcisToParse.append(line.split()[0])
        
        self.blacklistPcis = []
        for p in pcisToParse:
            self.blacklistPcis.append(PciAddress.ParseAddr(p))

    def Update(self):
        self.ahcidet.Update()
        self.sasdet.Update()
        
    def GetPci(self, syspath):
        cols = syspath.split('/')
        check = cols[4]
        #print(check)
        pci = PciAddress.ParseAddr(check)
        if(pci in self.blacklistPcis):
            pci = PciAddress.ParseAddr(cols[5])
        return pci

    def GetPort(self, syspath, pci, serial):
        p = self.ahcidet.GetPortFromSysPath(syspath)
        if p != None:
            #print("Setting port to " + str(p))
            return p
        
        p = self.sasdet.GetDevicePort(pci, serial)
        if p != None:
            #print("Setting port to sas" + str(p))
            return "sas" + str(p)

        return None