from injectable import injectable
from pathlib import Path
import json
import os
import logging

@injectable(singleton=True)
class ConfigService:

    @property
    def data(self):
        return self._data

    def __init__(self):
        self.logger = logging.getLogger(__name__ + "." + self.__class__.__qualname__)
        self.logger.setLevel(logging.DEBUG)
        self._data = {
            'couchdb': {
                'address': None,
                'port': None,
                'user': None,
                'password': None,
            },
            'websocket_host': {
                'port': 8765
            },
            'hddmon_remote_host': {
                'port': 56567
            }
        }
        self._path = (Path(__file__).parent / '../config/config.json').absolute()

        try:
            with self._path.open() as fd:
                self._data = json.load(fd)
        except FileNotFoundError:
            self.logger.warn(f"No config file exists at {self._path}! Be sure to specify configuration either environment variables or cmd line arguments! A config file should be used as a fallback!")
        except json.JSONDecodeError as e:
            self.logger.error(f"There was an error while parsing {self._path}! {str(e)}")
        
        self.override_env_var()

    def override_env_var(self):
        db_address = os.getenv('DB_ADDRESS')
        db_port = os.getenv('DB_PORT')
        db_user = os.getenv('DB_USER')
        db_passw = os.getenv('DB_PASSWORD')

        ws_port = os.getenv('WEBSOCKET_PORT')

        hddmon_port = os.getenv('HDDMON_PORT')
        

        if db_address != None:
            self._data['couchdb']['address'] = str(db_address)
            self.logger.debug(f"Got ENV variable DB_ADDRESS={db_address}")
        if db_port != None:
            self._data['couchdb']['port'] = int(db_port)
            self.logger.debug(f"Got ENV variable DB_PORT={db_port}")
        if db_user != None:
            self._data['couchdb']['user'] = str(db_user)
            self.logger.debug(f"Got ENV variable DB_USER (not displayed)")
        if db_passw != None:
            self._data['couchdb']['password'] = str(db_passw)
            self.logger.debug(f"Got ENV variable DB_PASSWORD (not displayed)")

        if ws_port != None:
            self._data['websocket_host']['port'] = int(ws_port)
            self.logger.debug(f"Got ENV variable WEBSOCKET_PORT={ws_port}")
        if hddmon_port != None:
            self._data['hddmon_remote_host']['port'] = int(hddmon_port)
            self.logger.debug(f"Got ENV variable HDDMON_PORT={hddmon_port}")