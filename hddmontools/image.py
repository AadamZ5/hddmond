import os

class Partition:
    def __init__(self, index, startSector, endSector, filesystem, type_, flags = []):
        self.index = index
        self.startSector = startSector
        self.endSector = endSector
        self.filesystem = filesystem
        self.parttype = type_
        self.flags = flags

class DiskImage:

    def __init__(self, name, path):
        self.name = name
        if(os.path.exists(path)):
            self.path = path
        else:
            raise Exception("Invalid path " + str(path))
        self._diskName = None
        self._sectorSizeLogical = None
        self._sectorSizePhysical = None
        self.partitions = []
        self._searchForPartitions()

    def _searchForPartitions(self):
        if not os.path.exists(os.path.join(self.path, 'disk')):
            raise Exception("Can't find image diskname")
        dn = ''

        with open(os.path.join(self.path, 'disk'), 'r') as fd:
            dn = fd.read()
            dn = dn.strip()

        if dn == '':
            raise Exception("Couldn't find diskname in " + str(os.path.join(self.path, 'disk')))

        self._diskName = dn
        
        partsFile = ''
        with open(os.path.join(self.path, self._diskName + '-pt.parted'), 'r') as fd:
            partsFile = fd.read()
            partsFile = partsFile.strip()

        lines = partsFile.splitlines()
        pStartIndex = 0
        pEndIndex = len(lines) #Partition definitions go to the end of the file, from wherever they start
        for i in range(len(lines)):
            if 'Sector size' in lines[i]:
                s = lines[i].split(':')[1].strip().split('/')
                self._sectorSizeLogical = int(s[0].lower().replace('b', ''))
                self._sectorSizePhysical = int(s[1].lower().replace('b', ''))

            if 'Number' in lines[i]: #Find where the partition definitions start
                pStartIndex = i + 1
                break
        
        # EX:
        # Number  Start       End         Size       Type     File system  Flags
        # 1      2048s       70311935s   70309888s  primary  ntfs         boot
        # 2      421971968s  424022015s  2050048s   primary  ntfs

        for line in lines[pStartIndex:pEndIndex]:
            vals = line.split()
            index = int(vals[0])
            startSector = int(vals[1].replace('s', ''))
            endSector = int(vals[2].replace('s', ''))
            type_ = vals[4]
            filesys = vals[5]
            flags = []
            if(len(vals) > 6):
                flags = vals[6].split()
            p = Partition(index, startSector, endSector, filesys, type_, flags)
            self.partitions.append(p)

        

            

        
