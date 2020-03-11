from .hddmon_dataclasses import TaskData, HddData, TaskQueueData
from .genericdatabase import GenericDatabase
from .hdddb_schema import SmartCaptureInput, AttributeInput, HddInput, TaskInput, Query, Mutation, NoteInput
from sgqlc.operation import Operation
from sgqlc.endpoint.http import HTTPEndpoint
import datetime
import threading

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
            print("Error while updatng database for task " + str(task.name) + " on " + str(serial))

    def decommission(self, serial:str, decommissioned=True):
        mutation = Operation(Mutation)
        mutation.decommission(serial=serial, decommission=decommissioned)
        try:
            self.connection(mutation)
            print("Decommissioned " + str(serial) + " in database")
        except:
            print("Error while decommissioniing " + str(serial))
        pass

    def insert_attribute_capture(self, serial: str, attribute_capture):
        pass
