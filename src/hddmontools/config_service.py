from injectable import injectable
from pathlib import Path
import json

@injectable(singleton=True)
class ConfigService:

    @property
    def data(self):
        return self._data

    def __init__(self):
        self._data = None
        self._path = Path(__file__).parent / '../config/config.json'
        try:
            with self._path.open() as fd:
                self._data = json.load(fd)
        except FileNotFoundError as e:
            print(f"Please ensure a config file exists at {self._path}!")
            print(str(e))
            exit(1)
