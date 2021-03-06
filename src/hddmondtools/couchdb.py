from hddmondtools.databaseinterface import GenericDatabase
from cloudant import CouchDB
from requests import HTTPError
from hddmondtools.hddmon_dataclasses import HddData, TaskData, AttributeData, SmartData
from hddmontools.config_service import ConfigService
import datetime
from injectable import injectable, injectable_factory, inject

import logging

class CouchDatabase(GenericDatabase):
    def __init__(self, address_with_port, user, passw):
        self.logger = logging.getLogger(__name__ + "." + self.__class__.__qualname__)
        self.logger.setLevel(logging.DEBUG)
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
            self.logger.debug("Database connection established.")
        except Exception as e:
            self.logger.error(f"Couldn't connect to database. {str(e)}")
            return False
        self.logger.debug("Creating databases...")
        self.couch.create_database('hard-drives')
        self.hdddb = self.couch['hard-drives']
        self.couch.create_database('tasks')
        self.taskdb = self.couch['tasks']
        self.couch.create_database('smart-captures')
        self.smartdb = self.couch['smart-captures']
        self.logger.debug("Databases created.")
        return True

    def disconnect(self):
        self.logger.info("Disconnecting from database...")
        self.couch.disconnect()

    def update_hdd(self, hdd: HddData):
        r_hdd = None

        if not hdd:
            return

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

        if not serial:
            return

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
            'hdd': serial,
            'time_started': task.time_started,
            'time_ended': task.time_ended
        }

        try:
            task_doc = self.taskdb.create_document(task_data)
        except HTTPError:
            self.logger.error(f"There was an HTTP error while trying to save the {task.name} task from {serial}")
            return
        
        r_hdd = self.hdddb[serial]
        r_hdd.fetch()
        tasks = r_hdd.get('tasks', list()).copy()
        tasks.append(task_doc['_id'])
        r_hdd['tasks'] = tasks
        r_hdd.save()
        del tasks

    def insert_attribute_capture(self, hdd:HddData):

        if not hdd:
            return

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
            'date': datetime.datetime.now(datetime.timezone.utc).isoformat(),
            'assessment': hdd.smart.assessment,
            'firmware': hdd.smart.firmware,
            'attributes': attributes_data
        }

        try:
            sc_doc = self.smartdb.create_document(s_data)
        except HTTPError:
            self.logger.error(f"There was an HTTP error while trying to save the smart capture from {hdd.serial}")
            return

        r_hdd = self.hdddb[hdd.serial]
        r_hdd.fetch()
        if not r_hdd.get('smart_captures', False):
            r_hdd['smart_captures'] = []
        r_hdd['smart_captures'].append(sc_doc['_id'])
        r_hdd.save()

@injectable_factory(CouchDatabase)
def couchdb_factory():
    cfg_svc = inject(ConfigService)
    address = cfg_svc.data['couchdb']['address']
    port = cfg_svc.data['couchdb']['port']
    user = cfg_svc.data['couchdb']['user']
    passw = cfg_svc.data['couchdb']['password']
    return CouchDatabase(f"{address}:{port}", user, passw)
