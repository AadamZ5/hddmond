import subprocess
import logging

from injectable import injectable
from pathlib import Path

from lib.oslib.pciaddress import PciAddress

class SasDevice:
    def __init__(self, index=None):
        self.logger = logging.getLogger(__name__ + "." + self.__class__.__qualname__ + f'[{index}]')
        self.logger.setLevel(logging.DEBUG)
        self.logger.info(f"Registering SAS device with index {index}...")
        self.Index = int(index)
        self.PciAddress = None
        self.Devices = {} #{Serial *str: slot *int}

        displayInfo = subprocess.run([SasDetective.sas2ircu, str(self.Index), 'DISPLAY'], stdout=subprocess.PIPE, stderr=subprocess.PIPE, universal_newlines=True)
        if (displayInfo.returncode == 0):

            startIndex = 0
            endIndex = 0

            lines = str(displayInfo.stdout).splitlines()
            for i in range(len(lines)):
                if("Controller information" in str(lines[i]).strip()):
                    startIndex = i
                    break
            
            for i in range(startIndex + 2, len(lines)):
                if(lines[i].startswith("--------")):
                    endIndex = i
                    break

            #Should end up with this
            # Controller information                                                    | i = 0
            # ------------------------------------------------------------------------  | i = 1
            #   Controller type                         : SAS2008                       | i = 2
            #   BIOS version                            : 7.39.02.00                    | i = 3
            #   Firmware version                        : 20.00.06.00                   | i = 4
            #   Channel description                     : 1 Serial Attached SCSI        | i = 5
            #   Initiator ID                            : 0                             | i = 6
            #   Maximum physical devices                : 255                           | i = 7
            #   Concurrent commands supported           : 3432                          | i = 8
            #   Slot                                    : 16                            | i = 9
            #   Segment                                 : 0                             | i = 10
            #   Bus                                     : 1                             | i = 11
            #   Device                                  : 0                             | i = 12
            #   Function                                : 0                             | i = 13
            #   RAID Support                            : No                            | i = 14
            # ------------------------------------------------------------------------  | i = 15

            data = lines[startIndex:endIndex]

            segment = data[10].split(':')[1].strip().zfill(4)
            bus =  data[11].split(':')[1].strip().zfill(2)
            device = data[12].split(':')[1].strip().zfill(2)
            function = data[13].split(':')[1].strip().zfill(1)

            self.PciAddress = PciAddress(segment, bus, device, function)
            self.logger.debug(f"Registered with PCI address {self.PciAddress}.")
            #print(self.PciAddress)
        else:
            self.logger.error(f"Got non-zero exit code {displayInfo.returncode} from sas2ircu!")
        self.GetDevices()
        self.logger.debug(f"Found {len(self.Devices)} devices attached to this device.")
    
    def GetPortFromSerial(self, serial:str):
        return self.Devices.get(serial, None)

    def GetDevices(self):
        self.logger.debug("Looking for attached devices...")
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
            for i in range((startIndex + 2), len(lines)): #The reason we start at 'startIndex + 2' is so we skip the line directly after the header, which does contain '--------' itself.
                if lines[i].startswith("--------"):
                    endIndex = i
                    break  
            
            data = lines[startIndex:endIndex]   #If startIndex and endIndex are never set for some reason, our data will consist of lines[0:0]
            for i in range(len(data)):
                if(data[i].strip().startswith("Device is a Hard disk")):
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
                    serial = str(data[i+8].split(':')[1].strip())
                    slot = int(str(data[i+2].split(':')[1].strip()))
                    self.Devices.update({serial: slot})
                    self.logger.debug(f"Found device {serial} on slot {slot}")
                    i += 10 #advance to the next block of data
        else:
            pass #Do something else?

@injectable(singleton=True)
class SasDetective:
    sas2ircu = str((Path(__file__).parent / '..' / '..' / 'sas2ircu' / 'sas2ircu_linux_x86_rel' / 'sas2ircu').resolve())

    def __init__(self):
        self.logger = logging.getLogger(__name__ + "." + self.__class__.__qualname__)
        self.logger.setLevel(logging.DEBUG)
        self.logger.info("Initializing SasDetective...")
        listSas = subprocess.run([SasDetective.sas2ircu, 'LIST'], stdout=subprocess.PIPE, stderr=subprocess.PIPE, universal_newlines=True)
        
        self.SasDevices = []
        
        if(listSas.returncode == 0):
            output = str(listSas.stdout)
            lines = output.splitlines()
            for entry in lines:
                splits = entry.split()
                if(len(splits) >= 1):
                    if(splits[0].isnumeric()):
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

                        device = SasDevice(index=int(cols[0])) #SasDevice will remove the h from the PCI address
                        self.SasDevices.append(device)
                        self.logger.debug(f"Found SAS device with index {device.Index}.")
                    else:
                        pass #The line was just informational text, not data we needed
        else:
            self.logger.error(f"Got non-zero exit code {listSas.returncode} from sas2ircu while trying to list SAS controllers!")
            pass #Incorperate error handling?

    def GetDevicePort(self, pci, serial):
        if(pci != None):
            self.logger.debug(f"Looking for port for {serial} using PCI address {pci} as a hint...")
            #print("Got PCI: " + str(pci))
            #First find the device with the same leading PCI address
            for sas in self.SasDevices:
                #print("Check " + str(pci) + " == " + str(sas.PciAddress))
                if sas.PciAddress == pci:
                    #print("Looking in SAS index " + str(sas.Index))
                    return sas.GetPortFromSerial(serial) #We found a SAS device with that PCI address. Let it try and find the device
            
            #The loop finished and we didn't find anything at that PCI address
            self.logger.debug(f"No SAS port found for {serial} on PCI address {pci}.")
            return None
        
        #If the PCI address isn't given, More resource intensive.
        elif(serial != None):
            self.logger.debug("Looking for drive " + serial + " in all SAS cards...")
            for sas in self.SasDevices:
                d = sas.GetPortFromSerial(serial)
                if(d != None):
                    return d #We found a device

            #The loop finished and we didn't find anything
            self.logger.debug(f"No SAS port found for {serial}")
            return None
        else:
            return None #What do you want us to do if you didn't give us anything?
                
    def Update(self):
        self.logger.debug("Updating all SAS device listings...")
        for sasdevice in self.SasDevices:
            sasdevice.GetDevices()