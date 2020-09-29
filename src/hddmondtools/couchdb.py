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
        self.couch = CouchDB(self._u, self._p, url=self._add, auto_renew=True)
        try:
            self.couch.connect()
        except:
            return False
        
        self.couch.create_database('hard-drives')
        self.hdddb = self.couch['hard-drives']
        self.couch.create_database('tasks')
        self.taskdb = self.couch['tasks']
        self.couch.create_database('smart-captures')
        self.smartdb = self.couch['smart-captures']
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
                'first_seen': datetime.datetime.now(datetime.timezone.utc).isoformat(),
                'last_seen': datetime.datetime.now(datetime.timezone.utc).isoformat(),
                'seen': 0, #hddmond will increase this counter accordingly.
                'decommissioned': False,
                'tasks': [],
                'notes': [],
                'smart_captures': [],
            }
            r_hdd = self.hdddb.create_document(data)
        else:
            r_hdd  = self.hdddb[hdd.serial]
            r_hdd.fetch()
            new_data = {
                'last_seen': datetime.datetime.now(datetime.timezone.utc).isoformat(),
            }

            r_hdd.update(new_data)

        r_hdd.save()

    def see_hdd(self, serial: str):
        r_hdd = None
        if not serial in self.hdddb:
            raise RuntimeWarning("Hdd doc " + str(serial) + " not found in database!")
        
        r_hdd = self.hdddb[serial]
        r_hdd.fetch()
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
            notes_dict_list.append(note_data)

        task_data = {
            'name': task.name,
            'notes': notes_dict_list,
            'return_code': task.return_code,
            'hdd': serial
        }

        task_doc = self.taskdb.create_document(task_data)
        r_hdd = self.hdddb[serial]
        r_hdd.fetch()
        tasks = r_hdd.get('tasks', list()).copy()
        tasks.append(task_doc['_id'])
        r_hdd['tasks'] = tasks
        r_hdd.save()
        del tasks

    def insert_attribute_capture(self, hdd:HddData):

        attributes_data = []
        for a in hdd.smart.attributes:
            a_data = {
                'index': a.index,
                'name': a.name,
                'value': a.value,
                'flags': a.flags,
                'worst': a.worst,
                'threshold': a.threshold,
                'type': a.attr_type,
                'updated': a.updated_freq,
                'when_failed': a.when_failed,
                'raw': a.raw_value
            }
            attributes_data.append(a_data)

        s_data = {
            'date': datetime.datetime.now().isoformat(),
            'assessment': hdd.smart.assessment,
            'firmware': hdd.smart.firmware,
            'attributes': attributes_data
        }

        sc_doc = self.smartdb.create_document(s_data)

        r_hdd = self.hdddb[hdd.serial]
        r_hdd.fetch()
        if not r_hdd.get('smart_captures', False):
            r_hdd['smart_captures'] = []
        r_hdd['smart_captures'].append(sc_doc['_id'])
        r_hdd.save()