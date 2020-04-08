from .genericdatabase import GenericDatabase
from cloudant import CouchDB
from .hddmon_dataclasses import HddData, TaskData, AttributeData, SmartData
import datetime

class CouchDatabase(GenericDatabase):
    def __init__(self, address_with_port, user, passw):
        self._u = user
        self._add = address_with_port
        self._p = passw

        self.couch = None
        self.hdddb = None
        self.taskdb = None
    
    def connect(self, *a, **kw):
        self.couch = CouchDB(self._u, self._p, url=self._add)
        self.couch.connect()
        self.couch.create_database('hard-drives')
        self.hdddb = self.couch['hard-drives']
        self.couch.create_database('tasks')
        self.taskdb = self.couch['tasks']
        return True

    def disconnect(self):
        self.couch.disconnect()

    def update_hdd(self, hdd: HddData):
        r_hdd = None
        if not hdd.serial in self.hdddb:

            data = {
                '_id': hdd.serial,
                'model': hdd.model,
                'wwn': hdd.wwn,
                'capacity': hdd.capacity,
                'firstSeen': datetime.datetime.now().isoformat(),
                'lastSeen': datetime.datetime.now().isoformat(),
                'seen': 1,
                'decomissioned': False,
                'tasks': [],
                'notes': [],
            }
            r_hdd = self.hdddb.create_document(data)
        else:
            r_hdd  = self.hdddb[hdd.serial]

            new_data = {
                'lastSeen': datetime.datetime.now().isoformat(),
            }

            r_hdd.update(new_data)

        r_hdd.save()

    def see_hdd(self, serial: str):
        r_hdd = None
        if not serial in self.hdddb:
            raise RuntimeWarning("Hdd doc " + str(serial) + " not found in database!")
        
        r_hdd = self.hdddb[serial]
        new_seen_count = r_hdd['seen'] + 1
        r_hdd['seen'] = new_seen_count
        r_hdd.save()

        return new_seen_count

    def add_task(self, serial: str, task:TaskData):
        r_hdd = None
        if not serial in self.hdddb:
            raise RuntimeWarning("Hdd doc " + str(serial) + " not found in database!")

        notes_dict_list = []
        for i in range(len(task.notes)):
            note_data = {
                'timestamp': task.notes[i].timestamp,
                'note': task.notes[i].note,
                'note_taker': task.notes[i].note_taker,
                'tags': task.notes[i].tags,
                'index': i
            }

        task_data = {
            'name': task.name,
            'notes': notes_dict_list,
            'return_code': task.return_code,
            'hdd': serial
        }

        task_doc = self.taskdb.create_document(task_data)
        r_hdd = self.hdddb[serial]
        r_hdd['tasks'].append(task_doc['_id'])
        r_hdd.save()