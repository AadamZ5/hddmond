import os
import gzip
import threading
import shutil

class Partition:
    def __init__(self, index, startSector, endSector, filesystem, type_, flags=None):
        self.index = index
        self.startSector = startSector
        self.endSector = endSector
        self.filesystem = filesystem
        self.parttype = type_
        self.flags = flags if type(flags) == list else []
        self.md5sums = {}

    def dump_md5s(self):
        import json
        return json.dumps(self.md5sums, indent=4)

    @staticmethod
    def parse_parted_line(line:str):
        '''
        parses a single partition line output from parted [device]. Returns a partition, or None if creation failed.
        '''
        vals = line.split()
        try:
            index = int(vals[0])
            startSector = int(vals[1].replace('s', ''))
            endSector = int(vals[2].replace('s', ''))
            type_ = vals[4]
            filesys = vals[5]
            flags = []
            if(len(vals) > 6):
                for i in range(len(vals[6:])):
                    flags.append(vals[i+6].strip().replace(',',''))
            p = Partition(index, startSector, endSector, filesys, type_, flags)
            return p
        except IndexError:
            return None

    @staticmethod
    def parse_parted_output(partedOutput:str):
        '''
        Parses the output of parted [device] for partitions. Returns a list of partitions.
        '''
        lines = partedOutput.splitlines()
        pStartIndex = 0
        pEndIndex = len(lines) #Partition definitions go to the end of the file, from wherever they start
        for i in range(len(lines)):
            if 'Number' in lines[i]: #Find where the partition definitions start
                pStartIndex = i + 1
                break
        
        # EX:
        # Number  Start       End         Size       Type     File system  Flags
        # 1      2048s       70311935s   70309888s  primary  ntfs         boot
        # 2      421971968s  424022015s  2050048s   primary  ntfs

        parts = []
        for line in lines[pStartIndex:pEndIndex]:
            p = Partition.parse_parted_line(line)
            if p != None:
                parts.append(p)
        
        return parts

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
        self.parttable = None
        self.partitions = []
        self._searchForPartitions()
        self._get_md5sums()

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

            if 'Partition Table' in lines[i]:
                s = lines[i].split(':')[1].strip()
                self.parttable = s

        self.partitions = Partition.parse_parted_output(partsFile)

    def _get_md5sums(self):
        for p in self.partitions:

            existing_sums = str(self._diskName + str(p.index)) + ".files-md5sum-rootbased.info.gz"
            path = os.path.join(self.path, existing_sums)
            if(os.path.exists(path)): #Check for our already-parsed md5-sum file.
                with gzip.open(path) as gz: #Read the compressed md5sum file
                    import json
                    md5s = str(gz.read().decode())
                    p.md5sums = json.loads(md5s)
                continue

            f = str(self._diskName + str(p.index)) + ".files-md5sum.info.gz"
            path = os.path.join(self.path, f)
            if(os.path.exists(path)):
                lines = None
                with gzip.open(path) as gz: #Read the compressed md5sum file
                    md5s = str(gz.read().decode())
                    lines = md5s.splitlines()
                    #print(len(lines))
                
                if lines != None:
                    import re
                    for line in lines:
                        #line might look like this:     
                        #c931e513a1e7a7692468ba95b9c621fc  /tmp/chksum_tmpd.DqNOIG/Drivers/kioskreport/MasterInfo.dll

                        t = line.split()
                        dir_ = str(t[1]) #  /tmp/chksum_tmpd.DqNOIG/Drivers/kioskreport/MasterInfo.dll
                        sum_ = str(t[0]) #  c931e513a1e7a7692468ba95b9c621fc

                        rootdir = re.sub('(\/tmp\/chksum_tmpd\.\w{6})', '', dir_) #  ------------/Drivers/kioskreport/MasterInfo.dll
                        p.md5sums.update({rootdir: sum_})
                self._write_new_md5sums(p)
                continue
                
    def _write_new_md5sums(self, p:Partition):
        md5s = p.dump_md5s()
        existing_sums = str(self._diskName + str(p.index)) + ".files-md5sum-rootbased.info.gz"
        with gzip.open(os.path.join(self.path,existing_sums), 'wt') as gz:
            gz.write(md5s)

class CustomerImage(DiskImage):
    def __init__(self, name, path, customer):
        self.customer = customer
        super(CustomerImage, self).__init__(name, path)

    @staticmethod
    def FromDiskImage(image: DiskImage, customer: str):
        c = CustomerImage.__new__(CustomerImage)
        c.__dict__ = image.__dict__
        c.customer = customer
        return c
        
class CopyManager:

    @property
    def Progress(self):
        return (self.files_copied/self.files_to_copy)*100

    def __init__(self):
        self.files_to_copy: int
        self.files_copied: int = 0
        self._stop = False

    def _copy_progress(self, src, dest, symlinks: bool = True):
        if self._stop == True:
            raise InterruptedError("Copy canceled")
        newdst = shutil.copy2(src,dest,follow_symlinks=symlinks)
        self.files_copied += 1
        return newdst

    def _count_files(self, directory):
        total = 0
        #dirpath, dirnames, filenames = os.walk(directory)
        for dirpath, dirnames, filenames in os.walk(directory):
            for file in filenames:
                total += 1

            for directory in dirnames:
                total += self._count_files(os.path.join(dirpath,directory))
        
        return total

    def copy(self, src, dest):
        self.files_to_copy = self._count_files(src)
        try:
            if(os.path.isdir(src)):
                shutil.copytree(src, dest, copy_function=self._copy_progress)
            elif(os.path.isfile(src)):
                self._copy_progress(src,dest)
        except InterruptedError as e:
            print("Copy incompleted:")
            print(str(e))
        else:
            print("Copy completed")

    def stop(self):
        self._stop = True
        
class ImageManager:
    def __init__(self):
        self._image_path = r'/etc/hddmon/images/' #Onboarded images go here.
        self.discovered_images = [] #List of DiskImage
        self._adding_images = [] #List of (CopyManager, image) that are being added. 
        self.added_images = [] #List of CustomerImage
        self._discover_locations = ['/home/partimag/']
        self._stop = False
        self._load_existing_images()

        for p in self._discover_locations:
            self.scan_for_images(p)

    def _put_on_server(self):
        pass

    def _load_existing_images(self):
        if not os.path.exists(self._image_path):
            return
        directories = os.listdir(self._image_path)
        for name in directories:
            directory = os.path.join(self._image_path,name)
            print("Loading image " + directory)
            datadat = os.path.join(directory, 'hddmond-data.dat')
            if(os.path.isdir(directory)) and (os.path.exists(datadat)):
                try:
                    import pickle
                    with open(datadat,'r+b') as fd:
                        i = pickle.load(fd)
                        self.added_images.append(i)
                except Exception as e:
                    print("Error loading image at " + directory + ":\n" + str(e))

    def scan_for_images(self, scan_folder):
        '''
        Scans for partclone images to parse. Will put images into discovered_images list.
        '''
        if not os.path.exists(scan_folder):
            return
        directories = os.listdir(scan_folder)
        for name in directories:
            directory = os.path.join(scan_folder,name)
            print("Found " + directory)
            if(os.path.isdir(directory)):
                try:
                    i = DiskImage(name, directory)
                    self.discovered_images.append(i)
                except Exception as e:
                    print("Error adding image at " + directory + ":\n" + str(e))

    def _copy_image_thread(self, image: DiskImage, customer: str, copydone=None):
        print("Copying local image {0} in background...".format(image.name))
        self.discovered_images.remove(image)
        #cp_manager = CopyManager()
        #t = (cp_manager, image)
        t = (None, image)
        self._adding_images.append(t)
        newpath = os.path.join(self._image_path, image.name)
        print(newpath)
        try:
            os.symlink(image.path, newpath, target_is_directory=os.path.isdir(image.path))
        except Exception as e:
            print("Failed copying {0}:".format(image.name))
            print(str(e))
        else:
            print("Copied and added image {0} to onboarded images.".format(image.name))
            self._adding_images.remove(t)
            c = CustomerImage(image.name, newpath, customer)
            if copydone != None and callable(copydone):
                copydone(c)
        
    def _copy_image_done(self, image: CustomerImage):
        self.added_images.append(image)
        print("Done adding " + str(image.name))

    def _copy_image(self, image: DiskImage, customer: str):
        ct = threading.Thread(target=self._copy_image_thread, args=(image,customer,self._copy_image_done), name="copy_image_{0}".format(image.name))
        ct.start()

    def onboard_image(self, image_name: str, customer: str):
        for i in range(len(self.discovered_images)):
            if self.discovered_images[i].name == image_name:
                disk_image = self.discovered_images[i]
                self._copy_image(disk_image, customer)
                break

    def get_images(self, *a, **kv):
        return {'onboarded_images': self.added_images, 'discovered_images': self.discovered_images}

    def stop(self):
        self._stop = True
        for manager, image in self._adding_images:
            if manager != None:
                manager.stop()
                
                


            

        
