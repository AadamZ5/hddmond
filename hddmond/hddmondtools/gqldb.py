from .hddmon_dataclasses import TaskData, HddData, TaskQueueData, ImageData
from .genericdatabase import GenericDatabase
from .hdddb_schema import SmartCaptureInput, AttributeInput, HddInput, TaskInput, Query, Mutation, NoteInput, ImageInput, PartitionInput, ChecksumInput
from sgqlc.operation import Operation
from sgqlc.endpoint.http import HTTPEndpoint
import datetime
import threading

# 
# This was an implimentation to get the daemon to talk to the database through graphql, but it is no longer being maintained. 
# GraphQL is the nicest when it's used as a front-end query language. While it would be acceptable to use it for this daemon, 
# it isn't the most practical in this case. This option was deserted for a pure couchdb implimentation where the daemon directly 
# communicates with couchdb. This avoids all the unessescesaryuwuad abstraction and implimentation for GraphQL.
#

class GraphQlDatabase(GenericDatabase):
    def __init__(self, url, header_dict=None):
        self.url = url
        self.headers = header_dict if header_dict != None else {}
        self._connection_thread = None
        self._connected = False
        self.connection = None

    def connect(self, *a, **kw):
        if not self._connected:
            self.connection = HTTPEndpoint(self.url, self.headers)
            # self._connection_thread = threading.Thread( target=self._connect, name="GraphqlDB")
            # self._connection_thread.start()

    def _connect(self):
        pass
    
    def disconnect(self):
        self.connection = None

    def update_hdd(self, hdd:HddData):
        mutation = Operation(Mutation)

        ghdd = HddInput()
        ghdd.capacity = hdd.capacity
        ghdd.model = hdd.model
        ghdd.wwn = hdd.wwn
        ghdd.serial = hdd.serial
        ghdd.last_seen = datetime.datetime.utcnow().isoformat()

        r = mutation.set_hdd(hdd=ghdd)
        r.serial()
        try:
            self.connection(mutation)
            print("Updated " + str(hdd.serial) + " in database")
        except Exception as e:
            print("Error updating " + str(hdd.serial) + " in database:\n" + str(e))

    def see_hdd(self, serial: str):
        mutation = Operation(Mutation)

        r = mutation.see_hdd(serial=serial)
        data = None
        try:
            data = self.connection(mutation)
            print("Increased 'seen' counter for " + str(serial) + " in database")
        except Exception as e:
            print("Error setting 'seen' counter for " + str(serial) + " in database:\n" + str(e))
        
        new_seen_count = None
        if data != None:
            try:
                new_seen_count = int(data['data']['seeHdd']['seen'])
            except Exception as e:
                print("Error gathering new seen count from " + str(serial) + ":\n" + str(e))
        
        return new_seen_count

    def add_task(self, serial:str, task:TaskData):
        mutation = Operation(Mutation)

        gnotes = []
        for n in task.notes:
            gn = NoteInput()
            gn.timestamp = n.timestamp
            gn.note = n.note
            gn.note_taker = n.note_taker
            gn.tags = n.tags
            gnotes.append(gn)

        t_compl = TaskInput()
        t_compl.name = task.name
        t_compl.notes = gnotes
        t_compl.return_code = task.return_code

        r = mutation.add_task(serial=serial, task=t_compl)
        r.name()
        try:
            self.connection(mutation)
            print("Added task " + str(task.name) + " to " + str(serial) + " in database")
        except:
            print("Error while updating database for task " + str(task.name) + " on " + str(serial))

    def decommission(self, serial:str, decommissioned=True):
        mutation = Operation(Mutation)
        mutation.decommission(serial=serial, decommission=decommissioned)
        try:
            self.connection(mutation)
            print("Decommissioned " + str(serial) + " in database")
        except:
            print("Error while decommissioniing " + str(serial))
        pass

    def insert_attribute_capture(self, hdd:HddData):
        mutation = Operation(Mutation)


        attr_input = []
        for a in hdd.smart.attributes:
            gatt = AttributeInput()
            gatt.index = a.index
            gatt.name = a.name
            gatt.value = a.value
            gatt.flags = a.flags
            gatt.worst = a.worst
            gatt.threshold = a.threshold
            gatt.type = a.attr_type
            gatt.updated = a.updated_freq
            gatt.when_failed = a.when_failed
            gatt.raw = a.raw_value
            attr_input.append(gatt)

        smart = SmartCaptureInput()
        smart.date = datetime.datetime.now().isoformat()
        smart.assessment = hdd.smart.assessment
        smart.firmware = hdd.smart.firmware
        smart.attributes = attr_input

        r = mutation.add_smart_capture(serial=hdd.serial, smartCapture=smart)
        r.assessment()
        try:
            self.connection(mutation)
            print("Added smart capture for " + str(hdd.serial) + " in database")
        except Exception as e:
            print("Error adding smart capture " + str(hdd.serial) + " in database:\n" + str(e))

    def set_image(self, image:ImageData):
        mutation = Operation(Mutation)

        parts = []
        for p in image.partitions:
            sums = []
            for s in p.md5_sums:
                gs = ChecksumInput()
                gs.checksum = s.md5_sum
                gs.path = s.root_path
                sums.append(gs)
            gp = PartitionInput()
            gp.index = p.index
            gp.filesystem = p.filesystem
            gp.start_sector = p.start_sector
            gp.end_sector = p.end_sector
            gp.flags = p.flags
            gp.md5_sums = sums
            gp.partition_type = p.part_type
            parts.append(gp)
            

        imageg = ImageInput()
        imageg.image_name = image.name
        imageg.notes = []
        imageg.path_on_server = image.path
        imageg.customer = "DNP" #This needs variable
        imageg.version = "??" #This needs variable
        imageg.partitions = parts
        r = mutation.set_image(image=imageg)
        r.image_name()
        try:
            self.connection(mutation)
            print("Added image " + str(image.name) + " to database")
        except:
            print("Error while updating database for image " + str(image.name))
