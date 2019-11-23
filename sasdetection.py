import subprocess

class SasDevice:
    def __init__(self, index=None, pciAddress=None):
        self.Index = int(index)
        self.PciAddress = []
        pci = str(pciAddress).replace('h', '')
        pcia = pci.split(':')
        for part in pcia:
            self.PciAddress.append(int(part))

        self.Devices = {} #{Serial: slot}
        self.GetDevices()
    
    def GetPortFromSerial(self, serial:str):
        return self.Devices.get(serial, None)

    def GetDevices(self):
        displayInfo = subprocess.run([SasDetective.sas2ircu, str(self.Index), 'DISPLAY'], stdout=subprocess.PIPE, stderr=subprocess.PIPE, universal_newlines=True)

        #Example output:
        # LSI Corporation SAS2 IR Configuration Utility.
        # Version 5.00.00.00 (2010.02.09) 
        # Copyright (c) 2009 LSI Corporation. All rights reserved. 

        # Read configuration has been initiated for controller 0
        # ------------------------------------------------------------------------
        # Controller information
        # ------------------------------------------------------------------------
        #   Controller type                         : SAS2008
        #   BIOS version                            : 7.39.02.00
        #   Firmware version                        : 20.00.06.00
        #   Channel description                     : 1 Serial Attached SCSI
        #   Initiator ID                            : 0
        #   Maximum physical devices                : 255
        #   Concurrent commands supported           : 3432
        #   Slot                                    : 16
        #   Segment                                 : 0
        #   Bus                                     : 1
        #   Device                                  : 0
        #   Function                                : 0
        #   RAID Support                            : No
        # ------------------------------------------------------------------------
        # IR Volume information
        # ------------------------------------------------------------------------
        # ------------------------------------------------------------------------
        # Physical device information                                                       <== We want this
        # ------------------------------------------------------------------------          |
        # Initiator at ID #0                                                                |
        #                                                                                   |
        # Device is a Hard disk                                                             |
        #   Enclosure #                             : 1                                     |
        #   Slot #                                  : 7                                     |
        #   State                                   : Ready (RDY)                           |
        #   Size (in MB)/(in sectors)               : 238475/488397167                      |
        #   Manufacturer                            : ATA                                   |
        #   Model Number                            : WDC WD2500AAJS-6                      |
        #   Firmware Revision                       : 3A02                                  |
        #   Serial No                               : WDWCAT16599125                        |
        #   Protocol                                : SATA                                  |
        #   Drive Type                              : SATA_HDD                              |
        # ------------------------------------------------------------------------          <== Stop here
        # Enclosure information
        # ------------------------------------------------------------------------
        #   Enclosure#                              : 1
        #   Logical ID                              : 500605b0:07d95e90
        #   Numslots                                : 8
        #   StartSlot                               : 0
        # ------------------------------------------------------------------------
        # SAS2IRCU: Command DISPLAY Completed Successfully.
        # SAS2IRCU: Utility Completed Successfully.



        if(displayInfo.returncode == 0):
            output = str(displayInfo.stdout)
            lines = output.splitlines()
            startIndex = 0
            endIndex = 0
            #Check to see when device list starts
            for i in range(len(lines)):
                if "Physical device information" in lines[i]:
                    startIndex = i #We found the beginning, which is the header containing "Physical device information"
                    break

            #Now find the end
            for i in range((startIndex + 2), len(lines)): #The reason we start at 'startIndex + 2' is so we skip the line directly after the header, which does
                if lines[i].startswith("--------"):      #contain '--------' itself. 
                    endIndex = i
                    break  
            
            data = lines[startIndex:endIndex]   #If startIndex and endIndex are never set for some reason, our data will consist of lines[0:0]
            for i in range(len(data)):
                if(data[i].startswith("Device is a Hard disk")):
                    #The next 10 lines are device information

                    # Device is a Hard disk                                         | i+0
                    #   Enclosure #                             : 1                 | i+1
                    #   Slot #                                  : 7                 | i+2
                    #   State                                   : Ready (RDY)       | i+3
                    #   Size (in MB)/(in sectors)               : 238475/488397167  | i+4
                    #   Manufacturer                            : ATA               | i+5
                    #   Model Number                            : WDC WD2500AAJS-6  | i+6
                    #   Firmware Revision                       : 3A02              | i+7
                    #   Serial No                               : WDWCAT16599125    | i+8
                    #   Protocol                                : SATA              | i+9
                    #   Drive Type                              : SATA_HDD          | i+10
                    serial = str(data[i+8])
                    slot = int(str(data[i+2]))
                    self.Devices.update({serial: slot})
                    i += 10 #advance to the next block of data
        else:
            pass #Do something else?

class SasDetective:
    sas2ircu = r'./sas2ircu/sas2ircu_linux_x86_rel/sas2ircu'

    def __init__(self):
        listSas = subprocess.run([SasDetective.sas2ircu, 'LIST'], stdout=subprocess.PIPE, stderr=subprocess.PIPE, universal_newlines=True)

        self.SasDevices = []

        if(listSas.returncode == 0):
            output = str(listSas.stdout)
            lines = output.splitlines()
            for entry in lines:
                if(entry.lstrip().split()[0].isnumeric()):
                    cols = entry.strip().split()

                    #Example output:
                    # LSI Corporation SAS2 IR Configuration Utility.
                    # Version 5.00.00.00 (2010.02.09) 
                    # Copyright (c) 2009 LSI Corporation. All rights reserved. 
                    #
                    #
            #   col:    0         1           2        3         4                  5      6
                    #          Adapter      Vendor  Device                       SubSys  SubSys 
                    #  Index    Type          ID      ID    Pci Address          Ven ID  Dev ID 
                    #  -----  ------------  ------  ------  -----------------    ------  ------ 
                    #    0     SAS2008     1000h    72h   00h:01h:00h:00h      1000h   3020h 
                    # SAS2IRCU: Utility Completed Successfully.

                    device = SasDevice(index=int(cols[0]), pciAddress=cols[4]) #SasDevice will remove the h from the PCI address
                    self.SasDevices.append(device)
                else:
                    pass #The line was just informational text, not data we needed
        else:
            pass #Incorperate error handling?

    def GetDevicePort(self, serial, pci=None):
        
        if(pci != None):
            pci = str(pci).replace('[', '').replace(']', '')
            pci = pci.split(':')
            pciAddress = []
            for part in pci:
                pciAddress.append(int(part))

            #First find the device with the same leading PCI address
            for sas in self.SasDevices:
                if sas.PciAddress[0] == pciAddress[0] and sas.PciAddress[1] == pciAddress[1]:
                    return sas.GetPortFromSerial(serial) #We found a SAS device with that PCI address. Let it try and find the device
            
            #The loop finished and we didn't find anything at that PCI address
            return None
        
        #If the PCI address isn't given, More resource intensive.
        else:
            for sas in self.SasDevices:
                d = sas.GetPortFromSerial(serial)
                if(d != None):
                    return d #We found a device

            #The loop finished and we didn't find anything
            return None
                
